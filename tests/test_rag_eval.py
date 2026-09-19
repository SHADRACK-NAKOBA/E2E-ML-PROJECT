import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from rag.eval import EvalCase, score_retrieval_relevance


def test_full_relevance_when_all_expected_sources_found():
    case = EvalCase(question="q", expected_source_doc_ids=["a", "b"])
    result = score_retrieval_relevance(case, ["a", "b", "c"])
    assert result.retrieval_relevance == 1.0
    assert result.expected_sources_missed == []


def test_partial_relevance_when_some_missed():
    case = EvalCase(question="q", expected_source_doc_ids=["a", "b"])
    result = score_retrieval_relevance(case, ["a"])
    assert result.retrieval_relevance == 0.5
    assert result.expected_sources_missed == ["b"]


def test_zero_relevance_when_none_found():
    case = EvalCase(question="q", expected_source_doc_ids=["a"])
    result = score_retrieval_relevance(case, ["z"])
    assert result.retrieval_relevance == 0.0
