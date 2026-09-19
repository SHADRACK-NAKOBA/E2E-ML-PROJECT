# Copilot Studio & Analytics Tooling Consolidation

These two JD "nice to have" items are treated differently from everything
else in this repo, on purpose — being honest about the difference matters
more than padding the repo with something that looks like coverage but isn't.

## Copilot Studio adoption

Copilot Studio is Microsoft's low-code conversational-agent builder — it's
not something you demonstrate with a Python module the way an MCP server or
a RAG pipeline is. What genuinely transfers from this repo to a Copilot
Studio integration:

- The MCP server in `agentic/mcp_server.py` is directly usable as a Copilot
  Studio custom connector / tool source, since Copilot Studio has native MCP
  support — the tool schemas, authorization guard, and reliability wrapper
  don't need to be rewritten, they're consumed as-is.
- The guardrail pattern in `rag/guardrails.py` (model is never the
  authorization boundary) applies identically whether the orchestration
  layer is a hand-rolled agent loop or Copilot Studio's topic/action
  system — the enforcement point is the same regardless of what's calling it.

What doesn't transfer: actual hands-on time building and publishing a
Copilot Studio bot, its topic design, and its channel deployment. That's a
genuine gap, not one this repo closes, and the honest answer in an
interview is exactly that — the underlying architecture reasoning holds,
the specific tool's UI/publishing workflow doesn't have reps behind it yet.

## Consolidating a fragmented analytics tooling estate

This is a process and governance problem more than an engineering one —
there's no single artifact that "demonstrates" it the way a working
pipeline demonstrates CI/CD discipline. What this repo *does* show that's
relevant to the underlying skill:

- `docs/DECISIONS.md` and `docs/DECISIONS_RAG_AGENTIC.md` are themselves a
  worked example of the actual skill being tested here — evaluating
  competing tools/approaches against explicit criteria and writing down why
  one was chosen over another, which is the same evaluative discipline a
  tooling-consolidation effort requires, just applied to a single project's
  choices instead of an organization's estate.
- The CODEOWNERS + policy-as-code pattern (`terraform/`, `.github/workflows/ci.yml`)
  is the mechanism that would actually enforce a consolidated standard once
  one exists — automation over a written policy nobody reads.

What doesn't transfer: actual experience running a cross-team tooling
audit and migration. Same honesty as above applies if this comes up.
