import spotipy
from spotipy.oauth2 import SpotifyOAuth

sp = spotipy.Spotify(auth_manager=SpotifyOAuth(
    client_id="YOUR_ID",
    client_secret="YOUR_SECRET",
    redirect_uri="http://localhost:8000/callback",
    scope="user-top-read user-read-recently-played"
))

def get_top_tracks():
    results = sp.current_user_top_tracks(limit=20)
    tracks = []

    for item in results['items']:
        tracks.append({
            "id": item["id"],
            "name": item["name"],
            "artist": item["artists"][0]["name"]
        })

    return tracks
