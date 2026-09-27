# Nakoba --- End-to-End Azure MLOps, RAG, and MCP Implementation Guide

> **Purpose:** Rebuildable engineering runbook and troubleshooting
> record for the Nakoba portfolio project.\
> **Platform:** Azure Machine Learning + Terraform + GitHub Actions +
> Azure OpenAI + Azure AI Search + MCP\
> **Environment used for the validated build:** Windows 11, Git
> Bash/MINGW64, Python 3.10, Azure CLI, Azure ML CLI v2, Terraform\
> **Repository:** `SHADRACK-NAKOBA/E2E-ML-PROJECT`\
> **Validated final implementation:** September 2026\
> **Important:** The warranty/service data and knowledge-base documents
> in this repository are synthetic/demo content. They are not
> manufacturer documents or production customer data.

------------------------------------------------------------------------

## Table of Contents

1.  [Project objective](#1-project-objective)
2.  [What was built](#2-what-was-built)
3.  [Final architecture](#3-final-architecture)
4.  [Repository structure](#4-repository-structure)
5.  [Phase 0 --- Prerequisites](#5-phase-0--prerequisites)
6.  [Phase 1 --- Git and GitHub setup](#6-phase-1--git-and-github-setup)
7.  [Phase 2 --- Azure authentication](#7-phase-2--azure-authentication)
8.  [Phase 3 --- Terraform remote
    state](#8-phase-3--terraform-remote-state)
9.  [Phase 4 --- Provision Azure
    infrastructure](#9-phase-4--provision-azure-infrastructure)
10. [Phase 5 --- Azure ML environment, data, and
    compute](#10-phase-5--azure-ml-environment-data-and-compute)
11. [Phase 6 --- Train, evaluate, and register the
    model](#11-phase-6--train-evaluate-and-register-the-model)
12. [Phase 7 --- Deploy the managed online
    endpoint](#12-phase-7--deploy-the-managed-online-endpoint)
13. [Phase 8 --- GitHub Actions CI/CD and
    OIDC](#13-phase-8--github-actions-cicd-and-oidc)
14. [Phase 9 --- Champion/challenger
    governance](#14-phase-9--championchallenger-governance)
15. [Phase 10 --- Azure OpenAI and Azure AI
    Search](#15-phase-10--azure-openai-and-azure-ai-search)
16. [Phase 11 --- Build the RAG index and ingest
    knowledge](#16-phase-11--build-the-rag-index-and-ingest-knowledge)
17. [Phase 12 --- Hybrid retrieval, reranking, and
    grounding](#17-phase-12--hybrid-retrieval-reranking-and-grounding)
18. [Phase 13 --- MCP and agentic
    integration](#18-phase-13--mcp-and-agentic-integration)
19. [Phase 14 --- Security and
    authorization](#19-phase-14--security-and-authorization)
20. [Phase 15 --- Testing and final
    validation](#20-phase-15--testing-and-final-validation)
21. [Azure Portal click-by-click
    verification](#21-azure-portal-click-by-click-verification)
22. [Troubleshooting --- errors encountered and
    fixes](#22-troubleshooting--errors-encountered-and-fixes)
23. [Cost control](#23-cost-control)
24. [Safe teardown](#24-safe-teardown)
25. [Rebuild after teardown](#25-rebuild-after-teardown)
26. [Interview walkthrough](#26-interview-walkthrough)
27. [Final completion checklist](#27-final-completion-checklist)

------------------------------------------------------------------------

# 1. Project objective

Nakoba is an end-to-end reference implementation for operating both
conventional machine learning and grounded generative AI in a controlled
Azure environment.

The business scenario is warranty/service escalation. The classical ML
model predicts whether a claim is likely to escalate. The RAG layer
answers dealer/technician knowledge questions from an approved knowledge
base. The MCP layer exposes those capabilities as structured tools so an
agent can use them without making the language model the security
boundary.

The point of the project is not model novelty. The point is platform
ownership:

-   infrastructure as code;
-   immutable/reproducible ML assets;
-   CI/CD;
-   federated cloud authentication rather than stored Azure client
    secrets;
-   model registry and lineage;
-   champion/challenger evaluation;
-   managed online inference;
-   rollback;
-   RAG with hybrid search;
-   reranking and groundedness checks;
-   server-side authorization;
-   MCP tools;
-   testing and operational troubleshooting.

------------------------------------------------------------------------

# 2. What was built

The final environment contains the following major resources and
capabilities.

  -----------------------------------------------------------------------
  Layer                               Implementation
  ----------------------------------- -----------------------------------
  Source control                      Git + GitHub

  Infrastructure                      Terraform using `azurerm ~> 3.100`

  Terraform state                     Azure Storage remote backend

  ML platform                         Azure Machine Learning workspace

  ML compute                          `cpu-cluster-dev`,
                                      `Standard_DS2_v2`, min 0 / max 1

  Registry                            Azure ML model/environment/data
                                      assets

  Serving                             Azure ML managed online endpoint

  Endpoint                            `nakoba-escalation-risk-ep`

  Production deployment               `champion`, `Standard_DS2_v2`, one
                                      instance

  Authentication                      Microsoft Entra ID / AAD token

  Runtime identity                    User-assigned managed identity

  CI/CD                               GitHub Actions

  CI/CD Azure auth                    GitHub OIDC federation

  LLM platform                        Azure OpenAI

  Embeddings                          `text-embedding-3-large`

  Chat/reranking/generation           `gpt-5-6-sol` deployment used in
                                      the validated build

  Retrieval                           Azure AI Search Basic

  Search service                      `srch-nakoba-dev`

  Search index                        `nakoba-rag-dev`

  RAG                                 vector + keyword hybrid retrieval,
                                      reranking, groundedness

  Agent tools                         MCP

  Authorization                       server-side role/action checks and
                                      sensitivity mapping

  Tests                               Pytest + Ruff + Terraform
                                      validation

  Final local test result             37 tests passed
  -----------------------------------------------------------------------

The Terraform root module provisions the resource group, networking,
identity, workspace, and AI modules. The AI module defines the Azure
OpenAI account, Azure AI Search service, embedding deployment, and chat
deployment. Runtime RBAC gives the endpoint identity inference access to
OpenAI and read access to Search.

------------------------------------------------------------------------

# 3. Final architecture

``` text
Developer
   |
   +---------------- Git / GitHub ----------------------+
   |                                                    |
   |                                             GitHub Actions
   |                                              CI + CD + OIDC
   |                                                    |
   v                                                    v
Terraform -------------------------------------------> Azure
   |                                                    |
   +--> Resource Group                                  |
   +--> VNet/Subnet                                     |
   +--> Storage                                         |
   +--> Key Vault                                       |
   +--> ACR                                             |
   +--> Managed Identity                                |
   +--> Azure ML Workspace                              |
   +--> Azure OpenAI                                    |
   +--> Azure AI Search                                 |
                                                        |
                       +--------------------------------+
                       |
                       v
              Azure Machine Learning
                       |
          +------------+-------------+
          |                          |
          v                          v
     Training jobs             Managed endpoint
     XGBoost model        nakoba-escalation-risk-ep
          |                          |
          v                          v
     Model registry              champion
                                   |
                                   v
                         escalation prediction

Knowledge documents
       |
       v
Chunk + embed
       |
       v
Azure AI Search: nakoba-rag-dev
       |
       v
Hybrid retrieval (BM25 + vector)
       |
       v
GPT reranking -> normalized relevance
       |
       v
Grounding threshold / abstention
       |
       v
GPT answer generation
       |
       v
Grounded answer + source IDs

MCP client / agent
       |
       v
MCP server
       |
       +--> check_claim_status
       +--> predict_claim_escalation_risk --> Azure ML endpoint
       +--> escalate_warranty_claim
       +--> ask_dealer_knowledge --> RAG pipeline
                     |
                     v
             authorization guard
             role -> sensitivity
```

A core design rule is that the model is **not** the authorization
boundary. Access control is enforced in code before a tool action or
restricted retrieval is permitted.

------------------------------------------------------------------------

# 4. Repository structure

``` text
.github/workflows/
    ci.yml
    cd.yml
agentic/
    azure_ml.py
    mcp_server.py
    reliability.py
    tools.py
data/
deploy/
    endpoint.yml
    deployment.yml
docs/
    DECISIONS.md
    DECISIONS_RAG_AGENTIC.md
    RUNBOOK.md
    COPILOT_STUDIO_AND_TOOLING_NOTES.md
environments/
jobs/
monitoring/
rag/
    create_index.py
    ingest.py
    ingest_live.py
    retrieve.py
    pipeline.py
    guardrails.py
    run_live.py
    eval.py
    eval_data/
    knowledge_base/
scripts/
src/
terraform/
    envs/
    modules/
        ai/
        identity/
        networking/
        workspace/
tests/
README.md
requirements-agentic.txt
requirements-dev.txt
```

Do not commit generated caches, local credentials, Terraform plan
binaries, or secrets.

------------------------------------------------------------------------

# 5. Phase 0 --- Prerequisites

## 5.1 Required software

Install and verify:

``` bash
git --version
python --version
az --version
terraform --version
gh --version
```

Install the Azure ML CLI extension:

``` bash
az extension add --name ml --yes
az extension show --name ml
```

The validated development environment used Python 3.10.

### Windows / Git Bash note

Azure CLI installed on Windows may not initially be visible from Git
Bash. If required:

``` bash
export PATH="$PATH:/c/Program Files/Microsoft SDKs/Azure/CLI2/wbin"
az --version
```

A particularly important Git Bash setting for this project is:

``` bash
export MSYS_NO_PATHCONV=1
```

Why: MSYS/Git Bash may rewrite Azure resource IDs beginning with
`/subscriptions/...` into Windows paths. This produced misleading Azure
`MissingSubscription` errors during the project.

You can place the export in your shell profile if you routinely use
Azure CLI resource IDs from Git Bash.

------------------------------------------------------------------------

# 6. Phase 1 --- Git and GitHub setup

Clone or create the repository and enter it:

``` bash
cd ~/Downloads
git clone <your-repository-url> nakoba
cd nakoba
```

Verify:

``` bash
git status
git remote -v
git branch --show-current
```

The final repository used `main` and was pushed to:

``` text
SHADRACK-NAKOBA/E2E-ML-PROJECT
```

## GitHub portal --- click by click

1.  Sign in to GitHub.
2.  Open the repository.
3.  Click **Settings**.
4.  Open **Branches** or **Rules / Rulesets**, depending on the GitHub
    UI.
5.  Protect `main`.
6.  Require the relevant CI checks before merge.
7.  Open **Settings → Secrets and variables → Actions**.
8.  Add the Azure OIDC values described later in this guide.
9.  Open **Actions** to inspect CI/CD runs.

------------------------------------------------------------------------

# 7. Phase 2 --- Azure authentication

Log in:

``` bash
az login
```

List subscriptions:

``` bash
az account list -o table
```

Select the subscription:

``` bash
az account set --subscription "<subscription-id-or-name>"
```

Verify:

``` bash
az account show -o table
```

For Git Bash:

``` bash
export MSYS_NO_PATHCONV=1
```

Set useful variables:

``` bash
export RG="rg-nakoba-dev"
export WS="mlw-nakoba-dev"
```

## Azure Portal --- verify subscription

1.  Open Azure Portal.
2.  Search for **Subscriptions**.
3.  Open the subscription used by the project.
4.  Confirm the subscription is enabled.
5.  Open **Access control (IAM)** if you need to verify permissions.

The person provisioning RBAC needs sufficient permission to create role
assignments.

------------------------------------------------------------------------

# 8. Phase 3 --- Terraform remote state

Never treat laptop-local Terraform state as the durable source of truth
for this project.

Create a dedicated state resource group:

``` bash
az group create \
  --name rg-tfstate \
  --location eastus2
```

Create the state storage account:

``` bash
az storage account create \
  --name sttfstatenakoba \
  --resource-group rg-tfstate \
  --location eastus2 \
  --sku Standard_LRS
```

Create the container:

``` bash
az storage container create \
  --name tfstate \
  --account-name sttfstatenakoba
```

`terraform/envs/dev-backend.tfbackend` should identify:

``` hcl
resource_group_name  = "rg-tfstate"
storage_account_name = "sttfstatenakoba"
container_name        = "tfstate"
key                   = "nakoba-dev.tfstate"
```

Initialize:

``` bash
cd terraform

terraform init \
  -backend-config=envs/dev-backend.tfbackend
```

Verify:

``` bash
terraform validate
terraform fmt -check -recursive
```

### Portal verification

1.  Azure Portal → **Resource groups**.
2.  Open `rg-tfstate`.
3.  Open the state storage account.
4.  Open **Data storage → Containers**.
5.  Open `tfstate`.
6.  Verify `nakoba-dev.tfstate` appears after Terraform begins using the
    backend.

Do not delete `rg-tfstate` when tearing down only the dev environment if
you want to preserve the Terraform backend.

------------------------------------------------------------------------

# 9. Phase 4 --- Provision Azure infrastructure

The root Terraform configuration creates the Nakoba resource group and
composes networking, workspace, identity, and AI modules.

The validated dev configuration uses:

``` hcl
environment = "dev"
location    = "eastus2"

embedding_model_version = "1"
chat_model_version      = "2026-07-09"
```

Azure AI Search is intentionally parameterized separately because Search
capacity was unavailable in East US 2 during the build; the working
Search service was created in East US.

Run:

``` bash
cd ~/Downloads/nakoba/terraform

terraform init \
  -backend-config=envs/dev-backend.tfbackend

terraform fmt -check -recursive

terraform validate

terraform plan \
  -var-file=envs/dev.tfvars
```

Review the plan before applying.

Then:

``` bash
terraform apply \
  -var-file=envs/dev.tfvars
```

Confirm only after reviewing the proposed changes.

Useful outputs:

``` bash
terraform output
terraform output -raw workspace_name
terraform output -raw acr_login_server
```

## What should exist

The validated environment included:

``` text
kv-nakoba-dev
appi-nakoba-dev
stnakobadev
id-nakoba-endpoint-dev
acrnakobadev
vnet-nakoba-dev
mlw-nakoba-dev
oai-nakoba-dev
srch-nakoba-dev
```

plus Azure ML endpoint/deployment resources created through the ML
control plane.

------------------------------------------------------------------------

# 10. Phase 5 --- Azure ML environment, data, and compute

Return to repository root:

``` bash
cd ~/Downloads/nakoba

export RG="rg-nakoba-dev"
export WS="mlw-nakoba-dev"
```

Create the training environment:

``` bash
az ml environment create \
  --file environments/train-env.yml \
  --resource-group "$RG" \
  --workspace-name "$WS"
```

Generate synthetic claims:

``` bash
python src/generate_synthetic_data.py \
  --rows 20000 \
  --out data/synthetic_claims.csv
```

Register data:

``` bash
az ml data create \
  --name nakoba-synthetic-claims \
  --version 1 \
  --path data/synthetic_claims.csv \
  --type uri_file \
  --resource-group "$RG" \
  --workspace-name "$WS"
```

The training YAML references:

``` text
azureml:nakoba-synthetic-claims:1
```

and compute:

``` text
azureml:cpu-cluster-dev
```

The validated compute configuration was:

``` text
Name: cpu-cluster-dev
VM size: Standard_DS2_v2
Minimum instances: 0
Maximum instances: 1
```

Setting minimum instances to zero is important for a portfolio/dev
environment because the cluster can scale down when idle.

------------------------------------------------------------------------

# 11. Phase 6 --- Train, evaluate, and register the model

Submit:

``` bash
az ml job create \
  --file jobs/train-job.yml \
  --resource-group "$RG" \
  --workspace-name "$WS"
```

If streaming works in your shell, you may use `--stream`. During this
build, `az ml job stream` also produced a local CLI decoding problem
even when the remote Azure job itself succeeded. Therefore, job status
polling is a reliable fallback:

``` bash
az ml job show \
  --name "<JOB_NAME>" \
  --resource-group "$RG" \
  --workspace-name "$WS" \
  --query status \
  -o tsv
```

The training command uses `src/train.py` with data path, output
directory, and hyperparameters.

The registered model is:

``` text
nakoba-escalation-risk
```

The first champion used version `1`.

The model registry metadata is designed to preserve training-job
lineage, training-data reference, validation metrics, reviewer, and
approval timestamp.

### Azure ML Studio --- click by click

1.  Open Azure Portal.
2.  Search for **Machine Learning**.
3.  Open `mlw-nakoba-dev`.
4.  Click **Launch studio**, or open Azure Machine Learning Studio
    directly.
5.  Select the correct workspace.
6.  Open **Jobs**.
7.  Open the training job.
8.  Inspect:
    -   status;
    -   code snapshot;
    -   inputs;
    -   environment;
    -   compute;
    -   outputs;
    -   metrics.
9.  Open **Models**.
10. Open `nakoba-escalation-risk`.
11. Inspect the registered version and metadata.

------------------------------------------------------------------------

# 12. Phase 7 --- Deploy the managed online endpoint

The endpoint YAML defines:

``` text
name: nakoba-escalation-risk-ep
auth_mode: aad_token
identity: user_assigned
```

The deployment YAML defines:

``` text
deployment: champion
model: nakoba-escalation-risk:1
environment: nakoba-train-env:3
instance_type: Standard_DS2_v2
instance_count: 1
```

Export the endpoint identity resource ID if the YAML requires it:

``` bash
export ENDPOINT_IDENTITY_ID="<user-assigned-managed-identity-resource-id>"
```

Create endpoint:

``` bash
az ml online-endpoint create \
  --file deploy/endpoint.yml \
  --resource-group "$RG" \
  --workspace-name "$WS"
```

Create deployment:

``` bash
az ml online-deployment create \
  --file deploy/deployment.yml \
  --resource-group "$RG" \
  --workspace-name "$WS" \
  --all-traffic
```

Verify:

``` bash
az ml online-endpoint show \
  --name nakoba-escalation-risk-ep \
  --resource-group "$RG" \
  --workspace-name "$WS" \
  -o json
```

Expected traffic:

``` json
{
  "champion": 100
}
```

### Endpoint test

On Windows Git Bash, avoid process substitution if Azure CLI interprets
`/dev/fd/...` incorrectly. Prefer a real request file:

``` bash
cat > request.json <<'JSON'
{
  "instances": [
    {
      "vehicle_model_line": "Touring",
      "dealer_region": "NA-East",
      "component": "engine",
      "vehicle_age_months": 24,
      "mileage_at_claim": 15000,
      "telemetry_fault_codes_30d": 2,
      "telemetry_avg_engine_temp_delta": 3.1,
      "component_historical_failure_severity": 0.4,
      "prior_claims_same_vin": 1,
      "dealer_avg_repair_days": 5.2
    }
  ],
  "claim_ids": ["CLM-TEST-001"]
}
JSON

az ml online-endpoint invoke \
  --name nakoba-escalation-risk-ep \
  --resource-group "$RG" \
  --workspace-name "$WS" \
  --request-file request.json
```

The final working endpoint returned an escalation-risk prediction rather
than a schema or authentication error.

------------------------------------------------------------------------

# 13. Phase 8 --- GitHub Actions CI/CD and OIDC

The project intentionally avoids a long-lived Azure client secret in
GitHub.

Create an Entra application:

``` bash
az ad app create \
  --display-name "nakoba-github-actions"
```

Get the application/client ID:

``` bash
APP_ID=$(az ad app list \
  --display-name "nakoba-github-actions" \
  --query "[0].appId" \
  -o tsv)

echo "$APP_ID"
```

Create the service principal:

``` bash
az ad sp create --id "$APP_ID"
```

Create only the role assignments required by the workflow.

## GitHub federated credentials

The federated credential subject must match the actual repository and
GitHub context exactly. A main-branch subject has the form:

``` text
repo:OWNER/REPOSITORY:ref:refs/heads/main
```

A pull-request credential uses a different subject. This distinction
mattered during implementation: PR and main-branch OIDC contexts are not
interchangeable.

Example:

``` bash
az ad app federated-credential create \
  --id "$APP_ID" \
  --parameters @federated-main.json
```

## GitHub --- click by click

1.  GitHub → repository.
2.  **Settings**.
3.  **Secrets and variables**.
4.  **Actions**.
5.  **New repository secret**.
6.  Add:
    -   `AZURE_CLIENT_ID`
    -   `AZURE_TENANT_ID`
    -   `AZURE_SUBSCRIPTION_ID`
7.  Do **not** add an Azure client secret for this OIDC design.
8.  Open **Actions** after pushing changes.
9.  Select the workflow.
10. Inspect each job and failed step if a run is red.

## CI

`.github/workflows/ci.yml` performs:

-   Python 3.10 setup;
-   dependency installation;
-   Ruff lint;
-   unit tests;
-   RAG evaluation gate;
-   Terraform format check;
-   Terraform init/validate/plan;
-   Gitleaks secret scanning.

Terraform authentication uses:

``` text
ARM_CLIENT_ID
ARM_TENANT_ID
ARM_SUBSCRIPTION_ID
ARM_USE_OIDC=true
ARM_USE_AZUREAD=true
```

## CD

The CD pipeline:

1.  authenticates with Azure using OIDC;
2.  initializes Terraform;
3.  creates a saved Terraform plan;
4.  applies that exact plan;
5.  registers the ML environment;
6.  generates synthetic data;
7.  registers immutable data;
8.  trains a challenger;
9.  registers the exact training-job artifact;
10. evaluates champion and challenger;
11. downloads evaluation artifacts;
12. runs the promotion gate.

The workflow deliberately does **not** automatically shift production
traffic merely because a candidate passes eligibility checks.

------------------------------------------------------------------------

# 14. Phase 9 --- Champion/challenger governance

The project compares champion and challenger using more than aggregate
accuracy.

The gate uses:

-   F1;
-   p95 inference latency;
-   dealer-region segment evaluation;
-   vehicle-model-line segment evaluation.

A blocked challenger is a valid governance outcome, not a broken
pipeline.

The implementation treats the promotion script exit codes differently:

``` text
0 = eligible/approved
2 = governance blocked; champion remains active
other = technical failure
```

This distinction prevents a healthy governance decision from being
mislabeled as an infrastructure failure.

Rollback is designed as a traffic change rather than rebuilding a model
during an incident.

------------------------------------------------------------------------

# 15. Phase 10 --- Azure OpenAI and Azure AI Search

The Terraform AI module provisions:

## Azure OpenAI

``` text
Account: oai-nakoba-dev
Region: eastus2
SKU: S0
Local auth: disabled
Public network access: enabled
System-assigned identity: enabled
```

Deployments:

``` text
text-embedding-3-large
gpt-5-6-sol
```

The validated Terraform configuration used Standard capacity for
embeddings and GlobalStandard capacity for chat.

## Azure AI Search

``` text
Service: srch-nakoba-dev
Region: eastus
SKU: Basic
Replica count: 1
Partition count: 1
Local authentication: disabled
Public network access: enabled
System-assigned identity: enabled
```

### Why Search is in East US

The original attempt to provision Search in East US 2 failed because
Azure reported insufficient regional resources/capacity. The fix was not
to move the entire platform. Instead, Search received its own
`search_location` Terraform variable and was placed in East US.

This is a useful infrastructure pattern: isolate regional constraints
instead of unnecessarily relocating unrelated services.

------------------------------------------------------------------------

# 16. Phase 11 --- Build the RAG index and ingest knowledge

The live Search index is:

``` text
nakoba-rag-dev
```

The index includes fields such as:

``` text
id
source_doc_id
text
source
document_owner
sensitivity
chunk_index
content_vector
```

The embedding vector is 3072 dimensions for the embedding model used by
the project.

The knowledge base is stored under:

``` text
rag/knowledge_base/documents.json
```

The demo documents include dealer-visible and internal sensitivity
levels.

Create the index with the repository script:

``` bash
python -m rag.create_index
```

Ingest:

``` bash
python -m rag.ingest_live
```

Use module invocation from the repository root so Python package imports
resolve consistently.

The successful live ingestion loaded four demo documents/chunks.

### Azure Portal --- Search verification

1.  Azure Portal → search **AI Search**.
2.  Open `srch-nakoba-dev`.
3.  Open **Indexes**.
4.  Select `nakoba-rag-dev`.
5.  Inspect fields.
6.  Use **Search explorer** if available.
7.  Confirm indexed documents exist.
8.  Inspect sensitivity metadata.

------------------------------------------------------------------------

# 17. Phase 12 --- Hybrid retrieval, reranking, and grounding

The final RAG flow is:

``` text
question
  -> embedding
  -> Azure AI Search hybrid retrieval
  -> sensitivity filter
  -> GPT reranking
  -> normalized relevance score
  -> grounding threshold
  -> answer generation or abstention
  -> answer + source IDs
```

## Hybrid retrieval

`rag/retrieve.py` combines keyword/BM25 and vector search. This matters
for service knowledge because exact identifiers such as bulletin numbers
or fault codes may be better served by lexical matching, while
natural-language paraphrases benefit from embeddings.

## Metadata security

Sensitivity filtering happens in the Search query before restricted
content reaches the model.

Do not rely on a prompt such as "ignore internal documents." If the user
is not authorized, those documents should not be retrieved.

## Reranking

The initial Azure Search hybrid score is retained as `search_score`.

The reranker produces a separate normalized relevance score in the range
`[0,1]`. That normalized score is used for grounding decisions.

## Important scoring correction

During live validation, the correct document was ranked first but the
Azure hybrid/RRF score was approximately `0.0333`. The original
grounding threshold was `0.35`.

Those values are on different scales.

The fix was architectural:

``` text
Azure Search/RRF score
    -> retrieval ranking / diagnostic search_score

GPT reranker normalized score [0,1]
    -> final relevance score
    -> grounding threshold
```

Do not arbitrarily lower a grounding threshold merely to accommodate a
raw RRF score. Normalize or use a score whose semantics match the
threshold.

## Live RAG validation

The validated question was:

``` text
What's the torque spec for the rear axle nut on a Touring model?
```

The demo knowledge base produced:

``` text
Abstained: False
Grounding score: 1.0
Sources:
- repair_manual_touring_rear_axle
- service_bulletin_tcu_fault_0142

Answer:
The rear axle nut torque is 95 ft-lb (129 Nm).
```

Again, that value comes from the project's synthetic/demo knowledge base
and must not be represented as an actual manufacturer's specification.

------------------------------------------------------------------------

# 18. Phase 13 --- MCP and agentic integration

The MCP layer exposes structured tools.

The final tool set includes:

``` text
check_claim_status
predict_claim_escalation_risk
escalate_warranty_claim
ask_dealer_knowledge
```

`predict_claim_escalation_risk` invokes the authenticated Azure ML
endpoint.

`ask_dealer_knowledge` invokes the live RAG path.

The RAG tool request includes:

``` text
question
caller_role
```

The response includes:

``` text
answer
abstained
grounding_score
sources
```

The server maps roles to allowed sensitivity levels:

``` text
technician       -> dealer_visible
dealer_rep       -> dealer_visible
warranty_reviewer -> dealer_visible + internal
```

A guest or unauthorized role is denied before the RAG call.

This is intentionally server-side. An LLM cannot grant itself access to
internal knowledge by emitting a different role or by following a
prompt-injected instruction.

------------------------------------------------------------------------

# 19. Phase 14 --- Security and authorization

The security design has several layers.

## 19.1 No local API keys for OpenAI/Search in the normal design

Terraform disables local authentication on the OpenAI and Search
services.

## 19.2 Managed identity

The endpoint has a dedicated user-assigned identity.

Terraform grants runtime access:

``` text
Cognitive Services OpenAI User
Search Index Data Reader
```

Ingestion/administration uses separate permissions rather than giving
the runtime identity broad write access.

## 19.3 GitHub OIDC

GitHub authenticates to Azure with short-lived federated identity
tokens. No long-lived Azure client secret is required in GitHub.

## 19.4 Authorization guard

Tool authorization is checked in application code.

## 19.5 Retrieval filtering

Sensitivity is filtered before context is passed to the LLM.

## 19.6 Failure classification

The reliability layer distinguishes transient failures, malformed
responses, persistent validation failures, authentication failures, and
rate limiting instead of retrying every error identically.

## 19.7 Cache isolation

The cache-key design includes tenant, caller authorization scope, data
version, prompt version, and model version. Semantic similarity alone is
not considered safe for a role-scoped/multi-tenant cache.

------------------------------------------------------------------------

# 20. Phase 15 --- Testing and final validation

From repository root:

``` bash
pytest tests/ -v
```

Final validated result:

``` text
37 passed
```

Lint:

``` bash
ruff check src/ monitoring/ scripts/ rag/ agentic/ tests/
```

Final result:

``` text
All checks passed!
```

Terraform:

``` bash
terraform -chdir=terraform fmt -check -recursive
terraform -chdir=terraform validate
```

Final validation:

``` text
Success! The configuration is valid.
```

Check whitespace:

``` bash
git diff --check
```

On Windows, LF-to-CRLF warnings may appear. Those warnings are not
themselves a failed `git diff --check`.

## Final live validation chain

The paid end-to-end test successfully exercised:

``` text
MCP tool
 -> authorization
 -> Azure OpenAI embedding HTTP 200
 -> Azure AI Search
 -> GPT reranking HTTP 200
 -> grounding
 -> GPT generation HTTP 200
 -> grounded response
```

This is the key proof that the agentic/RAG code was not only unit-tested
with stubs.

------------------------------------------------------------------------

# 21. Azure Portal click-by-click verification

Use these steps before a demo or before teardown.

## Resource group

1.  Azure Portal.
2.  Search **Resource groups**.
3.  Open `rg-nakoba-dev`.
4.  Confirm the expected resources are present.

## Azure ML workspace

1.  Search **Machine Learning**.
2.  Open `mlw-nakoba-dev`.
3.  Launch Azure ML Studio.
4.  Open **Compute** → verify `cpu-cluster-dev`.
5.  Open **Data** → verify registered claims data.
6.  Open **Jobs** → inspect completed training/evaluation jobs.
7.  Open **Models** → inspect `nakoba-escalation-risk`.
8.  Open **Endpoints** → **Real-time endpoints**.
9.  Open `nakoba-escalation-risk-ep`.
10. Confirm deployment `champion`.
11. Confirm traffic is 100% to champion.
12. Inspect logs/metrics if troubleshooting.

## Azure OpenAI

1.  Resource group → `oai-nakoba-dev`.
2.  Inspect **Resource Management / Identity**.
3.  Inspect **Access control (IAM)**.
4.  Open the Azure AI/Foundry experience associated with the resource if
    needed.
5.  Inspect model deployments:
    -   embedding deployment;
    -   chat deployment.

## Azure AI Search

1.  Resource group → `srch-nakoba-dev`.
2.  Open **Indexes**.
3.  Select `nakoba-rag-dev`.
4.  Inspect fields and vector configuration.
5.  Use Search explorer to inspect indexed demo content.
6.  Open **Access control (IAM)** to verify data-plane roles.

## Managed identity

1.  Resource group → `id-nakoba-endpoint-dev`.
2.  Open **Overview**.
3.  Record/inspect client ID and principal/object ID.
4.  Open **Azure role assignments** if available.
5.  Verify only required access is granted.

## GitHub Actions

1.  GitHub repository.
2.  **Actions**.
3.  Open latest CI run.
4.  Confirm lint/test/Terraform/secret-scan jobs.
5.  Open latest CD run.
6.  Inspect Terraform apply, training, registration, evaluation, and
    promotion gate.

------------------------------------------------------------------------

# 22. Troubleshooting --- errors encountered and fixes

This section records the important failures encountered during the
actual build.

## 22.1 Terraform backend was not configured

**Symptom:** `terraform init` could not use the intended remote backend.

**Cause:** Backend configuration had not been populated/uncommented.

**Fix:**

``` hcl
resource_group_name  = "rg-tfstate"
storage_account_name = "sttfstatenakoba"
container_name        = "tfstate"
key                   = "nakoba-dev.tfstate"
```

Then:

``` bash
terraform init -reconfigure \
  -backend-config=envs/dev-backend.tfbackend
```

**Lesson:** Configure durable state before building dependent
infrastructure.

------------------------------------------------------------------------

## 22.2 Azure compute quota / LowPriority issue

**Symptom:** Compute provisioning or jobs failed because the requested
capacity was unavailable.

**Cause:** Subscription/regional quota and/or VM family availability.

**Fix:** Inspect quota and choose an available VM SKU/capacity. The
final dev compute used `Standard_DS2_v2`.

**Lesson:** VM SKU is an operational dependency, not merely a YAML
preference.

------------------------------------------------------------------------

## 22.3 Application Insights drift

**Symptom:** Terraform plan showed unexpected changes to Application
Insights.

**Cause:** Azure-populated/default properties differed from the original
configuration/state assumptions.

**Fix:** Inspect real Azure state and Terraform state, then codify
intentional configuration rather than blindly applying drift.

**Lesson:** Always review plans. Drift can be platform behavior rather
than unauthorized human change.

------------------------------------------------------------------------

## 22.4 Failed compute existed in Azure but not Terraform state

**Symptom:** A compute target appeared in Azure after a failed attempt
but Terraform did not own it correctly.

**Fix:** Inspect both Azure and Terraform state before recreating or
deleting the resource.

``` bash
terraform state list
az ml compute list -g "$RG" -w "$WS" -o table
```

**Lesson:** Failed control-plane operations can leave partial cloud
resources.

------------------------------------------------------------------------

## 22.5 Azure ML CLI extension permissions on Windows

**Symptom:** Azure ML CLI extension installation/update failed or
behaved inconsistently.

**Fix:** Verify Azure CLI installation, extension path/permissions, and
reinstall/update the `ml` extension when needed.

``` bash
az extension remove --name ml
az extension add --name ml --yes
```

Use this only when extension corruption/versioning is actually the
problem.

------------------------------------------------------------------------

## 22.6 MLflow/runtime dependency mismatch

**Symptom:** Model environment/deployment failed because the serving
runtime did not contain compatible dependencies.

**Cause:** Training and serving environment versions were not aligned.

**Fix:** Pin the environment and deploy the validated environment
version. The final champion references `nakoba-train-env:3`.

**Lesson:** The environment is part of the model artifact contract.

------------------------------------------------------------------------

## 22.7 Endpoint managed identity YAML/schema issue

**Symptom:** Endpoint creation rejected the identity configuration.

**Fix:** Use the Azure ML endpoint schema and supply the user-assigned
identity resource ID through the expected environment placeholder.

``` bash
export ENDPOINT_IDENTITY_ID="<resource-id>"
```

**Lesson:** Azure resource identity syntax and Azure ML YAML identity
syntax are not interchangeable.

------------------------------------------------------------------------

## 22.8 CLI environment placeholder did not expand as expected

**Symptom:** A YAML placeholder remained unresolved.

**Fix:** Where appropriate, use `--set` to explicitly override the YAML
field at submission time.

**Lesson:** Verify the final object Azure receives rather than assuming
shell interpolation occurred inside YAML.

------------------------------------------------------------------------

## 22.9 Managed endpoint deployment quota/networking problems

**Symptom:** Managed deployment provisioning failed.

**Fix:** Inspect deployment logs, regional quota, VM SKU, workspace
networking, and endpoint configuration independently. Avoid changing
multiple dimensions at once.

------------------------------------------------------------------------

## 22.10 Missing `AcrPull`

**Symptom:** Deployment could not pull the container image.

**Cause:** Runtime identity lacked permission to pull from Azure
Container Registry.

**Fix:** Grant the correct identity `AcrPull` at the ACR scope.

**Lesson:** Model access and container-image access are separate
permissions.

------------------------------------------------------------------------

## 22.11 Missing inference server dependency

**Symptom:** Container started incorrectly or the endpoint failed
readiness.

**Cause:** Serving environment lacked the required Azure ML inference
runtime/server package.

**Fix:** Add the inference dependency to the serving environment,
rebuild/register the environment, and redeploy.

------------------------------------------------------------------------

## 22.12 Feature schema mismatch: categorical feature count

**Symptom:** Endpoint scoring failed because the incoming schema did not
match the trained model preprocessing schema.

**Cause:** Serving input/preprocessing and training features had
diverged.

**Fix:** Reuse the same feature definitions and categorical handling
between training and serving.

**Lesson:** Training-serving skew can be a schema failure, not only a
statistical problem.

------------------------------------------------------------------------

## 22.13 Git Bash changed `/subscriptions/...` and Azure reported `MissingSubscription`

**Symptom:** Azure CLI reported a misleading subscription/resource-ID
error even though the subscription ID was valid.

**Environment:** Windows + Git Bash/MINGW64.

**Cause:** MSYS path conversion rewrote `/subscriptions/...`.

**Fix:**

``` bash
export MSYS_NO_PATHCONV=1
```

Then rerun the Azure CLI command.

**Lesson:** On Windows Git Bash, validate what the shell is doing to
slash-prefixed Azure resource IDs before debugging Azure itself.

------------------------------------------------------------------------

## 22.14 GitHub OIDC PR identity did not match main-branch identity

**Symptom:** Azure login succeeded in one GitHub context but failed in
another.

**Cause:** Federated credential subject mismatch.

**Fix:** Create federated credentials matching the exact GitHub subjects
required for PR and main workflows.

**Lesson:** OIDC federation is exact-match identity configuration.

------------------------------------------------------------------------

## 22.15 GitHub Actions Terraform needed Azure permissions beyond login

**Symptom:** OIDC login succeeded, but Terraform operations failed.

**Cause:** Authentication and authorization are separate. The service
principal was authenticated but lacked a required Azure role.

**Fix:** Add only the required scoped RBAC roles, including data-plane
permissions where necessary.

------------------------------------------------------------------------

## 22.16 Apparent Azure ML API-version error was caused by empty shell variables

**Symptom:** CLI output suggested an API/version problem.

**Cause:** Resource-group/workspace variables were empty.

**Fix:**

``` bash
echo "$RG"
echo "$WS"
```

Re-export:

``` bash
export RG="rg-nakoba-dev"
export WS="mlw-nakoba-dev"
```

**Lesson:** Check command inputs before interpreting a cloud error as a
platform defect.

------------------------------------------------------------------------

## 22.17 `az ml job download --all` problem

**Symptom:** Downloading all job outputs behaved incorrectly.

**Fix:** Download the named output explicitly:

``` bash
az ml job download \
  --name "$JOB_NAME" \
  --output-name evaluation_output \
  --download-path artifacts/... \
  -g "$RG" \
  -w "$WS"
```

This pattern is also used by CD.

------------------------------------------------------------------------

## 22.18 DS3 quota issue

**Symptom:** A larger requested VM size could not provision.

**Fix:** Move to the available `Standard_DS2_v2` size for the portfolio
workload.

------------------------------------------------------------------------

## 22.19 `az ml job stream` local `Incorrect padding`

**Symptom:** Local CLI streaming threw a decoding/padding error while
the Azure job continued remotely.

**Fix:** Do not assume the remote job failed. Poll status:

``` bash
az ml job show \
  --name "$JOB_NAME" \
  -g "$RG" \
  -w "$WS" \
  --query status \
  -o tsv
```

**Lesson:** Separate client-side observability failure from server-side
workload failure.

------------------------------------------------------------------------

## 22.20 Champion baseline lacked p95 latency

**Symptom:** Promotion comparison could not make an apples-to-apples
latency decision.

**Fix:** Run champion and challenger through the same evaluator and
produce p95 for both.

------------------------------------------------------------------------

## 22.21 Initial latency comparison was not apples-to-apples

**Fix:** Use one evaluation path and equivalent conditions for champion
and challenger.

**Lesson:** A governance metric is useful only if measurement
methodology is consistent.

------------------------------------------------------------------------

## 22.22 Equal F1 challenger was blocked

**Symptom:** The workflow reported a blocked promotion.

**Interpretation:** This was an expected governance outcome, not a
broken pipeline.

**Fix:** CD was updated so governance exit code `2` is reported as
`BLOCKED`, while unexpected exit codes still fail technically.

------------------------------------------------------------------------

## 22.23 CI YAML heredoc/scanner error

**Symptom:** GitHub Actions workflow YAML failed parsing.

**Cause:** Embedded heredoc/Python indentation and YAML structure
interacted incorrectly.

**Fix:** Correct YAML indentation and shell block boundaries; validate
before pushing.

------------------------------------------------------------------------

## 22.24 Promotion tests broke after function signature expansion

**Symptom:** Existing tests failed after adding new promotion inputs.

**Fix:** Update tests and call sites together when governance contracts
change.

------------------------------------------------------------------------

## 22.25 Git HTTPS push failed

**Fix:** Switch the repository remote/authentication to SSH after GitHub
SSH authentication was configured.

Verify:

``` bash
git remote -v
ssh -T git@github.com
```

------------------------------------------------------------------------

## 22.26 Pydantic / MCP dependency conflict

**Symptom:** Agentic dependencies could not resolve or imports failed.

**Fix:** Pin compatible package versions in `requirements-agentic.txt`
and test them together.

**Lesson:** Agent protocol libraries and validation libraries evolve
quickly; dependency pinning is part of reproducibility.

------------------------------------------------------------------------

## 22.27 Terraform backend file was ignored by Git

**Symptom:** Required backend configuration was not included as
expected.

**Fix:** Add an intentional `.gitignore` exception for the non-secret
backend configuration file if appropriate.

Never commit credentials or access keys.

------------------------------------------------------------------------

## 22.28 OIDC subject required exact repository identity

**Symptom:** Federated login failed despite apparently correct
repository naming.

**Fix:** Use the exact owner/repository/branch or PR subject Azure
receives. Do not approximate the GitHub subject string.

------------------------------------------------------------------------

## 22.29 Node runtime warnings in GitHub Actions

**Symptom:** GitHub emitted Node runtime warnings for an action.

**Resolution:** Warnings were non-fatal when the action still executed
successfully.

**Lesson:** Distinguish deprecation warnings from failed workflow steps.

------------------------------------------------------------------------

## 22.30 CD missing Python dependencies

**Symptom:** CD synthetic-data/evaluation steps failed with missing
modules such as NumPy or pandas.

**Fix:** Explicitly install workflow-time dependencies before invoking
scripts.

Example from CD:

``` bash
python -m pip install --upgrade pip
python -m pip install numpy pandas
```

and for the promotion gate:

``` bash
python -m pip install "pandas==2.2.1"
```

------------------------------------------------------------------------

## 22.31 Azure ML data version based on full Git SHA was unsuitable

**Symptom:** Asset version naming caused validation problems.

**Fix:** Use the first 12 characters:

``` bash
DATA_VERSION="${GITHUB_SHA:0:12}"
```

This still preserves commit linkage while staying manageable.

------------------------------------------------------------------------

## 22.32 Azure ML model version required a positive integer

**Symptom:** Challenger model registration rejected a nonconforming
version.

**Fix:** Use:

``` bash
VERSION="${GITHUB_RUN_ID}"
```

------------------------------------------------------------------------

## 22.33 Process substitution `/dev/fd/63` failed with Azure CLI on Windows

**Symptom:** A command using:

``` bash
--request-file <(echo '...')
```

failed because Windows Azure CLI could not consume the Git Bash
pseudo-file path.

**Fix:** Write JSON to a real file and pass that file.

------------------------------------------------------------------------

## 22.34 Default Azure credential chain vs live Azure ML prediction

**Symptom:** Agent tool authentication did not initially reach the live
Azure ML endpoint correctly.

**Fix:** Use the intended Azure identity flow and verify token
acquisition separately from model scoring.

------------------------------------------------------------------------

## 22.35 Entra authentication exceptions needed normalized handling

**Symptom:** Authentication failures surfaced as inconsistent
exceptions.

**Fix:** Normalize auth failures into a known 401/auth category and do
not treat them as transient retry candidates.

------------------------------------------------------------------------

## 22.36 Search service unavailable in East US 2

**Symptom:** Terraform could not provision Azure AI Search in `eastus2`
due to capacity.

**Fix:** Add a separate `search_location` variable and provision Search
in `eastus`.

``` hcl
variable "search_location" {
  default = "eastus"
}
```

**Lesson:** A multi-service architecture should permit per-service
region choices where platform capacity requires them.

------------------------------------------------------------------------

## 22.37 Broad text replacement accidentally modified Terraform incorrectly

**Symptom:** A broad `sed` edit inserted `search_location` where it did
not belong.

**Detection:** `terraform validate`.

**Fix:** Revert/correct the unintended edits and rerun:

``` bash
terraform fmt -recursive
terraform validate
```

**Lesson:** Automated text replacement is fast but unsafe without
immediate validation.

------------------------------------------------------------------------

## 22.38 RAI policy drift

**Symptom:** Terraform detected differences around Azure OpenAI RAI
policy configuration.

**Fix:** Codify the intended policy (`Microsoft.DefaultV2`) rather than
repeatedly accepting drift.

------------------------------------------------------------------------

## 22.39 Search provisioning was slow

**Symptom:** Provisioning appeared stuck.

**Fix:** Check Azure provisioning state rather than interrupting a valid
long-running control-plane operation.

------------------------------------------------------------------------

## 22.40 Local developer could manage Search resource but not index data

**Symptom:** Control-plane operations worked while data-plane index
operations failed.

**Cause:** Azure Search separates management and data permissions.

**Fix:** Grant the appropriate data roles for the developer/ingestion
identity, such as Search Index Data Contributor, while keeping runtime
read-only.

------------------------------------------------------------------------

## 22.41 Search index creation failed after token expiration

**Symptom:** An operation that had previously authenticated began
failing.

**Fix:** Reauthenticate:

``` bash
az login
```

Then rerun the data-plane operation.

------------------------------------------------------------------------

## 22.42 Python import issue during ingestion

**Symptom:** Running a script directly caused package import problems.

**Fix:**

``` bash
python -m rag.ingest_live
```

from the repository root.

------------------------------------------------------------------------

## 22.43 Combined Search and Cognitive scopes caused `AADSTS70011`

**Symptom:** Token acquisition failed with invalid-scope error.

**Cause:** Resource scopes for different Azure services were combined
incorrectly.

**Fix:** Request tokens separately for the resource being called. Do not
combine Azure Search and Cognitive Services scopes into one token
request.

------------------------------------------------------------------------

## 22.44 Tenant login / MFA

**Symptom:** Azure CLI authentication required tenant-specific
interactive authentication/MFA.

**Fix:** Complete the required Entra login flow for the correct tenant,
then verify:

``` bash
az account show
```

------------------------------------------------------------------------

## 22.45 Azure OpenAI returned 401 despite an apparently relevant role

**Symptom:** Live OpenAI data-plane request returned 401.

**Cause:** The local developer identity did not yet have the effective
data-plane access required by the actual call.

**Fix:** Inspect the caller identity and role assignments. The
successful local configuration included the required Cognitive
Services/OpenAI data-plane roles. Wait for RBAC propagation if
necessary, then acquire a fresh token and retry.

**Lesson:** Role names that sound similar are not interchangeable, and
control-plane access does not prove data-plane access.

------------------------------------------------------------------------

## 22.46 Correct RAG document retrieved but grounding failed

**Symptom:** The top Search result was correct, but the grounding check
rejected it.

**Observed:** Raw Azure hybrid/RRF score was around `0.0333`, while the
grounding threshold was `0.35`.

**Root cause:** The threshold expected normalized relevance but was
being applied to an RRF ranking score.

**Fix:** Preserve raw Azure score separately and use the normalized GPT
reranker score for grounding.

This was one of the most important RAG correctness fixes in the project.

------------------------------------------------------------------------

## 22.47 Server-side role mapping was required for MCP knowledge access

**Risk:** Allowing the agent/model to choose `allowed_sensitivity` would
let model output influence authorization.

**Fix:** MCP accepts the authenticated/caller role and the server maps
it to permitted sensitivity levels.

**Lesson:** The LLM can request an action; it cannot define its own
authorization scope.

------------------------------------------------------------------------

## 22.48 Terraform plan binaries were accidentally executed

**Symptom:** Shell returned an `Exec format` style error.

**Cause:** A `.tfplan` binary was treated like an executable command.

**Fix:** Remove unnecessary local plan files and use them only with
Terraform:

``` bash
terraform apply tfplan
```

Do not execute `./tfplan`.

------------------------------------------------------------------------

## 22.49 Windows LF/CRLF warnings

**Symptom:** Git displayed LF-to-CRLF conversion warnings.

**Resolution:** These were warnings, not failures. `git diff --check`
remained the relevant whitespace check.

------------------------------------------------------------------------

# 23. Cost control

For a dev/portfolio environment, distinguish resources that can scale to
zero from provisioned services.

The final ML compute cluster has:

``` text
min_instances = 0
max_instances = 1
```

so it can scale down when idle.

The managed online deployment, however, uses:

``` text
Standard_DS2_v2
instance_count = 1
```

and should be treated as an intentionally running serving resource until
deleted.

Azure AI Search Basic is also a provisioned service and should be
considered when deciding whether to leave a demo environment running.

Before deleting anything, inventory:

``` bash
export RG="rg-nakoba-dev"

az resource list \
  --resource-group "$RG" \
  --query "[].{Name:name,Type:type,Location:location}" \
  -o table

az ml compute list \
  --resource-group "$RG" \
  --workspace-name "mlw-nakoba-dev" \
  -o table

az ml online-endpoint show \
  --name nakoba-escalation-risk-ep \
  --resource-group "$RG" \
  --workspace-name "mlw-nakoba-dev" \
  -o json
```

Do not make repeated paid inference calls merely to keep testing after
the E2E path has already been proven.

------------------------------------------------------------------------

# 24. Safe teardown

## Important distinction

The dev environment and Terraform state are deliberately separate:

``` text
rg-nakoba-dev   -> application/dev resources
rg-tfstate      -> Terraform remote state
```

If the objective is to stop dev-resource costs while preserving the
backend, do **not** delete `rg-tfstate`.

## Before teardown

Confirm the repository is pushed:

``` bash
git status
git log --oneline -5
git remote -v
```

Run:

``` bash
git status --short
```

It should be clean except for intentionally uncommitted local
documentation/source bundles.

Verify remote:

``` bash
git fetch origin
git status
```

## Preferred IaC teardown

From the Terraform directory:

``` bash
cd ~/Downloads/nakoba/terraform

export MSYS_NO_PATHCONV=1

terraform init \
  -backend-config=envs/dev-backend.tfbackend

terraform plan \
  -destroy \
  -var-file=envs/dev.tfvars
```

**Read the destroy plan before continuing.**

If the plan correctly represents the Terraform-managed dev resources:

``` bash
terraform destroy \
  -var-file=envs/dev.tfvars
```

Terraform will ask for confirmation.

### Important: ML-plane resources

Some Azure ML objects were created through `az ml` YAML/CLI rather than
Terraform. Terraform destroy may therefore not own every ML-plane
object.

Before or after Terraform destroy, inspect the resource group:

``` bash
az resource list \
  --resource-group rg-nakoba-dev \
  -o table
```

If the goal is complete dev-environment removal and the resource group
still exists with resources, the final cleanup can be the resource-group
deletion **only after you have confirmed there is nothing in that group
you intend to retain**:

``` bash
az group delete \
  --name rg-nakoba-dev \
  --yes
```

Do not run that command casually. Resource-group deletion is
destructive.

## Verify deletion

``` bash
az group exists --name rg-nakoba-dev
```

Expected after completed deletion:

``` text
false
```

Verify the Terraform state resource group still exists:

``` bash
az group exists --name rg-tfstate
```

If preserving state, expected:

``` text
true
```

------------------------------------------------------------------------

# 25. Rebuild after teardown

The project is designed to be recreated.

## Step 1 --- clone

``` bash
git clone <repo-url>
cd E2E-ML-PROJECT
```

## Step 2 --- authenticate

``` bash
az login
az account set --subscription "<subscription>"
export MSYS_NO_PATHCONV=1
```

## Step 3 --- initialize Terraform backend

``` bash
terraform -chdir=terraform init \
  -backend-config=envs/dev-backend.tfbackend
```

If the old state says resources exist but the resource group was
manually deleted, first run a refresh/plan and inspect carefully.
Terraform should discover missing remote objects and propose recreation,
but never apply without reviewing the plan.

## Step 4 --- infrastructure

``` bash
terraform -chdir=terraform plan \
  -var-file=envs/dev.tfvars

terraform -chdir=terraform apply \
  -var-file=envs/dev.tfvars
```

## Step 5 --- recreate ML-plane assets

Recreate/register:

-   Azure ML environment;
-   synthetic data asset;
-   training job;
-   registered model;
-   endpoint;
-   deployment.

## Step 6 --- recreate RAG data plane

After Search/OpenAI exist and RBAC is effective:

``` bash
python -m rag.create_index
python -m rag.ingest_live
```

## Step 7 --- validate

``` bash
pytest tests/ -v
ruff check src/ monitoring/ scripts/ rag/ agentic/ tests/
terraform -chdir=terraform validate
```

Then perform one controlled live ML and RAG/MCP validation.

------------------------------------------------------------------------

# 26. Interview walkthrough

A concise senior-level story is:

> I built Nakoba as an end-to-end Azure MLOps and agentic AI reference
> platform. I provisioned the Azure foundation with Terraform and remote
> state, used Azure ML YAML for ML-plane objects, and built a GitHub
> Actions pipeline authenticated to Azure through OIDC rather than
> long-lived secrets. The classical ML path trains and registers an
> XGBoost warranty-escalation model, evaluates champion and challenger
> using F1, p95 latency, and segment-level metrics, and serves the
> approved model through an AAD-protected managed endpoint. I then
> extended the same platform with Azure OpenAI, Azure AI Search,
> grounded hybrid RAG, and an MCP tool layer. The RAG path applies
> authorization and sensitivity filtering before retrieval, combines
> BM25 and vector search, reranks the candidates, checks normalized
> relevance before generation, and abstains when evidence is weak. MCP
> exposes both the ML prediction and dealer-knowledge capabilities while
> keeping authorization server-side. I validated the complete live path
> and also built CI tests, failure classification, rollback, and
> reproducible teardown/rebuild procedures.

When asked for a troubleshooting example, use the RRF/grounding problem:

> The correct document was retrieved first, but the RAG system abstained
> because I had compared Azure's reciprocal-rank-fusion score, roughly
> 0.03, to a 0.35 normalized relevance threshold. Instead of lowering
> the threshold until the demo passed, I separated score semantics: I
> preserved the Azure score for retrieval diagnostics, added a
> normalized reranker score from 0 to 1, and applied the grounding
> threshold to that score. That fixed the immediate issue and made the
> architecture correct for future documents.

For security:

> I deliberately kept the LLM out of the authorization boundary. Caller
> role is validated server-side, role maps to allowed document
> sensitivity, and Azure Search applies the sensitivity filter before
> context reaches the model. The endpoint identity receives only the
> data-plane permissions it needs, and GitHub uses OIDC instead of an
> Azure client secret.

For governance:

> A blocked model promotion is not a failed deployment. My pipeline
> distinguishes a governance block from a technical error. A challenger
> has to satisfy F1, p95 latency, and segment-level checks before it is
> eligible for controlled promotion.

------------------------------------------------------------------------

# 27. Final completion checklist

Use this before calling the project complete.

-   [x] Git repository created and pushed
-   [x] Terraform remote state configured
-   [x] Azure infrastructure provisioned
-   [x] Azure ML workspace provisioned
-   [x] Compute configured
-   [x] Synthetic data generated and registered
-   [x] Training completed
-   [x] Model registered
-   [x] Managed online endpoint deployed
-   [x] Live ML prediction validated
-   [x] GitHub Actions CI implemented
-   [x] GitHub OIDC implemented
-   [x] CD training/registration/evaluation implemented
-   [x] Champion/challenger governance implemented
-   [x] Azure OpenAI provisioned
-   [x] Azure AI Search provisioned
-   [x] RAG index created
-   [x] Demo knowledge ingested
-   [x] Hybrid retrieval implemented
-   [x] Reranking implemented
-   [x] Grounding/abstention implemented
-   [x] MCP tools implemented
-   [x] Server-side authorization implemented
-   [x] Live MCP → RAG → Azure path validated
-   [x] 37 tests passed
-   [x] Ruff passed
-   [x] Terraform validation passed
-   [x] Implementation guide created
-   [ ] Commit final documentation
-   [ ] Push final documentation to GitHub
-   [ ] Verify GitHub remote contains final documentation
-   [ ] Destroy Azure dev resources
-   [ ] Verify `rg-nakoba-dev` is gone
-   [ ] Preserve GitHub repository and Terraform-state strategy

------------------------------------------------------------------------

## Final note

This repository is a portfolio/reference implementation. The synthetic
warranty claims and demo repair/service documents are intentionally
non-proprietary. The architecture demonstrates production-style
controls, but a real production rollout would still require
organization-specific network policy, private connectivity decisions,
logging/retention standards, threat modeling, data governance, SLOs,
operational ownership, and formal security/compliance review.
