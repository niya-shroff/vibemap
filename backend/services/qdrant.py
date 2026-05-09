from qdrant_client import QdrantClient
from qdrant_client.models import VectorParams, Distance
import uuid
from core.config import *

client = QdrantClient(host=QDRANT_HOST, port=QDRANT_PORT)

TRACKS_COLLECTION = "tracks"
AUDIO_COLLECTION = "audio_collection"

def init_db():
    client.recreate_collection(
        collection_name=TRACKS_COLLECTION,
        vectors_config=VectorParams(size=384, distance=Distance.COSINE)
    )
    client.recreate_collection(
        collection_name=AUDIO_COLLECTION,
        vectors_config=VectorParams(size=2048, distance=Distance.COSINE)
    )

def upsert(track, vector):
    client.upsert(
        collection_name=TRACKS_COLLECTION,
        points=[{
            "id": str(uuid.uuid4()),
            "vector": vector,
            "payload": track
        }]
    )

def search(vector, limit=10):
    response = client.query_points(
        collection_name=TRACKS_COLLECTION,
        query=vector,
        limit=limit
    )
    return response.points