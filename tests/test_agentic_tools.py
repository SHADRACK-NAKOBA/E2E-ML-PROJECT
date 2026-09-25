import pytest

from agentic.tools import (
    PredictEscalationRiskRequest,
    predict_escalation_risk,
)
from rag.guardrails import AuthorizationDeniedError


def _request(caller_role: str = "technician") -> PredictEscalationRiskRequest:
    return PredictEscalationRiskRequest(
        claim_id="CLM-TEST-001",
        caller_role=caller_role,
        vehicle_model_line="Touring",
        dealer_region="NA-East",
        component="engine",
        vehicle_age_months=24,
        mileage_at_claim=15000,
        telemetry_fault_codes_30d=2,
        telemetry_avg_engine_temp_delta=3.1,
        component_historical_failure_severity=0.4,
        prior_claims_same_vin=1,
        dealer_avg_repair_days=5.2,
    )


def test_prediction_calls_azure_ml_with_validated_payload(monkeypatch):
    captured = {}

    def fake_invoke(*, claim_id, instance, timeout_seconds=30):
        captured["claim_id"] = claim_id
        captured["instance"] = instance
        return {
            "claim_id": claim_id,
            "escalation_risk_score": 0.693873405456543,
            "high_risk": True,
            "top_weighted_factors": [
                "telemetry_fault_codes_30d",
                "prior_claims_same_vin",
            ],
        }

    monkeypatch.setattr(
        "agentic.tools.invoke_escalation_model",
        fake_invoke,
    )

    response = predict_escalation_risk(_request())

    assert captured["claim_id"] == "CLM-TEST-001"
    assert "claim_id" not in captured["instance"]
    assert "caller_role" not in captured["instance"]
    assert len(captured["instance"]) == 10
    assert captured["instance"]["vehicle_model_line"] == "Touring"
    assert captured["instance"]["telemetry_fault_codes_30d"] == 2

    assert response.claim_id == "CLM-TEST-001"
    assert response.high_risk is True
    assert response.escalation_risk_score == pytest.approx(
        0.693873405456543
    )


def test_unauthorized_prediction_never_calls_azure_ml(monkeypatch):
    called = False

    def fake_invoke(**kwargs):
        nonlocal called
        called = True
        raise AssertionError("Azure ML must not be called")

    monkeypatch.setattr(
        "agentic.tools.invoke_escalation_model",
        fake_invoke,
    )

    with pytest.raises(AuthorizationDeniedError):
        predict_escalation_risk(_request(caller_role="guest"))

    assert called is False


def test_entra_auth_failure_is_not_retried(monkeypatch):
    from azure.core.exceptions import ClientAuthenticationError

    from agentic.azure_ml import invoke_escalation_model
    from agentic.reliability import NonRetryableError, call_with_retry

    calls = {"n": 0}

    class FailingCredential:
        def get_token(self, *args, **kwargs):
            calls["n"] += 1
            raise ClientAuthenticationError(
                message="Simulated Entra authentication failure"
            )

    monkeypatch.setattr(
        "agentic.azure_ml.DefaultAzureCredential",
        lambda: FailingCredential(),
    )

    instance = {
        "vehicle_model_line": "Touring",
        "dealer_region": "NA-East",
        "component": "engine",
        "vehicle_age_months": 24,
        "mileage_at_claim": 15000,
        "telemetry_fault_codes_30d": 2,
        "telemetry_avg_engine_temp_delta": 3.1,
        "component_historical_failure_severity": 0.4,
        "prior_claims_same_vin": 1,
        "dealer_avg_repair_days": 5.2,
    }

    with pytest.raises(NonRetryableError):
        call_with_retry(
            lambda: invoke_escalation_model(
                claim_id="CLM-TEST-001",
                instance=instance,
            ),
            sleep=lambda seconds: None,
        )

    assert calls["n"] == 1
