# Design Decisions

Each entry: the decision, why, and what I rejected.

---

### 1. Git as the single source of truth for workspace objects

**Decision:** Environments, datasets, pipelines, compute targets, and endpoints are all defined declaratively in Terraform / YAML and deployed through CI/CD — never created by clicking in the Azure ML Studio portal.

**Why:** A portal-clicked workspace can't be reproduced. Six months later, nobody can say exactly what settings were used. Standing up a second environment (dev → staging) should mean re-running a pipeline against a different `.tfvars` file, not someone's memory of what they clicked.

**Rejected:** Manual portal setup with documentation in a wiki. Wikis drift from reality within weeks; code doesn't, because CI enforces that the code *is* the reality.

---

### 2. Terraform over ARM/Bicep for the base infra, `az ml` CLI + YAML for ML-plane objects

**Decision:** Terraform provisions the Azure resource layer (resource group, workspace, storage, Key Vault, ACR, networking, managed identities). The Azure ML plane objects (environments, jobs, endpoints) are defined as `az ml` YAML, which is the native and more actively maintained format for that layer.

**Why:** Terraform's plan/apply gives a reviewable diff before anything touches an account you might not own outright (useful if this were ever handed to a team). The ML-plane YAML format is what Azure ML's own CLI/SDK expects natively — fighting that with Terraform's (weaker) azurerm ML resources adds friction for no real benefit.

**Rejected:** Pure Bicep. Would work equally well; Terraform was chosen for provider-agnostic state and because it's the tool I have the deepest production reps in.

---

### 3. Build once, promote the same artifact

**Decision:** The training environment is built into a single Docker image, pushed to ACR tagged by digest (not `latest`), and that exact image is what every job and every deployment stage references.

**Why:** If you rebuild per environment, a dependency can silently resolve to a different version between the environment you validated and the one that goes to production — you lose the guarantee that what you tested is what you shipped.

**Rejected:** Rebuilding per stage from the same Dockerfile. Faster to set up, but breaks the reproducibility guarantee the whole registry/lineage story depends on.

---

### 4. Model registry gate before deployment eligibility

**Decision:** A trained model isn't deployable until it's registered with evaluation metrics, the training-data reference, and an approving reviewer attached as metadata (see `jobs/model-registration.yml`).

**Why:** Blob storage tells you where the bytes are. A registry tells you what the asset is and whether it's cleared for production. In a warranty context, that approval metadata is what a finance or service-quality reviewer needs months later — "why did the model flag this claim" has to be answerable from lineage, not memory.

**Rejected:** Treating any model artifact in blob storage as deployable directly. Faster, but has no audit trail and no promotion gate.

---

### 5. Managed online endpoint over self-managed AKS

**Decision:** Serving uses an Azure ML managed online endpoint.

**Why:** Single model, moderate/predictable traffic. Managed endpoints give built-in traffic-splitting (needed for canary), versioned deployments behind one stable URL, and managed scaling — without owning a Kubernetes control plane.

**Rejected — explicitly, with the trade-off named:** If this needed to sit alongside several other custom services (an MCP gateway, multiple FastAPI microservices with their own routing), I'd move to AKS. Managed endpoints are excellent for a model; they're not a general application host.

---

### 6. Four separate monitoring layers, not "endpoint is up"

**Decision:** `monitoring/` tracks infrastructure metrics, application/latency metrics, model-quality metrics, and business metrics (are flagged claims actually escalating at the predicted rate) as four distinct signals.

**Why:** An endpoint can report 99.99% uptime while the model has quietly stopped being useful. In a service network, a silently degraded model doesn't throw an error — it just routes claims to the wrong technicians for weeks before anyone notices.

**Rejected:** Uptime/latency-only alerting. Cheaper to build, blind to the failure mode that actually matters here.

---

### 7. Scoped managed identity per workload, not a shared service principal

**Decision:** The endpoint's compute uses a system-assigned managed identity with RBAC scoped only to the specific storage container and Key Vault secrets it needs.

**Why:** Blast radius. A compromised credential on a shared service principal exposes everything that principal touches. A scoped identity exposes only what that one workload legitimately needs, and there's no long-lived secret sitting in a pipeline YAML to leak.

**Rejected:** One shared service principal for all pipelines. Simpler to set up initially, much worse failure mode.

---

### 8. Feature store with point-in-time correctness

**Decision:** Features (e.g. "this component's historical failure severity for this vehicle model line") are defined once in `src/features.py` and computed identically for training and serving.

**Why:** Warranty data has a specific leakage risk: many fields get updated retroactively as a repair progresses. Without point-in-time correctness, training data can "see" information that wouldn't have actually been available at claim-intake time — the model looks great offline and fails in production.

**Rejected:** Recomputing features ad hoc in the training notebook and again in the serving path. This is exactly how training-serving skew happens.

---

### 9. Challenger vs. champion, never an automatic promotion

**Decision:** A new candidate model is compared against the current production model on validation F1, latency, and a per-segment consistency check (across vehicle model line / dealer region) before promotion — see `scripts/promote_challenger.py`.

**Why:** A model that's slightly more accurate overall but systematically worse for one region or model line is an operational-fairness problem, not just a performance number. Higher aggregate F1 alone isn't a promotion decision.

**Rejected:** Auto-promoting on any F1 improvement. Simple, but blind to segment-level regressions.

---

### 10. Rollback is a traffic/alias change, not a rebuild

**Decision:** The prior approved image digest, model version, and deployment config are always kept live at reduced traffic weight, so `scripts/rollback.sh` is a single `az ml online-endpoint update` traffic-split change.

**Why:** Designed before the release, not during the incident. Rollback under pressure needs to be boring.

**Rejected:** Redeploying from the last known-good Git commit during an incident. Works, but is slower and depends on CI/CD being healthy at the exact moment you need it least.
