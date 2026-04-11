from qdrant_client import QdrantClient
from qdrant_client.models import VectorParams, Distance

client = QdrantClient("localhost", port=6333)

COLLECTION = "tracks"

def init_collection():
    client.recreate_collection(
        collection_name=COLLECTION,
        vectors_config=VectorParams(size=384, distance=Distance.COSINE)
    )

def upsert_track(track, vector):
    client.upsert(
        collection_name=COLLECTION,
        points=[{
            "id": track["id"],
            "vector": vector,
            "payload": track
        }]
    )
