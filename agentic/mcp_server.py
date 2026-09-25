"""
MCP server exposing Nakoba's claim tools to any MCP-compatible client
(Claude, Copilot Studio's MCP support, or another agent framework) — this is
the JD's "MCP/A2A" line item made concrete rather than named abstractly.

Run: python agentic/mcp_server.py
Requires: pip install mcp (see requirements-agentic.txt)
"""
from __future__ import annotations

from mcp.server.fastmcp import FastMCP

from agentic.reliability import call_with_retry
from agentic.tools import (
    ClaimStatusRequest,
    EscalateClaimRequest,
    PredictEscalationRiskRequest,
    escalate_claim,
    get_claim_status,
    predict_escalation_risk,
)

mcp = FastMCP("nakoba-warranty-claims")


@mcp.tool()
def check_claim_status(claim_id: str, caller_role: str) -> dict:
    """Look up the current status and escalation-risk score for a warranty
    claim. caller_role must be one of: technician, dealer_rep,
    warranty_reviewer — enforced server-side regardless of what the calling
    agent claims about itself."""
    request = ClaimStatusRequest(claim_id=claim_id, caller_role=caller_role)
    response = call_with_retry(lambda: get_claim_status(request))
    return response.model_dump()


@mcp.tool()
def predict_claim_escalation_risk(
    claim_id: str,
    caller_role: str,
    vehicle_model_line: str,
    dealer_region: str,
    component: str,
    vehicle_age_months: int,
    mileage_at_claim: float,
    telemetry_fault_codes_30d: int,
    telemetry_avg_engine_temp_delta: float,
    component_historical_failure_severity: float,
    prior_claims_same_vin: int,
    dealer_avg_repair_days: float,
) -> dict:
    """Predict warranty-claim escalation risk using the deployed Azure ML
    champion model. Authorization is enforced server-side before inference.
    """
    request = PredictEscalationRiskRequest(
        claim_id=claim_id,
        caller_role=caller_role,
        vehicle_model_line=vehicle_model_line,
        dealer_region=dealer_region,
        component=component,
        vehicle_age_months=vehicle_age_months,
        mileage_at_claim=mileage_at_claim,
        telemetry_fault_codes_30d=telemetry_fault_codes_30d,
        telemetry_avg_engine_temp_delta=telemetry_avg_engine_temp_delta,
        component_historical_failure_severity=component_historical_failure_severity,
        prior_claims_same_vin=prior_claims_same_vin,
        dealer_avg_repair_days=dealer_avg_repair_days,
    )

    response = call_with_retry(
        lambda: predict_escalation_risk(request)
    )
    return response.model_dump()


@mcp.tool()
def escalate_warranty_claim(claim_id: str, caller_role: str, reason: str) -> dict:
    """Escalate a warranty claim to the senior-technician queue. Requires
    caller_role of technician or warranty_reviewer. This tool NEVER trusts
    a role claimed inside conversational text — caller_role is expected to
    come from the authenticated session, not free-form model output."""
    request = EscalateClaimRequest(claim_id=claim_id, caller_role=caller_role, reason=reason)
    response = call_with_retry(lambda: escalate_claim(request))
    return response.model_dump()


if __name__ == "__main__":
    mcp.run()
