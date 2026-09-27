"""Create or update the Azure AI Search index used by the Nakoba RAG pipeline."""

from azure.identity import DefaultAzureCredential
from azure.search.documents.indexes import SearchIndexClient
from azure.search.documents.indexes.models import (
    HnswAlgorithmConfiguration,
    SearchField,
    SearchFieldDataType,
    SearchIndex,
    SimpleField,
    SearchableField,
    VectorSearch,
    VectorSearchProfile,
)

SEARCH_ENDPOINT = "https://srch-nakoba-dev.search.windows.net"
INDEX_NAME = "nakoba-rag-dev"
VECTOR_DIMENSIONS = 3072
VECTOR_PROFILE = "nakoba-vector-profile"
HNSW_ALGORITHM = "nakoba-hnsw"


def build_index() -> SearchIndex:
    fields = [
        SimpleField(
            name="id",
            type=SearchFieldDataType.String,
            key=True,
            filterable=True,
        ),
        SimpleField(
            name="source_doc_id",
            type=SearchFieldDataType.String,
            filterable=True,
        ),
        SearchableField(
            name="text",
            type=SearchFieldDataType.String,
        ),
        SimpleField(
            name="source",
            type=SearchFieldDataType.String,
            filterable=True,
        ),
        SimpleField(
            name="document_owner",
            type=SearchFieldDataType.String,
            filterable=True,
        ),
        SimpleField(
            name="sensitivity",
            type=SearchFieldDataType.String,
            filterable=True,
        ),
        SimpleField(
            name="chunk_index",
            type=SearchFieldDataType.Int32,
            filterable=True,
            sortable=True,
        ),
        SearchField(
            name="content_vector",
            type=SearchFieldDataType.Collection(SearchFieldDataType.Single),
            searchable=True,
            vector_search_dimensions=VECTOR_DIMENSIONS,
            vector_search_profile_name=VECTOR_PROFILE,
        ),
    ]

    vector_search = VectorSearch(
        algorithms=[
            HnswAlgorithmConfiguration(
                name=HNSW_ALGORITHM,
            )
        ],
        profiles=[
            VectorSearchProfile(
                name=VECTOR_PROFILE,
                algorithm_configuration_name=HNSW_ALGORITHM,
            )
        ],
    )

    return SearchIndex(
        name=INDEX_NAME,
        fields=fields,
        vector_search=vector_search,
    )


def main() -> None:
    credential = DefaultAzureCredential()
    client = SearchIndexClient(
        endpoint=SEARCH_ENDPOINT,
        credential=credential,
    )

    index = client.create_or_update_index(build_index())

    print(f"Index name: {index.name}")
    print(f"Vector dimensions: {VECTOR_DIMENSIONS}")
    print(f"Vector profile: {VECTOR_PROFILE}")
    print("Azure AI Search index creation: SUCCESS")


if __name__ == "__main__":
    main()
