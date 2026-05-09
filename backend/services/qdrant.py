from qdrant_client import QdrantClient
from qdrant_client.models import VectorParams, Distance
import uuid
from core.config import *

client = QdrantClient(url=QDRANT_URL, api_key=QDRANT_API_KEY)

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
    print(f"[Qdrant] Upserting track {track.get('name')} to {TRACKS_COLLECTION}...")
    try:
        client.upsert(
            collection_name=TRACKS_COLLECTION,
            points=[{
                "id": str(uuid.uuid4()),
                "vector": vector,
                "payload": track
            }],
            wait=True
        )
        print(f"[Qdrant] Successfully upserted track {track.get('name')}")
    except Exception as e:
        print(f"[Qdrant] Error upserting track {track.get('name')}: {e}")

def search(vector, limit=10):
    response = client.query_points(
        collection_name=TRACKS_COLLECTION,
        query=vector,
        limit=limit
    )
    return response.points