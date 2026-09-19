# Nakoba

**A full-lifecycle MLOps platform on Azure ML, built around a connected-vehicle warranty/service-escalation risk model.**

Nakoba is a personal project, built on my own initiative — not an employer deliverable. I built it to demonstrate, end to end, the same platform-ownership patterns I apply professionally: infrastructure as code, CI/CD-gated model promotion, managed endpoint deployment, drift/monitoring, and rollback — without the scope boundaries of any single employer's backlog. It's built on Azure ML and Azure AI Foundry-adjacent patterns specifically, not ported from another cloud.

## The problem it solves

Predict which incoming warranty/service claims for a connected vehicle or equipment fleet are at high risk of escalating into a costly, disputed, or SLA-breaching repair — early enough in intake that a senior technician gets routed to it, and parts get pre-staged at the dealer before the vehicle arrives.

I picked this domain because it generalizes across any manufacturer with sensor-equipped products and a dealer/service network (automotive, industrial equipment, appliances) — it's not built for or copied from any single company's internals.

## What's actually here vs. what's narrated

This repo prioritizes the platform scaffolding — the part that's usually invisible in a portfolio — over model sophistication. The model itself (XGBoost classifier) is intentionally simple. The infrastructure, promotion gates, identity, and monitoring around it are the point.

## Architecture at a glance

```
Git (source of truth)
  │
  ├─ Terraform ─────────► Azure ML workspace, compute, ACR, Key Vault,
  │                        networking, managed identities  (all declarative)
  │
  ├─ GitHub Actions CI ──► lint, unit tests, Terraform plan, secret scan
  │                        on every PR — nothing merges without green checks
  │
  ├─ GitHub Actions CD ──► on merge to main: apply infra, build+push env
  │                        image, submit training job, register candidate
  │                        model with metrics + lineage metadata
  │
  └─ Promotion gate ─────► candidate compared against production champion
                            on F1, latency, and per-segment fairness before
                            traffic shifts — never an automatic promotion
```

## Directory layout

| Path | What it is | Why it's separate |
|---|---|---|
| `terraform/` | All Azure infra as code (workspace, networking, identity, ACR, Key Vault) | Workspace objects are deployed as versioned code, not clicked into the portal — see `docs/DECISIONS.md` #1 |
| `environments/` | Pinned conda environment for training/serving | Runtime version is a release artifact, not an assumption |
| `src/` | Training code, feature definitions, scoring script | The actual model logic — deliberately the smallest part of the repo |
| `jobs/` | Azure ML job YAMLs (training job, hyperparameter sweep) | Jobs are declarative and reproducible, not run interactively |
| `deploy/` | Managed online endpoint + deployment config | Endpoint/deployment are versioned config, not portal clicks |
| `monitoring/` | Drift checks, the 4-layer monitoring definitions | Uptime ≠ model health — see `docs/DECISIONS.md` #6 |
| `.github/workflows/` | CI (every PR) and CD (on merge to main) pipelines | Build once, promote the same artifact through every stage |
| `docs/DECISIONS.md` | Every non-obvious design decision, and what I rejected | The "why," not just the "what" |
| `scripts/rollback.sh` | One-command traffic rollback to the prior deployment | Rollback has to be a config change, not an incident-time investigation |

## Quickstart

```bash
# 1. Provision the Azure ML workspace and supporting infra
cd terraform && terraform init && terraform plan -var-file=envs/dev.tfvars

# 2. Build and register the training environment
az ml environment create -f environments/train-env.yml -g <rg> -w <workspace>

# 3. Submit the training job (produces a lineage-tracked model)
az ml job create -f jobs/train-job.yml -g <rg> -w <workspace>

# 4. Register the trained model (only after evaluation gate passes)
az ml model create -f jobs/model-registration.yml -g <rg> -w <workspace>

# 5. Deploy behind a managed online endpoint (canary traffic split)
az ml online-endpoint create -f deploy/endpoint.yml -g <rg> -w <workspace>
az ml online-deployment create -f deploy/deployment.yml -g <rg> -w <workspace>
```

Full step-by-step, including what each command actually does and the alternative I rejected at each step, is in `docs/DECISIONS.md`.

## Status

Actively built as a portfolio reference implementation. Not connected to any real telemetry feed — `data/` uses a synthetic warranty-claims generator (`src/generate_synthetic_data.py`) so the repo is runnable without any proprietary or real customer data.
