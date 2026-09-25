import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from rag.guardrails import (
    ActionAuthorizationGuard,
    AuthorizationDeniedError,
    check_groundedness,
)


def test_abstains_below_threshold():
    result = check_groundedness([0.1, 0.2, 0.15])
    assert result.should_abstain


def test_does_not_abstain_above_threshold():
    result = check_groundedness([0.9, 0.6])
    assert not result.should_abstain


def test_abstains_on_empty_retrieval():
    result = check_groundedness([])
    assert result.should_abstain
    assert "No evidence" in result.reason


def test_authorized_role_passes():
    guard = ActionAuthorizationGuard()
    guard.authorize("warranty_reviewer", "approve_claim_without_review")  # should not raise


def test_unauthorized_role_denied_even_if_action_is_valid():
    """The core prompt-injection-defense assertion: an action that EXISTS
    and IS valid for some role is still denied for a role that lacks it,
    with no path for a model claim to override this."""
    guard = ActionAuthorizationGuard()
    with pytest.raises(AuthorizationDeniedError):
        guard.authorize("technician", "approve_claim_without_review")


def test_unknown_action_denied_by_default():
    guard = ActionAuthorizationGuard()
    with pytest.raises(AuthorizationDeniedError):
        guard.authorize("warranty_reviewer", "delete_all_claims")


def test_prediction_authorized_for_supported_role():
    guard = ActionAuthorizationGuard()
    guard.authorize("dealer_rep", "predict_escalation_risk")


def test_prediction_denied_for_unknown_role():
    guard = ActionAuthorizationGuard()
    with pytest.raises(AuthorizationDeniedError):
        guard.authorize("guest", "predict_escalation_risk")
