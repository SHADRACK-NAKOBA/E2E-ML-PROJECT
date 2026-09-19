#!/usr/bin/env bash
# Rollback is a traffic-split change, not a rebuild or a redeploy.
# The prior approved deployment is always left live at reduced (but nonzero)
# traffic weight specifically so this script is a single command, not an
# incident-time investigation. See docs/DECISIONS.md #10.
#
# Usage: ./rollback.sh <endpoint-name> <resource-group> <workspace> <prior-deployment-name>

set -euo pipefail

ENDPOINT_NAME="${1:?endpoint name required}"
RESOURCE_GROUP="${2:?resource group required}"
WORKSPACE="${3:?workspace name required}"
PRIOR_DEPLOYMENT="${4:?prior (known-good) deployment name required}"

echo "Rolling ${ENDPOINT_NAME} back to deployment '${PRIOR_DEPLOYMENT}' at 100% traffic..."

az ml online-endpoint update \
  --name "${ENDPOINT_NAME}" \
  --resource-group "${RESOURCE_GROUP}" \
  --workspace-name "${WORKSPACE}" \
  --traffic "${PRIOR_DEPLOYMENT}=100"

echo "Rollback complete. Verifying traffic split:"
az ml online-endpoint show \
  --name "${ENDPOINT_NAME}" \
  --resource-group "${RESOURCE_GROUP}" \
  --workspace-name "${WORKSPACE}" \
  --query "traffic"
