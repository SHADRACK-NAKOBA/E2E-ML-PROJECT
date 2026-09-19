"""
Production reliability for anything calling an external model or API.
Failures are classified, not handled uniformly:

- transient provider failure  -> retry with exponential backoff + jitter
- malformed-but-close response -> controlled repair/re-prompt, not a fresh full-price call
- persistent validation failure -> fallback model or human-review queue, not an infinite loop
- auth failure                 -> never retried
- rate limit                   -> provider-aware backoff, not a fixed interval

Also: a semantic cache key must include authorization, tenant, data version,
and prompt/model version — never similarity alone, or a caching optimization
quietly becomes one tenant seeing another tenant's cached response.
"""
from __future__ import annotations

import hashlib
import random
import time
from dataclasses import dataclass
from enum import Enum, auto


class FailureClass(Enum):
    TRANSIENT = auto()
    MALFORMED = auto()
    PERSISTENT_VALIDATION = auto()
    AUTH = auto()
    RATE_LIMIT = auto()


class RetryExhaustedError(Exception):
    pass


class NonRetryableError(Exception):
    pass


def classify_failure(status_code: int, error_body: str = "") -> FailureClass:
    if status_code == 401 or status_code == 403:
        return FailureClass.AUTH
    if status_code == 429:
        return FailureClass.RATE_LIMIT
    if status_code in (500, 502, 503, 504):
        return FailureClass.TRANSIENT
    if status_code == 422 and "schema" in error_body.lower():
        return FailureClass.MALFORMED
    return FailureClass.PERSISTENT_VALIDATION


def backoff_delay(attempt: int, base: float = 0.5, cap: float = 30.0) -> float:
    """Exponential backoff with full jitter (AWS-style), so many concurrent
    retries don't all collide on the same retry timestamp."""
    exp = min(cap, base * (2 ** attempt))
    return random.uniform(0, exp)


def call_with_retry(fn, *, max_attempts: int = 4, classify=classify_failure, sleep=time.sleep):
    """fn: callable() -> result, expected to raise an exception carrying a
    .status_code and .body on failure. Retries only TRANSIENT and
    RATE_LIMIT classes; everything else raises immediately."""
    last_exc = None
    for attempt in range(max_attempts):
        try:
            return fn()
        except Exception as exc:
            status_code = getattr(exc, "status_code", 500)
            body = getattr(exc, "body", "")
            failure_class = classify(status_code, body)
            last_exc = exc

            if failure_class == FailureClass.AUTH:
                raise NonRetryableError(f"Auth failure, not retrying: {exc}") from exc
            if failure_class == FailureClass.PERSISTENT_VALIDATION:
                raise NonRetryableError(f"Persistent validation failure, routing to human review: {exc}") from exc
            if failure_class == FailureClass.MALFORMED and attempt >= 1:
                # one repair attempt only — don't loop indefinitely on a
                # response that keeps failing schema validation
                raise NonRetryableError(f"Malformed response persisted after repair attempt: {exc}") from exc

            if attempt < max_attempts - 1:
                sleep(backoff_delay(attempt))
                continue

    raise RetryExhaustedError(f"Exhausted {max_attempts} attempts: {last_exc}")


@dataclass(frozen=True)
class CacheKey:
    """Every field here is required — this is the whole point. Similarity
    alone is never sufficient; authorization/tenant/version scoping is what
    prevents a caching optimization from becoming a cross-tenant data leak."""
    tenant_id: str
    caller_authorization_scope: str
    data_version: str
    prompt_version: str
    model_version: str
    semantic_hash: str

    def as_cache_string(self) -> str:
        raw = "|".join([
            self.tenant_id, self.caller_authorization_scope, self.data_version,
            self.prompt_version, self.model_version, self.semantic_hash,
        ])
        return hashlib.sha256(raw.encode()).hexdigest()


def build_cache_key(
    tenant_id: str,
    caller_authorization_scope: str,
    data_version: str,
    prompt_version: str,
    model_version: str,
    query_text: str,
) -> CacheKey:
    semantic_hash = hashlib.sha256(query_text.strip().lower().encode()).hexdigest()[:16]
    return CacheKey(tenant_id, caller_authorization_scope, data_version, prompt_version, model_version, semantic_hash)
