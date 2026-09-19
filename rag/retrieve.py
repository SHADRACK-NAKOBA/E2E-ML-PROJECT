"""
Retrieval: hybrid (vector + keyword) search against Azure AI Search, with
metadata filtering applied BEFORE anything reaches the model — sensitivity
and source filters are query-time index filters, not a prompt instruction
the model could be talked out of. See rag/guardrails.py for why that
distinction matters.

Hybrid, not vector-only, because service bulletins and repair procedures are
full of exact strings — part numbers, bulletin IDs, DTC codes — that vector
similarity alone handles poorly; keyword search catches those, vector search
catches paraphrase/semantic matches, and the reranker combines both signals.
"""
from __future__ import annotations

from dataclasses import dataclass


@dataclass
class RetrievedChunk:
    chunk_id: str
    text: str
    source: str
    source_doc_id: str
    score: float


def hybrid_search(
    query: str,
    search_client,        # azure.search.documents.SearchClient, injected
    embed_fn,              # same embedding fn used at ingest time
    allowed_sensitivity: list[str],
    top_k: int = 20,
) -> list[RetrievedChunk]:
    """Runs vector search and keyword search against the same index and
    returns the combined candidate set. Filtering by sensitivity happens
    in the search query itself (an index-level filter), not as something
    the model is asked to respect after the fact."""
    query_vector = embed_fn([query])[0]

    sensitivity_filter = " or ".join(f"sensitivity eq '{s}'" for s in allowed_sensitivity)

    results = search_client.search(
        search_text=query,                 # keyword/BM25 leg of the hybrid search
        vector_queries=[{
            "vector": query_vector,          # vector leg
            "k_nearest_neighbors": top_k,
            "fields": "content_vector",
        }],
        filter=sensitivity_filter,
        top=top_k,
    )

    return [
        RetrievedChunk(
            chunk_id=r["id"],
            text=r["text"],
            source=r["source"],
            source_doc_id=r["source_doc_id"],
            score=r["@search.score"],
        )
        for r in results
    ]


def rerank(query: str, candidates: list[RetrievedChunk], rerank_fn, top_n: int = 6) -> list[RetrievedChunk]:
    """rerank_fn: callable(query, list[str]) -> list[float] cross-encoder
    scores, injected for the same swappability reason as embed_fn. Reranking
    the combined hybrid candidate set, rather than trusting either leg's raw
    score, is what keeps a high keyword-match-but-irrelevant chunk from
    outranking a genuinely relevant paraphrase."""
    texts = [c.text for c in candidates]
    scores = rerank_fn(query, texts)
    ranked = sorted(zip(candidates, scores), key=lambda pair: pair[1], reverse=True)
    return [c for c, _ in ranked[:top_n]]
