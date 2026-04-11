from qdrant_client import QdrantClient
from embeddings import model

client = QdrantClient("localhost", port=6333)

def search(query):
    vector = model.encode(query).tolist()

    results = client.search(
        collection_name="tracks",
        query_vector=vector,
        limit=5
    )

    return [r.payload for r in results]
