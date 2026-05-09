# VibeMap: AI Music Cognition Engine

VibeMap is a semantic music assistant: it ingests your Spotify library into a vector index, then uses the **Hermes** LLM with tool calling to answer in natural language—search by vibe, build playlists from your memory, and **export real playlists** to your Spotify account.

<img width="1608" height="1708" alt="image" src="https://github.com/user-attachments/assets/9c48b52c-f61c-4be1-a8b8-c7ed7bf731ac" />

## Features

- **Spotify OAuth:** Links your account and reads **top tracks** and **saved tracks** for ingestion.
- **Vector library:** Embeds tracks (title, artist, and optional audio-feature hints when present) into **Qdrant** for similarity search (“build me something sad”, “upbeat workout”, etc.).
- **Hermes agent with tools:** The backend exposes function-calling tools (`search_vibe`, `build_playlist`, `search_spotify_global`, `export_physical_playlist`, …) so the model plans searches and exports instead of guessing track IDs.
- **Reliable playlist export:** In-request **`PlaylistAgentState`** keeps canonical Spotify track IDs and the **exported playlist URL**. The API returns structured fields so the UI can round-trip IDs across chat turns and show Open Spotify links.
- **Pydantic validation:** Tool arguments and `/chat` payloads are validated (including 22-character Spotify track id format) before calling Spotify or the vector DB.
- **OpenAPI docs:** Interactive Swagger at `/docs`.

## Running locally

1. **Environment** — Create `backend/.env`:

   ```env
   SPOTIFY_CLIENT_ID=your_id
   SPOTIFY_CLIENT_SECRET=your_secret
   SPOTIFY_REDIRECT_URI=http://localhost:8000/callback
   ```

2. **Qdrant** — Docker available; the stack expects Qdrant running (see `make up` / project compose).

3. **Embeddings** — The first run may download the sentence-transformers model (`all-MiniLM-L6-v2`). Ensure Hugging Face / network access if required (`huggingface-cli login` optional).

4. **Start everything** — From the repo root:

   ```bash
   make up
   ```

   Typical URLs: API **http://localhost:8000**, dev UI **http://localhost:3000** (see your `Makefile` / Vite config).

5. **Flow** — Open the app → **Login** (Spotify) → **Ingest Memory** → chat.

## Chat API (`POST /chat`)

Request body (JSON):

| Field | Description |
| --- | --- |
| `messages` | Array of `{ "role": "user" \| "assistant" \| "system", "content": "..." }` (chat history the UI shows). |
| `last_spotify_track_ids` | Optional. Canonical track ids from the **previous** response; the server pins them so follow-up “export this” messages still have valid IDs without the model seeing hidden tool JSON. |

Response:

| Field | Description |
| --- | --- |
| `status` | `"ok"` |
| `response` | Assistant text. |
| `spotify_track_ids` | Ids from the latest search/build in that request (or after a successful export). |
| `spotify_playlist_url` | Present when `export_physical_playlist` succeeded—open link for the new playlist. |

The frontend stores `spotify_track_ids` and sends them back as `last_spotify_track_ids` on the next message so multi-turn export stays consistent.

## Swagger

**[http://localhost:8000/docs](http://localhost:8000/docs)**

Useful routes include:

- **`GET /ingest`** — Sync library into Qdrant (requires auth).
- **`POST /chat`** — Agent (request body as above).
- **`GET /test-spotify`** — Smoke-test Spotify integration.

## Project structure

- `backend/` — FastAPI, Qdrant, Spotify client, embeddings, **`agent/`** (`mcp_agent.py`, `schemas.py`, `session_state.py`).
- `frontend/` — Vite + React UI.

## Deploying to Vercel

VibeMap can be deployed as a single app on Vercel.

1. Push the repository to a Git host and import the project in Vercel.
2. Use the Vite preset so the frontend builds; backend routing follows your `vercel.json`.
3. Set environment variables in Vercel: `SPOTIFY_CLIENT_ID`, `SPOTIFY_CLIENT_SECRET`, `SPOTIFY_REDIRECT_URI` (production callback URL, e.g. `https://your-app.vercel.app/callback`—match your app and Spotify dashboard).
4. Point **Qdrant** at a hosted instance (e.g. Qdrant Cloud) instead of localhost for production.
