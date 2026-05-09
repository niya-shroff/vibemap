import base64
import requests
import secrets
import urllib.parse

from fastapi import APIRouter, Request
from fastapi.responses import RedirectResponse

from core.config import SPOTIFY_CLIENT_ID, SPOTIFY_CLIENT_SECRET, SPOTIFY_REDIRECT_URI

router = APIRouter()

# TEMP (replace with Redis in production)
STATE_STORE = {}

# user_id -> tokens
TOKEN_STORE = {}

SCOPE = " ".join([
    "user-top-read",
    "user-read-recently-played",
    "user-library-read",
    "playlist-modify-private",
    "playlist-modify-public"
])


# -------------------------
# LOGIN
# -------------------------
@router.get("/login")
def login():
    state = secrets.token_urlsafe(16)
    STATE_STORE[state] = True

    params = {
        "response_type": "code",
        "client_id": SPOTIFY_CLIENT_ID,
        "scope": SCOPE,
        "redirect_uri": SPOTIFY_REDIRECT_URI,
        "state": state,
        "show_dialog": "true"
    }

    url = "https://accounts.spotify.com/authorize?" + urllib.parse.urlencode(params)
    return RedirectResponse(url)


# -------------------------
# CALLBACK
# -------------------------
@router.get("/callback")
def callback(state: str, code: str = None, error: str = None):

    # Validate state
    if state not in STATE_STORE:
        return {"error": "invalid_state"}
    STATE_STORE.pop(state, None)

    if error:
        return {"error": error}

    if not code:
        return {"error": "missing_code"}

    # Exchange code for token
    auth = f"{SPOTIFY_CLIENT_ID}:{SPOTIFY_CLIENT_SECRET}"
    b64 = base64.b64encode(auth.encode()).decode()

    r = requests.post(
        "https://accounts.spotify.com/api/token",
        data={
            "grant_type": "authorization_code",
            "code": code,
            "redirect_uri": SPOTIFY_REDIRECT_URI
        },
        headers={
            "Authorization": f"Basic {b64}",
            "Content-Type": "application/x-www-form-urlencoded"
        }
    )

    data = r.json()

    if r.status_code >= 400:
        return {"error": data}

    access_token = data.get("access_token")
    refresh_token = data.get("refresh_token")

    if not access_token:
        return {"error": "no_access_token_returned"}

    # -------------------------
    # GET USER PROFILE (IMPORTANT FIX)
    # -------------------------
    me = requests.get(
        "https://api.spotify.com/v1/me",
        headers={"Authorization": f"Bearer {access_token}"}
    ).json()

    user_id = me.get("id")
    if not user_id:
        return {"error": "failed_to_get_user_profile"}

    # -------------------------
    # STORE TOKENS PER USER
    # -------------------------
    TOKEN_STORE[user_id] = {
        "access": access_token,
        "refresh": refresh_token
    }

    return RedirectResponse("/?auth=true")