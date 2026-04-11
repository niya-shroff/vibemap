import time
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware

from auth_spotify import router as auth_router
from ingest import ingest_user_music
from agent.mcp_agent import agent
app = FastAPI(
    title="VibeMap Music Cognition Engine",
    description="""
An AI-powered semantic music search and playlist generation API integrating Spotify Web API, Qdrant Vector Database, and Google Gemini LLM.

🚨 **AUTHENTICATION REQUIRED:** Before you can test any endpoints below, you must authenticate. 
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

        return {
            "status": "error",
            "message": str(e)
        }


# -------------------------
# SPOTIFY API TEST ENDPOINT
# -------------------------
from auth_spotify import TOKEN_STORE
import spotify_api

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
        
        if search_res:
            test_id = search_res[0]["id"]
            features = spotify_api.get_audio_features(user_id, [test_id])
            results["audio_features"] = features[0] if features else None
            
        if search_res:
            rec_res = spotify_api.get_recommendations(user_id, seed_tracks=[test_id], limit=2)
            results["recommendations"] = [{"name": t["name"], "id": t["id"]} for t in rec_res]
            
        pl = spotify_api.create_physical_playlist(user_id, name="Test Vibe API")
        if search_res and rec_res:
            tracks_to_add = [search_res[0]["id"], rec_res[0]["id"]]
            added = spotify_api.add_tracks_to_physical_playlist(user_id, pl["id"], tracks_to_add)
            results["playlist_created"] = pl["id"]
            results["playlist_populated"] = added.get("snapshot_id") is not None
            
        return {"status": "success", "tests": results}
        
    except Exception as e:
        print("[TEST ERROR] Failed inside test route:", str(e))
        return {"status": "error", "error": str(e)}

# -------------------------
# CHAT ENDPOINT
# -------------------------
@app.get("/chat", tags=["Agent"], summary="Talk to the VibeMap LLM Agent")
def chat(
    q: str = Query(..., description="Your natural language request to the agent.", example="Build a playlist for rainy nights")
):
    """
    Passes your semantic query directly into the Google Gemini LLM Engine.
    The agent computes your vector space explicitly to form responses.
    """
    print(f"[Chat Endpoint] Invoking VibeMap Agent with query: '{q}'")

    try:
        response = agent(q)

        return {
            "status": "ok",
            "response": response
        }

    except Exception as e:
        print("[CHAT ERROR]", repr(e))

        return {
            "status": "error",
            "message": str(e)
        }