"""Ingest the demo knowledge base into the live Azure AI Search index."""

import json

from azure.identity import DefaultAzureCredential, get_bearer_token_provider
from azure.search.documents import SearchClient
from openai import AzureOpenAI

from rag.ingest import build_chunks, embed_chunks

OPENAI_ENDPOINT = "https://oai-nakoba-dev.openai.azure.com/"
OPENAI_DEPLOYMENT = "text-embedding-3-large"

SEARCH_ENDPOINT = "https://srch-nakoba-dev.search.windows.net"
SEARCH_INDEX = "nakoba-rag-dev"

KNOWLEDGE_BASE = "rag/knowledge_base/documents.json"


def main() -> None:
    credential = DefaultAzureCredential()

    token_provider = get_bearer_token_provider(
        credential,
        "https://cognitiveservices.azure.com/.default",
    )

    openai_client = AzureOpenAI(
        azure_endpoint=OPENAI_ENDPOINT,
        azure_ad_token_provider=token_provider,
        api_version="2024-10-21",
    )

    def embed_fn(texts: list[str]) -> list[list[float]]:
        response = openai_client.embeddings.create(
            model=OPENAI_DEPLOYMENT,
            input=texts,
        )
        return [item.embedding for item in response.data]

    search_client = SearchClient(
        endpoint=SEARCH_ENDPOINT,
        index_name=SEARCH_INDEX,
        credential=credential,
    )

    with open(KNOWLEDGE_BASE, encoding="utf-8") as f:
        documents = json.load(f)

    all_chunks = []

    for document in documents:
        chunks = build_chunks(
            doc_id=document["doc_id"],
            text=document["text"],
            source=document["source"],
            document_owner=document["document_owner"],
            sensitivity=document["sensitivity"],
        )

        all_chunks.extend(chunks)

        print(
            f"Prepared {len(chunks)} chunk(s): "
            f"{document['doc_id']}"
        )

    records = embed_chunks(all_chunks, embed_fn)

    print(f"Generated embeddings for {len(records)} chunks.")

    results = search_client.upload_documents(documents=records)

    failed = []

    for result in results:
        if result.succeeded:
            print(f"Uploaded: {result.key}")
        else:
            failed.append(result)
            print(
                f"FAILED: {result.key} "
                f"{result.error_message}"
            )

    if failed:
        raise RuntimeError(
            f"{len(failed)} document(s) failed to upload."
        )

    print()
    print(f"Documents loaded: {len(documents)}")
    print(f"Chunks indexed: {len(records)}")
    print(f"Search index: {SEARCH_INDEX}")
    print("Live RAG ingestion: SUCCESS")


if __name__ == "__main__":
    main()
