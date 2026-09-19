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
    escalate_claim,
    get_claim_status,
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
