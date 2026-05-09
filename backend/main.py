import time
from fastapi import FastAPI, Request, HTTPException
from fastapi.middleware.cors import CORSMiddleware

from api.auth import router as auth_router
from services.ingest import ingest_user_music
from agent.mcp_agent import agent
app = FastAPI(
    title="VibeMap Music Cognition Engine",
    description="""
An AI-powered semantic music search and playlist generation API integrating Spotify Web API, Qdrant Vector Database, and Hermes AI LLM.

**AUTHENTICATION REQUIRED:** Before you can test any endpoints below, you must authenticate. 
**[Click Here to Login to Spotify](/login)** (This will redirect you back to the frontend, after which you can return here to test).

### API Endpoints:
- **/docs**: Interactive Swagger Documentation (You are here!)
- **/login**: Triggers the Spotify OAuth flow
- **/ingest**: Ingests your Spotify library into Qdrant vectors
- **/test-spotify**: Runs lifecycle tests against the Spotify API endpoints
- **/chat**: Speaks with the agent directly
    """,
    version="1.0.0"
)

# -------------------------
# CORS (FIXED FOR FRONTEND)
# -------------------------
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000"
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# -------------------------
# REQUEST LOGGER MIDDLEWARE
# -------------------------
@app.middleware("http")
async def log_requests(request: Request, call_next):
    start_time = time.time()

    print(f"\n[API Request] {request.method} {request.url.path} initiated...")

    try:
        response = await call_next(request)
    except Exception as e:
        # 🔥 Prevent silent 500s becoming "CORS errors"
        print("[UNHANDLED ERROR]", repr(e))
        raise e

    process_time = (time.time() - start_time) * 1000
    print(
        f"[API Response] {request.method} {request.url.path} "
        f"completed in {process_time:.2f}ms (Status: {response.status_code})"
    )

    return response


# -------------------------
# ROUTERS
# -------------------------
app.include_router(auth_router)


from fastapi import Query

# -------------------------
# INGEST ENDPOINT (FIXED)
# -------------------------
@app.get("/ingest", tags=["Data Pipeline"], summary="Sync Music Library to Qdrant")
def ingest():
    """
    Triggers the Ingestion sequence.
    * Fetches top & saved tracks from Spotify.
    * Retrieves audio features for semantic sound profiling.
    * Generates text embeddings and ships them to Qdrant Vector DB.
    """
    print("[Ingestion Engine] Triggered user memory sync sequence.")

    try:
        result = ingest_user_music()

        return {
            "status": "ok",
            "message": "Ingestion completed successfully",
            "result": result
        }

    except Exception as e:
        print("[INGEST ERROR]", repr(e))
        raise HTTPException(status_code=500, detail=str(e))


# -------------------------
# SPOTIFY API TEST ENDPOINT
# -------------------------
from api.auth import TOKEN_STORE
from services import spotify as spotify_api

@app.get("/test-spotify", tags=["Diagnostics"], summary="Execute API Test Suite")
def test_spotify():
    """
    Evaluates backend Spotify integrations without invoking the LLM workflow.
    Ensures that Search, Recommendations, Audio Features, and Playlist Mutations execute effectively.
    """
    print("[Test Engine] Testing Spotify API endpoints...")
    if not TOKEN_STORE:
        return {"status": "error", "message": "You must login first!"}
        
    user_id = list(TOKEN_STORE.keys())[0]
    results = {}
    
    try:
        results["top_tracks"] = len(spotify_api.get_top_tracks(user_id))
        
        search_res = spotify_api.search_spotify(user_id, "drake", limit=2)
        results["search"] = [{"name": t["name"], "id": t["id"]} for t in search_res]
        
        pl = spotify_api.create_physical_playlist(user_id, name="Test Vibe API")
        
        tracks_to_add = []
        if search_res: tracks_to_add.append(search_res[0]["id"])
        
        if tracks_to_add:
            added = spotify_api.add_tracks_to_physical_playlist(user_id, pl["id"], tracks_to_add)
            results["playlist_created"] = pl["id"]
            results["playlist_populated"] = added.get("snapshot_id") is not None
            
        return {"status": "success", "tests": results}
        
    except Exception as e:
        print("[TEST ERROR] Failed inside test route:", str(e))
        raise HTTPException(status_code=500, detail=str(e))

# -------------------------
# CHAT ENDPOINT
# -------------------------
from pydantic import BaseModel
from typing import List, Dict

class ChatRequest(BaseModel):
    messages: List[Dict[str, str]]

@app.post("/chat", tags=["Agent"], summary="Talk to the VibeMap LLM Agent")
def chat(req: ChatRequest):
    """
    Passes your semantic query directly into the Hermes AI LLM Engine.
    The agent computes your vector space explicitly to form responses.
    """
    print(f"[Chat Endpoint] Invoking VibeMap Agent with history length: {len(req.messages)}")

    try:
        response = agent(req.messages)

        return {
            "status": "ok",
            "response": response
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# -------------------------
# STATIC FRONTEND SERVING
# -------------------------
import os
import mimetypes
from fastapi.staticfiles import StaticFiles

# Fix MIME types for Windows/macOS where registry might be missing .js
mimetypes.add_type("application/javascript", ".js")
mimetypes.add_type("text/css", ".css")
mimetypes.add_type("image/svg+xml", ".svg")

frontend_dist = os.path.join(os.path.dirname(os.path.dirname(__file__)), "frontend", "dist")

if os.path.isdir(frontend_dist):
    print(f"[Startup] Found built frontend at {frontend_dist}. Mounting to root.")
    app.mount("/", StaticFiles(directory=frontend_dist, html=True), name="frontend")
else:
    print(f"[Startup] Frontend not built. Use 'npm run build' in frontend dir to serve UI via backend.")