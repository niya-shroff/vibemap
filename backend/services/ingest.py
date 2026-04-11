from .spotify import get_top_tracks, get_saved_tracks
from .embeddings import embed_track
from .qdrant import upsert, init_db
from api.auth import TOKEN_STORE


def ingest_user_music():
    init_db()

    if not TOKEN_STORE:
        raise Exception("No authenticated users")

    user_id = list(TOKEN_STORE.keys())[0]

    top_tracks = get_top_tracks(user_id)
    saved_tracks = get_saved_tracks(user_id)

    manifest_map = {
        t["id"]: t
        for t in (top_tracks + saved_tracks)
        if t and t.get("id")
    }
    
    manifest = manifest_map.values()
    count = 0

    for t in manifest:
        vec = embed_track(t)
        upsert(t, vec)
        count += 1

    return {"ingested": count, "user_id": user_id}