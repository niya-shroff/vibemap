# VibeMap: AI Music Cognition Engine

VibeMap is an advanced semantic natural language music cognition system. It integrates the Spotify Web API with Qdrant Vector Database and the Hermes AI LLM to create dynamic acoustic vector spaces out of a user's standard music library.

<img width="1608" height="1708" alt="image" src="https://github.com/user-attachments/assets/9c48b52c-f61c-4be1-a8b8-c7ed7bf731ac" />

## Features
* **OAuth Spotify Linking:** Authenticates and pulls robust payloads directly from your personalized Spotify library.
* **Vector Library Ingestion:** Absorbs custom user libraries (Top Tracks, Saved Tracks) mixed directly with robust algorithmic endpoints (Audio Features & Recommendations).
* **Hermes AI LLM Agent Workflow:** Accepts fully natural language queries like `"Build me a playlist for rainy nights"` or `"Search the catalog for intense lofi tracks"` and programmatically invokes backend endpoints to serve up your vibe automatically.
* **Intelligent Swagger UI Documentation:** Pre-configured auto-generated interactive OpenAPI docs available.

## Running Locally

1. Create a `.env` in the `backend/` directory housing your tokens:
```
SPOTIFY_CLIENT_ID=YOUR_ID
SPOTIFY_CLIENT_SECRET=YOUR_SECRET
SPOTIFY_REDIRECT_URI=http://localhost:8000/callback
```
2. Make sure you have Docker correctly configured to start the Qdrant DB.
3. Bring the entire stack up via `make up`.

## Access the Swagger Configuration
FastAPI natively serves an automatic Swagger portal which can be incredibly useful to verify specific pieces of your system. To view the API definitions, navigate your browser strictly to:
**[http://localhost:8000/docs](http://localhost:8000/docs)**

From there, you can interact directly with:
- **`GET /test-spotify`**: Ensures all HTTP calls run cleanly.
- **`GET /ingest`**: Initiates the Qdrant database sync sequence.
- **`GET /chat?q=...`**: Passes language strictly through the Agent process map dynamically testing the tools.

## Project Structure
- `backend/`: Fast API + Qdrant ML Layer + LLM orchestrator script map
- `frontend/`: Clean standard JavaScript Spotify-themed minimalist UI Client

## Deploying to Vercel

VibeMap is pre-configured to be deployed as a single application on Vercel.

1. Push your repository to a Git provider (GitHub, GitLab, etc.).
2. Import the project into Vercel.
3. Keep the default Vite framework preset. Vercel will automatically build the React frontend and deploy the FastAPI backend as Serverless Functions using the `vercel.json` configuration.
4. Add the required environment variables in the Vercel dashboard:
   - `SPOTIFY_CLIENT_ID`
   - `SPOTIFY_CLIENT_SECRET`
   - `SPOTIFY_REDIRECT_URI` (Set this to your production Vercel URL, e.g., `https://your-app.vercel.app/api/auth/callback`)
5. Deploy the application. Note that for production, you will need to update the Qdrant configuration to point to a managed Qdrant Cloud instance instead of localhost.
