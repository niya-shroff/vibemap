from fastapi import FastAPI
from spotify import get_top_tracks
from embeddings import embed_track
from qdrant_client import init_collection, upsert_track
from recommender import search

app = FastAPI()

@app.on_event("startup")
def startup():
    init_collection()

@app.get("/ingest")
def ingest():
    tracks = get_top_tracks()

    for track in tracks:
        vector = embed_track(track)
        upsert_track(track, vector)

    return {"status": "ingested", "count": len(tracks)}

@app.get("/search")
def query(q: str):
    results = search(q)
    return {"results": results}
