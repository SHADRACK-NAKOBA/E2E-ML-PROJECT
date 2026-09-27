"""Live Azure RAG runner for the Nakoba project."""

from __future__ import annotations

import json

from azure.identity import AzureCliCredential, get_bearer_token_provider
from azure.search.documents import SearchClient
from openai import AzureOpenAI

from rag.pipeline import answer_question


TENANT_ID = "8f1f1c52-d507-4981-b0bc-dd9b2a0177d7"
OPENAI_ENDPOINT = "https://oai-nakoba-dev.openai.azure.com/"
SEARCH_ENDPOINT = "https://srch-nakoba-dev.search.windows.net"
SEARCH_INDEX = "nakoba-rag-dev"

EMBEDDING_MODEL = "text-embedding-3-large"
CHAT_MODEL = "gpt-5-6-sol"


credential = AzureCliCredential(tenant_id=TENANT_ID)

token_provider = get_bearer_token_provider(
    credential,
    "https://cognitiveservices.azure.com/.default",
)

openai_client = AzureOpenAI(
    azure_endpoint=OPENAI_ENDPOINT,
    azure_ad_token_provider=token_provider,
    api_version="2024-10-21",
)

search_client = SearchClient(
    endpoint=SEARCH_ENDPOINT,
    index_name=SEARCH_INDEX,
    credential=credential,
)


def embed_fn(texts: list[str]) -> list[list[float]]:
    response = openai_client.embeddings.create(
        model=EMBEDDING_MODEL,
        input=texts,
    )
    return [item.embedding for item in response.data]


def rerank_fn(query: str, texts: list[str]) -> list[float]:
    """Use the deployed model to score candidate relevance from 0 to 1."""
    if not texts:
        return []

    numbered = "\n\n".join(
        f"[{index}] {text}"
        for index, text in enumerate(texts)
    )

    prompt = f"""
Score how relevant each candidate is to the question.

Question:
{query}

Candidates:
{numbered}

Return ONLY a JSON array containing exactly {len(texts)} numbers.
Each number must be between 0 and 1.

Use:
0.0 = unrelated
0.5 = partially relevant
1.0 = directly answers the question

Do not return explanations.
"""

    response = openai_client.chat.completions.create(
        model=CHAT_MODEL,
        messages=[
            {
                "role": "system",
                "content": (
                    "You are a relevance scoring component. "
                    "Return only valid JSON."
                ),
            },
            {
                "role": "user",
                "content": prompt,
            },
        ],
    )

    content = response.choices[0].message.content
    scores = json.loads(content)

    if not isinstance(scores, list) or len(scores) != len(texts):
        raise ValueError(
            "Reranker returned an invalid number of relevance scores"
        )

    return [float(score) for score in scores]


def generate_fn(question, chunks) -> str:
    evidence = "\n\n".join(
        (
            f"[Source: {chunk.source_doc_id}]\n"
            f"{chunk.text}"
        )
        for chunk in chunks
    )

    response = openai_client.chat.completions.create(
        model=CHAT_MODEL,
        messages=[
            {
                "role": "system",
                "content": (
                    "You are a grounded enterprise service assistant. "
                    "Answer only from the supplied evidence. "
                    "Never invent specifications, policies, or procedures. "
                    "If the evidence does not support the answer, say so."
                ),
            },
            {
                "role": "user",
                "content": (
                    f"Evidence:\n{evidence}\n\n"
                    f"Question:\n{question}"
                ),
            },
        ],
    )

    return response.choices[0].message.content.strip()


def ask_dealer_knowledge(
    question: str,
    allowed_sensitivity: list[str],
):
    """Run the live grounded RAG pipeline for an authorized caller."""
    return answer_question(
        question=question,
        search_client=search_client,
        embed_fn=embed_fn,
        rerank_fn=rerank_fn,
        generate_fn=generate_fn,
        allowed_sensitivity=allowed_sensitivity,
        retrieval_top_k=4,
        rerank_top_n=4,
    )


def main() -> None:
    question = (
        "What's the torque spec for the rear axle nut "
        "on a Touring model?"
    )

    print("Question:", question)
    print()

    response = ask_dealer_knowledge(
        question=question,
        allowed_sensitivity=["dealer_visible"],
    )

    print("LIVE RAG RESULT")
    print("=" * 60)
    print("Abstained:", response.abstained)
    print(
        "Grounding score:",
        response.grounding.max_retrieval_score,
    )
    print("Grounding:", response.grounding.reason)
    print("Sources:", response.sources)
    print()
    print("Answer:")
    print(response.answer)


if __name__ == "__main__":
    main()
