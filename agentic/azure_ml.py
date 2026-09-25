"""
Authenticated adapter for the Nakoba Azure ML managed online endpoint.

Keeps Azure-specific networking/authentication separate from MCP tool and
business logic. Uses Microsoft Entra ID authentication rather than endpoint
keys or credentials stored in source code.
"""
from __future__ import annotations

import json
import os
import urllib.error
import urllib.request

from azure.core.exceptions import ClientAuthenticationError
from azure.identity import DefaultAzureCredential


AZURE_ML_SCOPE = "https://ml.azure.com/.default"


class AzureMLInvocationError(Exception):
    """HTTP error shape understood by agentic.reliability.call_with_retry."""

    def __init__(self, status_code: int, body: str):
        self.status_code = status_code
        self.body = body
        super().__init__(f"Azure ML invocation failed ({status_code}): {body}")


def _endpoint_uri() -> str:
    uri = os.getenv("NAKOBA_AZUREML_SCORING_URI")
    if not uri:
        raise ValueError(
            "NAKOBA_AZUREML_SCORING_URI is required. "
            "Set it to the managed online endpoint scoring URI."
        )
    return uri


def invoke_escalation_model(
    *,
    claim_id: str,
    instance: dict,
    timeout_seconds: int = 30,
) -> dict:
    """Invoke the deployed Azure ML champion and return one prediction."""

    credential = DefaultAzureCredential()
    try:
        token = credential.get_token(AZURE_ML_SCOPE).token
    except ClientAuthenticationError as exc:
        raise AzureMLInvocationError(
            401,
            "Microsoft Entra ID authentication failed.",
        ) from exc

    payload = json.dumps(
        {
            "instances": [instance],
            "claim_ids": [claim_id],
        }
    ).encode("utf-8")

    request = urllib.request.Request(
        _endpoint_uri(),
        data=payload,
        method="POST",
        headers={
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
        },
    )

    try:
        with urllib.request.urlopen(request, timeout=timeout_seconds) as response:
            body = response.read().decode("utf-8")
    except urllib.error.HTTPError as exc:
        body = exc.read().decode("utf-8", errors="replace")
        raise AzureMLInvocationError(exc.code, body) from exc
    except urllib.error.URLError as exc:
        raise AzureMLInvocationError(503, str(exc.reason)) from exc

    decoded = json.loads(body)

    # Some Azure ML scoring configurations return JSON encoded as a string.
    if isinstance(decoded, str):
        decoded = json.loads(decoded)

    predictions = decoded.get("predictions", [])
    if len(predictions) != 1:
        raise AzureMLInvocationError(
            422,
            f"Expected exactly one prediction, received {len(predictions)}",
        )

    return predictions[0]
