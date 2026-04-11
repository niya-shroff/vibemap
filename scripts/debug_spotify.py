import requests
from backend.auth_spotify import TOKEN_STORE
import backend.spotify_api as spotify_api

def run():
    if not TOKEN_STORE:
        print("No tokens found.")
        return
    user_id = list(TOKEN_STORE.keys())[0]
    token = TOKEN_STORE[user_id]['access']
    print(f"User ID: {user_id}")
    
    # Check scopes or token info if possible. Spotify doesn't have a token debug endpoint, but we can try creating a playlist.
    r = requests.post(
        f"https://api.spotify.com/v1/users/{user_id}/playlists",
        headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"},
        json={"name": "Debug Playlist", "public": False}
    )
    print("Create Playlist response:", r.status_code, r.text)

if __name__ == '__main__':
    # wait we don't have access to the running process's memory...
    pass
