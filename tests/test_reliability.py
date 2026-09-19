import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from agentic.reliability import (
    FailureClass,
    NonRetryableError,
    RetryExhaustedError,
    build_cache_key,
    call_with_retry,
    classify_failure,
)


class FakeError(Exception):
    def __init__(self, status_code, body=""):
        super().__init__(str(status_code))
        self.status_code = status_code
        self.body = body


@pytest.mark.parametrize("status,body,expected", [
    (401, "", FailureClass.AUTH),
    (403, "", FailureClass.AUTH),
    (429, "", FailureClass.RATE_LIMIT),
    (503, "", FailureClass.TRANSIENT),
    (422, "schema validation failed", FailureClass.MALFORMED),
    (422, "unrelated error", FailureClass.PERSISTENT_VALIDATION),
])
def test_classify_failure(status, body, expected):
    assert classify_failure(status, body) == expected


def test_transient_failure_retries_then_succeeds():
    calls = {"n": 0}

    def flaky():
        calls["n"] += 1
        if calls["n"] < 3:
            raise FakeError(503)
        return "ok"

    result = call_with_retry(flaky, sleep=lambda s: None)
    assert result == "ok"
    assert calls["n"] == 3


def test_auth_failure_never_retried():
    calls = {"n": 0}

    def always_fails():
        calls["n"] += 1
        raise FakeError(401)

    with pytest.raises(NonRetryableError):
        call_with_retry(always_fails, sleep=lambda s: None)
    assert calls["n"] == 1  # exactly one attempt — no retry loop


def test_persistent_transient_failure_exhausts_retries():
    def always_fails():
        raise FakeError(503)

    with pytest.raises(RetryExhaustedError):
        call_with_retry(always_fails, max_attempts=3, sleep=lambda s: None)


def test_cache_key_scoped_by_tenant():
    k1 = build_cache_key("tenantA", "scope1", "v1", "p1", "m1", "same query text")
    k2 = build_cache_key("tenantB", "scope1", "v1", "p1", "m1", "same query text")
    assert k1.as_cache_string() != k2.as_cache_string()


def test_cache_key_stable_for_identical_inputs():
    k1 = build_cache_key("tenantA", "scope1", "v1", "p1", "m1", "same query text")
    k2 = build_cache_key("tenantA", "scope1", "v1", "p1", "m1", "same query text")
    assert k1.as_cache_string() == k2.as_cache_string()
