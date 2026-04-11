from api.auth import TOKEN_STORE
import requests
import base64
from core.config import SPOTIFY_CLIENT_ID, SPOTIFY_CLIENT_SECRET
BASE_URL = "https://api.spotify.com/v1"

def refresh_access_token(refresh_token: str):
    auth = f"{SPOTIFY_CLIENT_ID}:{SPOTIFY_CLIENT_SECRET}"
    b64 = base64.b64encode(auth.encode()).decode()

    r = requests.post(
        "https://accounts.spotify.com/api/token",
        data={
            "grant_type": "refresh_token",
            "refresh_token": refresh_token
        },
        headers={
            "Authorization": f"Basic {b64}",
            "Content-Type": "application/x-www-form-urlencoded"
        }
    )

    data = r.json()

    if r.status_code != 200:
        print("[Spotify Refresh Error]", data)
        raise Exception("Failed to refresh token")

    return data

def get_headers(user_id: str):
    token_data = TOKEN_STORE.get(user_id)
    if not token_data:
        raise Exception("User not authenticated")

    access = token_data["access"]
    refresh = token_data["refresh"]

    # test token validity
    r = requests.get(
        "https://api.spotify.com/v1/me",
        headers={"Authorization": f"Bearer {access}"}
    )

    # if expired → refresh
    if r.status_code == 401:
        print("[Spotify] Access token expired, refreshing...")

        refreshed = refresh_access_token(refresh)

        access = refreshed["access_token"]

        # Spotify sometimes does NOT return refresh_token again
        TOKEN_STORE[user_id]["access"] = access

        r = requests.get(
            "https://api.spotify.com/v1/me",
            headers={"Authorization": f"Bearer {access}"}
        )

        if r.status_code >= 400:
            raise Exception(r.json())

    return {
        "Authorization": f"Bearer {access}",
        "Content-Type": "application/json"
    }

def get_spotify_user_id(headers):
    # We will keep this for backward compatibility if needed, but spotify_session is better
    r = requests.get("https://api.spotify.com/v1/me", headers=headers)
    print("[Spotify Token Scopes]", r.headers.get("x-oauth-scopes", "None"))
    if r.status_code >= 400:
        raise Exception(r.json())
    return r.json()["id"]

def spotify_session(user_id: str):
    headers = get_headers(user_id)
    r = requests.get("https://api.spotify.com/v1/me", headers=headers)
    
    if r.status_code >= 400:
        raise Exception(r.json())
        
    me = r.json()
    return headers, me["id"]

def _safe_json(r):
    try:
        return r.json()
    except Exception:
        return {"error": {"status": r.status_code, "message": r.text or "Empty Response"}}


def get_top_tracks(user_id: str):
    headers, spotify_user = spotify_session(user_id)
    print(f"[Spotify API] Fetching top tracks for {spotify_user}...")
    r = requests.get(
        f"{BASE_URL}/me/top/tracks?limit=25",
        headers=headers
    )
    data = _safe_json(r)
    if r.status_code >= 400:
        print("[Spotify API Error]", data)
        raise Exception(data)

    print(f"[Spotify API] Retrieved {len(data.get('items', []))} top tracks.")
    return data.get("items", [])


def get_saved_tracks(user_id: str):
    headers, spotify_user = spotify_session(user_id)
    print(f"[Spotify API] Fetching saved tracks for {spotify_user}...")
    r = requests.get(
        f"{BASE_URL}/me/tracks?limit=50",
        headers=headers
    )
    data = _safe_json(r)
    if r.status_code >= 400:
        print("[Spotify API Error]", data)
        raise Exception(data)

    items = [i["track"] for i in data.get("items", []) if i.get("track")]
    print(f"[Spotify API] Retrieved {len(items)} saved tracks.")
    return items

def create_physical_playlist(user_id: str, *, name: str):
    headers, spotify_user = spotify_session(user_id)
    print(f"[Spotify API] Creating playlist '{name}' for {spotify_user}...")

    r = requests.post(
        f"{BASE_URL}/me/playlists",
        headers=headers,
        json={
            "name": name,
            "public": False,
            "collaborative": False
        }
    )

    data = _safe_json(r)

    print("[Spotify Playlist Create Status]", r.status_code)
    print("[Spotify Playlist Create Response]", data)

    if r.status_code >= 400:
        raise Exception(data)

    print(f"[Spotify API] Playlist created! ID: {data.get('id')}")
    return data


def add_tracks_to_physical_playlist(user_id: str, playlist_id: str, track_ids: list[str]):
    headers, spotify_user = spotify_session(user_id)
    
    print(f"[Spotify API] Adding {len(track_ids)} tracks to playlist {playlist_id}...")
    
    # safeguard against the LLM prepending spotify:track: already
    uris = []
    for t in track_ids[:100]:
        if str(t).startswith("spotify:track:"):
            uris.append(str(t))
        else:
            uris.append(f"spotify:track:{t}")

    print(f"[Spotify API] Payload URIs: {uris}")

    r = requests.post(
        f"{BASE_URL}/playlists/{playlist_id}/items",
        headers=headers,
        json={"uris": uris}
    )
    
    data = _safe_json(r)
    
    print("[Spotify Add Tracks Status]", r.status_code)
    print("[Spotify Add Tracks Response]", data)

    if r.status_code >= 400:
        raise Exception(data)

    print("[Spotify API] Tracks successfully added!")
    return data


def search_spotify(user_id: str, query: str, limit: int = 10):
    headers, spotify_user = spotify_session(user_id)
    print(f"[Spotify API] Searching global catalog for '{query}'...")
    r = requests.get(
        f"{BASE_URL}/search",
        headers=headers,
        params={"q": query, "type": "track", "limit": limit}
    )
    data = _safe_json(r)
    if r.status_code >= 400:
        print("[Spotify API Error]", data)
        raise Exception(data)

    tracks = data.get("tracks", {}).get("items", [])
    print(f"[Spotify API] Found {len(tracks)} matching tracks.")
    return tracks