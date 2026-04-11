from services.embeddings import embed_text
from services.qdrant import search
from services import spotify as spotify_api
from api.auth import TOKEN_STORE


def search_vibe(vibe_description: str):
    vec = embed_text(vibe_description)
    results = search(vec)

    return [
        {
            "song": r.payload["name"],
            "artist": r.payload["artists"][0]["name"],
            "spotify_id": r.payload["id"],
            "score": round(float(r.score), 2)
        }
        for r in results
    ]

def search_spotify_global(query: str):
    if not TOKEN_STORE:
        return []
    user_id = list(TOKEN_STORE.keys())[0]
    results = spotify_api.search_spotify(user_id, query)
    
    return [
        {
            "song": t["name"],
            "artist": t["artists"][0]["name"] if t.get("artists") else "Unknown",
            "spotify_id": t["id"]
        }
        for t in results
    ]

def build_playlist(vibe_description: str):
    return search_vibe(vibe_description)


def export_physical_playlist(playlist_name: str, spotify_ids: list[str]):

    if not TOKEN_STORE:
        return "No Spotify user authenticated"

    user_id = list(TOKEN_STORE.keys())[0]

    pl = spotify_api.create_physical_playlist(
        user_id=user_id,
        name=playlist_name
    )

    spotify_api.add_tracks_to_physical_playlist(
        user_id=user_id,
        playlist_id=pl["id"],
        track_ids=spotify_ids
    )

    return f"https://open.spotify.com/playlist/{pl['id']}"


def explain_vibe(tracks):
    return "Your songs form a semantic cluster in embedding space."