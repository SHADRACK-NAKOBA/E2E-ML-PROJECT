"""
Retrieval: hybrid (vector + keyword) search against Azure AI Search, with
metadata filtering applied BEFORE anything reaches the model.

Azure AI Search hybrid results use ranking scores (for example RRF scores)
that are useful for ordering candidates but are not calibrated confidence
scores. The reranker therefore produces the normalized relevance score used
by the downstream groundedness gate.
"""
from __future__ import annotations

from dataclasses import dataclass

from azure.search.documents.models import VectorizedQuery


@dataclass
class RetrievedChunk:
    chunk_id: str
    text: str
    source: str
    source_doc_id: str
    score: float
    search_score: float | None = None


def hybrid_search(
    query: str,
    search_client,
    embed_fn,
    allowed_sensitivity: list[str],
    top_k: int = 20,
) -> list[RetrievedChunk]:
    """Run hybrid keyword + vector retrieval with index-level filtering."""
    query_vector = embed_fn([query])[0]

    sensitivity_filter = " or ".join(
        f"sensitivity eq '{s}'" for s in allowed_sensitivity
    )

    vector_query = VectorizedQuery(
        vector=query_vector,
        k_nearest_neighbors=top_k,
        fields="content_vector",
    )

    results = search_client.search(
        search_text=query,
        vector_queries=[vector_query],
        filter=sensitivity_filter,
        top=top_k,
    )

    return [
        RetrievedChunk(
            chunk_id=r["id"],
            text=r["text"],
            source=r["source"],
            source_doc_id=r["source_doc_id"],
            score=float(r["@search.score"]),
            search_score=float(r["@search.score"]),
        )
        for r in results
    ]


def rerank(
    query: str,
    candidates: list[RetrievedChunk],
    rerank_fn,
    top_n: int = 6,
) -> list[RetrievedChunk]:
    """Rerank hybrid candidates and preserve reranker relevance scores.

    rerank_fn(query, texts) must return one normalized relevance score in
    the range [0, 1] for every candidate. These scores, rather than Azure
    hybrid/RRF ranking scores, are used by the groundedness gate.
    """
    if not candidates:
        return []

    texts = [candidate.text for candidate in candidates]
    scores = rerank_fn(query, texts)

    if len(scores) != len(candidates):
        raise ValueError(
            "rerank_fn must return exactly one score for every candidate"
        )

    scored: list[RetrievedChunk] = []

    for candidate, score in zip(candidates, scores):
        relevance_score = float(score)

        if not 0.0 <= relevance_score <= 1.0:
            raise ValueError(
                "rerank_fn scores must be normalized to the range [0, 1]"
            )

        scored.append(
            RetrievedChunk(
                chunk_id=candidate.chunk_id,
                text=candidate.text,
                source=candidate.source,
                source_doc_id=candidate.source_doc_id,
                score=relevance_score,
                search_score=(
                    candidate.search_score
                    if candidate.search_score is not None
                    else candidate.score
                ),
            )
        )

    return sorted(
        scored,
        key=lambda chunk: chunk.score,
        reverse=True,
    )[:top_n]
