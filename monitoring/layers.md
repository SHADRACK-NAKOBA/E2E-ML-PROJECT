# The Four Monitoring Layers

An endpoint can report 99.99% uptime while the model has quietly stopped
being useful. These are tracked as four separate signals, not one
"is it up" check — see `docs/DECISIONS.md` #6.

| Layer | What it tracks | Where | Alerts on |
|---|---|---|---|
| **Infrastructure** | Compute health — node availability, CPU/memory, autoscale events | Azure Monitor (Container Insights on the compute cluster / endpoint) | Node unhealthy, scale-to-zero failures |
| **Application** | Endpoint responsiveness — p50/p95/p99 latency, request rate, error rate | Application Insights (wired via `azurerm_application_insights.ml` in Terraform) | p99 latency doubling, 5xx rate > 1% |
| **Model** | Prediction quality on a delayed-labeled sample — F1/precision/recall as real outcomes come back | `monitoring/drift_check.py` + a scheduled Azure ML pipeline scoring a holdback sample against known outcomes | F1 drop beyond threshold on a rolling window |
| **Business** | Are flagged high-risk claims actually escalating into high-cost repairs at the predicted rate | A weekly job joining predictions against actual claim outcomes from the (synthetic, in this repo) claims system | Predicted-vs-actual escalation rate diverging |

The reason for separating these: a model that silently degrades doesn't
throw an error — it just routes claims to the wrong technicians for weeks
before anyone notices, while every infra/app dashboard stays green.

Latency is read by percentile, not average, because averages hide the tail:
if p50 holds steady while p99 doubles, that's cold starts / one unhealthy
instance / GPU or CPU saturation / a slow downstream call affecting a
subset of requests — not a reason to add compute reflexively. If p50, p95,
and p99 all move together, that's systemic, and gets correlated against
recent deployments first: rollback (`scripts/rollback.sh`) is the safer
first move over adding capacity if the timing lines up with a release.
