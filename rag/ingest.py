"""
Ingestion for the dealer/technician knowledge assistant RAG pipeline
(the Cigna-pattern: approved internal sources -> chunked -> embedded ->
indexed with metadata that lets retrieval be filtered BEFORE anything
reaches the model, not after).

Domain here: service bulletins, repair procedures, and warranty policy
documents a technician or dealer-support rep would query against — the
kind of "dealer-support copilot" the JD's GenAI growth angle points at.
"""
from __future__ import annotations

import hashlib
from dataclasses import dataclass, field

CHUNK_SIZE_TOKENS = 400   # sized to sit comfortably alongside retrieved
CHUNK_OVERLAP_TOKENS = 60  # evidence inside the model's context window, with
                            # enough overlap that a fact split across a
                            # boundary isn't silently lost in either chunk


@dataclass
class DocumentChunk:
    chunk_id: str
    source_doc_id: str
    text: str
    source: str            # e.g. "service_bulletin", "repair_manual", "warranty_policy"
    document_owner: str     # accountable team/individual, for audit trail
    sensitivity: str        # "internal" | "dealer_visible" | "restricted"
    metadata: dict = field(default_factory=dict)


def chunk_text(text: str, chunk_size: int = CHUNK_SIZE_TOKENS, overlap: int = CHUNK_OVERLAP_TOKENS) -> list[str]:
    """Naive whitespace-token chunking with overlap. A production system
    would use a tokenizer matching the embedding model; this keeps the
    pipeline runnable without pulling in a specific model's tokenizer."""
    words = text.split()
    if not words:
        return []
    step = max(chunk_size - overlap, 1)
    chunks = []
    for start in range(0, len(words), step):
        chunk_words = words[start:start + chunk_size]
        chunks.append(" ".join(chunk_words))
        if start + chunk_size >= len(words):
            break
    return chunks


def build_chunks(
    doc_id: str,
    text: str,
    source: str,
    document_owner: str,
    sensitivity: str,
) -> list[DocumentChunk]:
    chunks = []
    for i, chunk_text_ in enumerate(chunk_text(text)):
        chunk_id = hashlib.sha256(f"{doc_id}:{i}".encode()).hexdigest()[:16]
        chunks.append(DocumentChunk(
            chunk_id=chunk_id,
            source_doc_id=doc_id,
            text=chunk_text_,
            source=source,
            document_owner=document_owner,
            sensitivity=sensitivity,
            metadata={"chunk_index": i},
        ))
    return chunks


def embed_chunks(chunks: list[DocumentChunk], embed_fn) -> list[dict]:
    """embed_fn: callable(list[str]) -> list[list[float]], injected so this
    module doesn't hard-depend on a specific embedding provider (Azure
    OpenAI text-embedding-3-large in production; swappable for tests)."""
    texts = [c.text for c in chunks]
    vectors = embed_fn(texts)
    records = []
    for chunk, vector in zip(chunks, vectors):
        records.append({
            "id": chunk.chunk_id,
            "source_doc_id": chunk.source_doc_id,
            "text": chunk.text,
            "source": chunk.source,
            "document_owner": chunk.document_owner,
            "sensitivity": chunk.sensitivity,
            "content_vector": vector,
            **chunk.metadata,
        })
    return records
