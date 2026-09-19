# Nakoba — Runbook: Zero to Deployed

Follow this top to bottom. Each step names the exact command and why it's
there. Stop and fix before moving on if a step fails — later steps assume
the prior ones succeeded.

---

## Phase 0 — Prerequisites

Install these once:

| Tool | Check install | Install |
|---|---|---|
| Git | `git --version` | https://git-scm.com/downloads |
| GitHub CLI (optional but recommended) | `gh --version` | https://cli.github.com |
| Azure CLI | `az --version` | https://learn.microsoft.com/cli/azure/install-azure-cli |
| Azure ML CLI extension | `az extension list` (look for `ml`) | `az extension add -n ml` |
| Terraform | `terraform --version` | https://developer.hashicorp.com/terraform/install |
| Python 3.10+ | `python3 --version` | https://www.python.org/downloads |

You'll also need:
- A **GitHub account** (free tier is fine).
- An **Azure subscription** with permission to create resource groups and
  assign roles (Owner or Contributor + User Access Administrator on the
  subscription/resource group).

---

## Phase 1 — Get the code onto your machine and into your GitHub

```bash
tar -xzf nakoba.tar.gz
cd nakoba
```

Re-attribute the existing commits to you (they were made with a placeholder identity):

```bash
git rebase -i --root
# in the editor, mark every commit "edit" (not "pick"), save and close
git commit --amend --author="Your Name <you@email.com>" --no-edit
git rebase --continue   # repeat the amend+continue for each commit
```

Create the GitHub repo and push:

```bash
# with GitHub CLI (easiest):
gh auth login
gh repo create nakoba --public --source=. --remote=origin --push

# OR manually:
#   1. Create an empty repo named "nakoba" at github.com/new (no README/gitignore)
#   2. git remote add origin https://github.com/<you>/nakoba.git
#   3. git branch -M main
#   4. git push -u origin main
```

Fix the placeholder in `CODEOWNERS` (replace `@<your-github-username>` with
your real handle), commit, push:

```bash
sed -i 's/@<your-github-username>/@YOUR_ACTUAL_HANDLE/g' CODEOWNERS
git add CODEOWNERS && git commit -m "Set real CODEOWNERS handle" && git push
```

---

## Phase 2 — Azure: log in and pick where things live

```bash
az login
az account list --output table          # find the subscription you want
az account set --subscription "<subscription-id-or-name>"
```

Decide your resource group naming (the Terraform already assumes
`rg-nakoba-<environment>`, so nothing to change unless you want different names).

---

## Phase 3 — Terraform remote state (do this before terraform init)

Terraform needs somewhere durable to store its state file — not your laptop.
Create a small storage account just for this, once:

```bash
az group create -n rg-tfstate -l eastus2
az storage account create -n sttfstatenakoba -g rg-tfstate -l eastus2 --sku Standard_LRS
az storage container create -n tfstate --account-name sttfstatenakoba
```

Edit `terraform/envs/dev-backend.tfbackend` and uncomment/fill in:

```hcl
resource_group_name  = "rg-tfstate"
storage_account_name = "sttfstatenakoba"
container_name        = "tfstate"
key                    = "nakoba-dev.tfstate"
```

(If `sttfstatenakoba` is already taken globally — storage account names are
globally unique across all of Azure — pick another name and update it in
both the `az storage account create` command and the backend file.)

---

## Phase 4 — Provision the infrastructure

```bash
cd terraform
terraform init -backend-config=envs/dev-backend.tfbackend
terraform plan -var-file=envs/dev.tfvars      # review what it will create
terraform apply -var-file=envs/dev.tfvars     # type "yes" to confirm
```

This creates: resource group, VNet/subnet, storage account, Key Vault,
Application Insights, Container Registry, the Azure ML workspace, a
scoped managed identity, and a compute cluster. Takes roughly 5–10 minutes.

Grab the outputs you'll need next:

```bash
terraform output workspace_name
terraform output acr_login_server
```

---

## Phase 5 — Build the training environment and generate data

```bash
cd ..   # back to repo root
RG=rg-nakoba-dev
WS=$(cd terraform && terraform output -raw workspace_name)

az ml environment create -f environments/train-env.yml -g $RG -w $WS

python3 src/generate_synthetic_data.py --rows 20000 --out data/synthetic_claims.csv

az ml data create --name nakoba-synthetic-claims --version 1 \
  --path data/synthetic_claims.csv --type uri_file -g $RG -w $WS
```

Update `jobs/train-job.yml`'s `claims_data` path to point at the registered
data asset (`azureml:nakoba-synthetic-claims:1`) instead of the placeholder
blob path, if you haven't already.

---

## Phase 6 — Train and register the model

```bash
az ml job create -f jobs/train-job.yml -g $RG -w $WS --stream
```

Watch it run in your terminal (`--stream`), or open the run in Azure ML
Studio. Once it completes, note the job name it printed, then register:

```bash
JOB_NAME=<the job name from the previous step>
az ml model create -f jobs/model-registration.yml -g $RG -w $WS \
  --set path="azureml://jobs/$JOB_NAME/outputs/artifacts/paths/model"
```

---

## Phase 7 — Deploy behind the managed endpoint

```bash
az ml online-endpoint create -f deploy/endpoint.yml -g $RG -w $WS
az ml online-deployment create -f deploy/deployment.yml -g $RG -w $WS --all-traffic
```

`--all-traffic` sends 100% of traffic to this first deployment since there's
no prior champion yet. On any future model version, deploy it as a *second*
deployment (e.g. `challenger`) at a small traffic percentage instead — that's
the canary pattern `docs/DECISIONS.md` #5 describes.

Test it:

```bash
az ml online-endpoint invoke --name nakoba-escalation-risk-ep -g $RG -w $WS \
  --request-file <(echo '{"instances":[{"vehicle_model_line":"Touring","dealer_region":"NA-East","component":"engine","vehicle_age_months":24,"mileage_at_claim":15000,"telemetry_fault_codes_30d":2,"telemetry_avg_engine_temp_delta":3.1,"component_historical_failure_severity":0.4,"prior_claims_same_vin":1,"dealer_avg_repair_days":5.2}],"claim_ids":["CLM-TEST-001"]}')
```

You should get back a JSON prediction with an escalation risk score and top
weighted factors.

---

## Phase 8 — Wire up CI/CD (GitHub Actions)

The workflows use OIDC federation to Azure AD — no long-lived secret ever
sits in GitHub. Set it up once:

```bash
# Create an app registration for GitHub Actions to authenticate as
az ad app create --display-name "nakoba-github-actions"
APP_ID=$(az ad app list --display-name "nakoba-github-actions" --query "[0].appId" -o tsv)
az ad sp create --id $APP_ID

# Give it Contributor on the resource group (scope tighter in a real org)
az role assignment create --assignee $APP_ID --role Contributor \
  --scope /subscriptions/<your-subscription-id>/resourceGroups/rg-nakoba-dev

# Federate it to your GitHub repo (no client secret needed)
az ad app federated-credential create --id $APP_ID --parameters '{
  "name": "nakoba-main-branch",
  "issuer": "https://token.actions.githubusercontent.com",
  "subject": "repo:YOUR_GH_USERNAME/nakoba:ref:refs/heads/main",
  "audiences": ["api://AzureADTokenExchange"]
}'
```

Add these as GitHub repo secrets (Settings → Secrets and variables → Actions):

| Secret | Value |
|---|---|
| `AZURE_CLIENT_ID` | `$APP_ID` from above |
| `AZURE_TENANT_ID` | `az account show --query tenantId -o tsv` |
| `AZURE_SUBSCRIPTION_ID` | `az account show --query id -o tsv` |

Turn on branch protection for `main` (Settings → Branches → Add rule)
requiring the CI checks (`lint-and-test`, `terraform-plan`, `secret-scan`)
before merge.

Push any small change on a branch, open a PR, and watch the CI checks run
in the Actions tab — that's your first real proof this all works together.

---

## Phase 9 — Optional: run the RAG/agentic layer locally

These don't need Azure provisioned to demonstrate — they run against local
stubs already, which is how I tested them:

```bash
pip install -r requirements-agentic.txt
python3 -m pytest tests/ -v        # confirm all 26 tests still pass on your machine
python3 agentic/mcp_server.py      # starts the MCP server; connect an MCP client to try the tools
```

To make the RAG pipeline real instead of stub-tested, you'd additionally
need an Azure AI Search resource (`az search service create`) and some
actual documents to ingest — that's a reasonable next phase once the core
platform above is running, not a blocker to showing this repo as-is.

---

## Troubleshooting quick-reference

| Symptom | Likely cause |
|---|---|
| `terraform init` fails on backend | Storage account name in Phase 3 isn't globally unique yet, or you forgot to uncomment the backend file |
| `az ml environment create` hangs/fails on build | Check `az acr login --name <acr-name>` works — usually an auth issue, not a Dockerfile issue |
| Training job fails immediately | Check the compute cluster scaled up (`az ml compute show`) — LowPriority nodes can be preempted; rerun |
| Endpoint invoke returns 401 | `auth_mode: aad_token` in `deploy/endpoint.yml` means you need an AAD token, not a static key — use `az ml online-endpoint invoke` (handles this for you) rather than a raw curl without a token |
| GitHub Actions OIDC login fails | Double-check the federated credential `subject` matches your exact repo path and branch |

---

## What "done" looks like

- [ ] Repo pushed to your own GitHub, commits attributed to you
- [ ] `terraform apply` succeeded — workspace visible in Azure ML Studio
- [ ] A training job completed and a model is registered
- [ ] The endpoint responds to a real invoke with a prediction
- [ ] A PR triggers CI and all three checks go green
- [ ] Branch protection is on, so the checks actually gate merges

At that point you have a real, running thing to walk an interviewer through
click by click — not just a repo that looks right sitting still.
