"""
Tools the agent (or an MCP client) can call. Every tool has an explicit
input/output schema — no integration that asks a model for arbitrary output
and hopes Python can parse it. Output is validated against the schema
before it reaches downstream code.
"""
from __future__ import annotations

from pydantic import BaseModel, Field

from agentic.azure_ml import invoke_escalation_model
from rag.guardrails import ActionAuthorizationGuard, AuthorizationDeniedError


class ClaimStatusRequest(BaseModel):
    claim_id: str
    caller_role: str


class ClaimStatusResponse(BaseModel):
    claim_id: str
    status: str
    escalation_risk_score: float | None = None
    top_weighted_factors: list[str] = Field(default_factory=list)


class PredictEscalationRiskRequest(BaseModel):
    claim_id: str
    caller_role: str
    vehicle_model_line: str
    dealer_region: str
    component: str
    vehicle_age_months: int = Field(ge=0)
    mileage_at_claim: float = Field(ge=0)
    telemetry_fault_codes_30d: int = Field(ge=0)
    telemetry_avg_engine_temp_delta: float
    component_historical_failure_severity: float = Field(ge=0)
    prior_claims_same_vin: int = Field(ge=0)
    dealer_avg_repair_days: float = Field(ge=0)


class PredictEscalationRiskResponse(BaseModel):
    claim_id: str
    escalation_risk_score: float = Field(ge=0, le=1)
    high_risk: bool
    top_weighted_factors: list[str] = Field(default_factory=list)


class EscalateClaimRequest(BaseModel):
    claim_id: str
    caller_role: str
    reason: str = Field(min_length=1, max_length=500)


class EscalateClaimResponse(BaseModel):
    claim_id: str
    escalated: bool
    routed_to: str


_guard = ActionAuthorizationGuard()

# In-memory stand-in for a claims backend — a real deployment calls the
# actual claims system here. Kept simple and swappable so the tool logic
# (validation, authz, error shape) is what this module demonstrates.
_FAKE_CLAIMS_DB = {
    "CLM-0000001": {"status": "intake", "escalation_risk_score": 0.72, "top_weighted_factors": ["telemetry_fault_codes_30d", "prior_claims_same_vin"]},
}


def get_claim_status(request: ClaimStatusRequest) -> ClaimStatusResponse:
    _guard.authorize(request.caller_role, "read_claim_status")  # authz runs regardless of what any model output claims

    record = _FAKE_CLAIMS_DB.get(request.claim_id)
    if record is None:
        return ClaimStatusResponse(claim_id=request.claim_id, status="not_found")

    return ClaimStatusResponse(claim_id=request.claim_id, **record)


def predict_escalation_risk(
    request: PredictEscalationRiskRequest,
) -> PredictEscalationRiskResponse:
    _guard.authorize(request.caller_role, "predict_escalation_risk")

    instance = request.model_dump(
        exclude={"claim_id", "caller_role"}
    )

    prediction = invoke_escalation_model(
        claim_id=request.claim_id,
        instance=instance,
    )

    return PredictEscalationRiskResponse.model_validate(prediction)


def escalate_claim(request: EscalateClaimRequest) -> EscalateClaimResponse:
    _guard.authorize(request.caller_role, "escalate_claim")  # same authz boundary — no exception for "the model was confident"

    return EscalateClaimResponse(
        claim_id=request.claim_id,
        escalated=True,
        routed_to="senior_technician_queue",
    )


TOOL_ERRORS = (AuthorizationDeniedError,)
