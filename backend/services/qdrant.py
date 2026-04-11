from qdrant_client import QdrantClient
from qdrant_client.models import VectorParams, Distance
import uuid
from core.config import *

client = QdrantClient(host=QDRANT_HOST, port=QDRANT_PORT)

COLLECTION = "tracks"

def init_db():
    client.recreate_collection(
        collection_name=COLLECTION,
        vectors_config=VectorParams(size=384, distance=Distance.COSINE)
    )

def upsert(track, vector):
    client.upsert(
        collection_name=COLLECTION,
        points=[{
            "id": str(uuid.uuid4()),
            "vector": vector,
            "payload": track
        }]
    )

def search(vector, limit=10):
    response = client.query_points(
        collection_name=COLLECTION,
        query=vector,
        limit=limit
    )
    return response.points
