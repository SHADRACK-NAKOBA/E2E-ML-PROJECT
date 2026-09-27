"""
Runtime RAG orchestration.

Retrieval, reranking, grounding, and generation remain separate concerns.
Generation is dependency-injected so the pipeline is not coupled to one
LLM provider and can be tested without external model calls.
"""
from __future__ import annotations

from dataclasses import dataclass

from rag.guardrails import GroundingResult, check_groundedness
from rag.retrieve import RetrievedChunk, hybrid_search, rerank


@dataclass
class RAGResponse:
    answer: str
    abstained: bool
    grounding: GroundingResult
    sources: list[str]


ABSTENTION_MESSAGE = (
    "I don't have enough trusted evidence to answer this question."
)


def answer_question(
    *,
    question: str,
    search_client,
    embed_fn,
    rerank_fn,
    generate_fn,
    allowed_sensitivity: list[str],
    retrieval_top_k: int = 20,
    rerank_top_n: int = 6,
) -> RAGResponse:
    """Retrieve trusted evidence, gate on grounding, then generate.

    generate_fn receives:
        generate_fn(question, retrieved_chunks) -> str

    It is never called when retrieval evidence fails the grounding gate.
    """
    candidates = hybrid_search(
        query=question,
        search_client=search_client,
        embed_fn=embed_fn,
        allowed_sensitivity=allowed_sensitivity,
        top_k=retrieval_top_k,
    )

    ranked: list[RetrievedChunk] = rerank(
        query=question,
        candidates=candidates,
        rerank_fn=rerank_fn,
        top_n=rerank_top_n,
    )

    grounding = check_groundedness(
        [chunk.score for chunk in ranked]
    )

    sources = list(
        dict.fromkeys(chunk.source_doc_id for chunk in ranked)
    )

    if grounding.should_abstain:
        return RAGResponse(
            answer=ABSTENTION_MESSAGE,
            abstained=True,
            grounding=grounding,
            sources=sources,
        )

    answer = generate_fn(question, ranked)

    return RAGResponse(
        answer=answer,
        abstained=False,
        grounding=grounding,
        sources=sources,
    )
