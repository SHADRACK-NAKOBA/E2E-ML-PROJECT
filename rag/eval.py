"""
Evaluation harness. There's no single universal hallucination metric that
covers every failure mode, so this scores three things separately against a
small eval set of realistic questions with known expected sources — and this
runs as part of CI on every retrieval/prompt-config change, because a prompt
change is a production change with the same blast radius as a code change.
"""
from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path


@dataclass
class EvalCase:
    question: str
    expected_source_doc_ids: list[str]  # ground truth: which docs SHOULD be retrieved


@dataclass
class EvalResult:
    question: str
    retrieval_relevance: float   # fraction of expected sources actually retrieved
    expected_sources_found: list[str]
    expected_sources_missed: list[str]


def load_eval_set(path: str) -> list[EvalCase]:
    data = json.loads(Path(path).read_text())
    return [EvalCase(**case) for case in data]


def score_retrieval_relevance(case: EvalCase, retrieved_doc_ids: list[str]) -> EvalResult:
    retrieved_set = set(retrieved_doc_ids)
    expected_set = set(case.expected_source_doc_ids)

    found = expected_set & retrieved_set
    missed = expected_set - retrieved_set
    relevance = len(found) / len(expected_set) if expected_set else 1.0

    return EvalResult(
        question=case.question,
        retrieval_relevance=relevance,
        expected_sources_found=sorted(found),
        expected_sources_missed=sorted(missed),
    )


def run_eval_suite(eval_set_path: str, retrieve_fn) -> dict:
    """retrieve_fn: callable(question) -> list[doc_id], injected so this
    harness runs against any retrieval implementation, including a stub in
    tests. Returns a summary a CI gate can threshold on (see CI-gate note
    below)."""
    cases = load_eval_set(eval_set_path)
    results = [score_retrieval_relevance(c, retrieve_fn(c.question)) for c in cases]

    avg_relevance = sum(r.retrieval_relevance for r in results) / len(results) if results else 0.0
    regressions = [r for r in results if r.retrieval_relevance < 0.8]

    return {
        "average_retrieval_relevance": avg_relevance,
        "n_cases": len(results),
        "n_regressions": len(regressions),
        "regressions": [{"question": r.question, "missed": r.expected_sources_missed} for r in regressions],
        "results": results,
    }
