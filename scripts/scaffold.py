import os

files = {
    "backend/config.py": """import os
from dotenv import load_dotenv

load_dotenv()

SPOTIFY_CLIENT_ID = os.getenv("SPOTIFY_CLIENT_ID")
SPOTIFY_CLIENT_SECRET = os.getenv("SPOTIFY_CLIENT_SECRET")
SPOTIFY_REDIRECT_URI = os.getenv("SPOTIFY_REDIRECT_URI")

QDRANT_HOST = "localhost"
QDRANT_PORT = 6333

OLLAMA_URL = "http://localhost:11434/api/chat"
OLLAMA_MODEL = "mistral"
""",
    "backend/auth_spotify.py": """import base64
import requests
import secrets
from fastapi import APIRouter
from fastapi.responses import RedirectResponse
from config import *

router = APIRouter()

STATE_STORE = {}
TOKEN_STORE = {}

SCOPE = "user-top-read user-read-recently-played"

@router.get("/login")
def login():
    state = secrets.token_urlsafe(16)
    STATE_STORE[state] = True

    url = (
        "https://accounts.spotify.com/authorize?"
        f"response_type=code&client_id={SPOTIFY_CLIENT_ID}"
        f"&scope={SCOPE}"
        f"&redirect_uri={SPOTIFY_REDIRECT_URI}"
        f"&state={state}"
    )

    return RedirectResponse(url)


@router.get("/callback")
def callback(code: str, state: str):

    if state not in STATE_STORE:
        return {"error": "invalid_state"}

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

    TOKEN_STORE["access"] = data["access_token"]
    TOKEN_STORE["refresh"] = data.get("refresh_token")

    return {"status": "logged_in"}
""",
    "backend/spotify_api.py": """import requests
from auth_spotify import TOKEN_STORE

def get_headers():
    return {
        "Authorization": f"Bearer {TOKEN_STORE.get('access')}"
    }

def get_top_tracks():
    r = requests.get(
        "https://api.spotify.com/v1/me/top/tracks?limit=25",
        headers=get_headers()
    )
    res = r.json()
    if 'items' not in res:
        raise Exception("Spotify error: " + str(res))
    return res["items"]
""",
    "backend/embeddings.py": """from sentence_transformers import SentenceTransformer

model = SentenceTransformer("all-MiniLM-L6-v2")

def embed_track(track):
    text = f"{track['name']} {track['artists'][0]['name']}"
    return model.encode(text).tolist()

def embed_text(text):
    return model.encode(text).tolist()
""",
    "backend/qdrant_db.py": """from qdrant_client import QdrantClient
from qdrant_client.models import VectorParams, Distance
import uuid
from config import *

client = QdrantClient(host=QDRANT_HOST, port=QDRANT_PORT)

COLLECTION = "tracks"

def init_db():
    client.recreate_collection(
        collection_name=COLLECTION,
        vectors_config=VectorParams(size=384, distance=Distance.COSINE)
    )

def upsert(track, vector):
    client.upsert(
        collection_name=COLLECTION,
        points=[{
            "id": str(uuid.uuid4()),
            "vector": vector,
            "payload": track
        }]
    )

def search(vector, limit=10):
    return client.search(
        collection_name=COLLECTION,
        query_vector=vector,
        limit=limit
    )
""",
    "backend/ingest.py": """from spotify_api import get_top_tracks
from embeddings import embed_track
from qdrant_db import upsert, init_db

def ingest_user_music():
    init_db()
    tracks = get_top_tracks()

    for t in tracks:
        vec = embed_track(t)
        upsert(t, vec)

    return {"ingested": len(tracks)}
""",
    "backend/tools/music_tools.py": """from embeddings import embed_text
from qdrant_db import search

def search_music(query: str):
    vec = embed_text(query)
    results = search(vec)

    return [
        {
            "song": r.payload["name"],
            "artist": r.payload["artists"][0]["name"],
            "score": r.score
        }
        for r in results
    ]


def build_playlist(vibe: str):
    return search_music(vibe)


def explain_vibe(tracks):
    return "These songs cluster in your personal taste space based on mood, tempo, and acoustic similarity."
""",
    "backend/tools/registry.py": """from tools.music_tools import search_music, build_playlist, explain_vibe

TOOLS = {
    "search_music": search_music,
    "build_playlist": build_playlist,
    "explain_vibe": explain_vibe
}
""",
    "backend/agent/mcp_agent.py": """import requests
from config import *
from tools.registry import TOOLS

SYSTEM_PROMPT = \"\"\"
You are VibeMap AI.

You can call tools:
- search_music(query)
- build_playlist(vibe)
- explain_vibe(tracks)

Always pick the best tool for the user request.
Return structured responses.
\"\"\"

def call_llm(prompt):
    r = requests.post(
        OLLAMA_URL,
        json={
            "model": OLLAMA_MODEL,
            "messages": [
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": prompt}
            ]
        }
    )
    return r.json()["message"]["content"]


def agent(user_input: str):

    # SIMPLE MCP ROUTING
    if "playlist" in user_input:
        return TOOLS["build_playlist"](user_input)

    if "like" in user_input:
        return TOOLS["search_music"](user_input)

    if "explain" in user_input:
        return TOOLS["explain_vibe"]([])

    return TOOLS["search_music"](user_input)
""",
    "backend/main.py": """from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from auth_spotify import router as auth_router
from ingest import ingest_user_music
from agent.mcp_agent import agent

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth_router)

@app.get("/ingest")
def ingest():
    return ingest_user_music()

@app.get("/chat")
def chat(q: str):
    return {
        "response": agent(q)
    }
""",
    "frontend/index.html": """<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>VibeMap Cognition</title>
    <link rel="stylesheet" href="style.css">
    <link href="https://fonts.googleapis.com/css2?family=Libre+Baskerville:ital,wght@0,400;0,700;1,400&display=swap" rel="stylesheet">
</head>
<body>
    <div class="container">
        <header>
            <h1>VibeMap</h1>
            <p>Music Cognition & Reasoning Engine</p>
        </header>
        
        <div class="controls">
            <button id="loginBtn" class="btn">Connect to Spotify</button>
            <button id="ingestBtn" class="btn btn-secondary">Sync Memory (Qdrant)</button>
        </div>

        <div class="chat-container">
            <div id="chatHistory" class="chat-history">
                <div class="message system">Cognitive engine ready. Please authenticate.</div>
            </div>
            
            <div class="input-group">
                <input type="text" id="chatInput" placeholder="e.g. Build a playlist for rainy nights..." disabled>
                <button id="sendBtn" class="btn" disabled>Send</button>
            </div>
        </div>
    </div>
    <script src="app.js"></script>
</body>
</html>
""",
    "frontend/style.css": """
:root {
    --bg-color: #f7f7f5;
    --text-primary: #1d1d1f;
    --text-secondary: #86868b;
    --border-color: #d2d2d7;
    --accent-color: #000000;
}

body {
    background-color: var(--bg-color);
    color: var(--text-primary);
    font-family: 'Times New Roman', 'Libre Baskerville', serif;
    margin: 0;
    padding: 0;
    display: flex;
    justify-content: center;
    min-height: 100vh;
}

.container {
    width: 100%;
    max-width: 680px;
    padding: 3rem 1.5rem;
    display: flex;
    flex-direction: column;
    gap: 2rem;
}

header h1 {
    font-size: 2.5rem;
    font-weight: 700;
    margin: 0;
    letter-spacing: -0.02em;
}

header p {
    color: var(--text-secondary);
    font-size: 1rem;
    font-style: italic;
    margin: 0.5rem 0 0 0;
}

.controls {
    display: flex;
    gap: 1rem;
    padding-bottom: 2rem;
    border-bottom: 1px solid var(--border-color);
}

.btn {
    background-color: var(--accent-color);
    color: #ffffff;
    border: none;
    padding: 0.6rem 1.2rem;
    font-family: 'Times New Roman', 'Libre Baskerville', serif;
    font-size: 0.9rem;
    cursor: pointer;
    transition: opacity 0.2s;
    letter-spacing: 0.03em;
}

.btn:hover {
    opacity: 0.8;
}

.btn:disabled {
    opacity: 0.4;
    cursor: not-allowed;
}

.btn-secondary {
    background-color: transparent;
    color: var(--text-primary);
    border: 1px solid var(--accent-color);
}

.chat-container {
    display: flex;
    flex-direction: column;
    gap: 1.5rem;
}

.chat-history {
    min-height: 300px;
    max-height: 500px;
    overflow-y: auto;
    display: flex;
    flex-direction: column;
    gap: 1rem;
}

.message {
    padding: 1rem;
    line-height: 1.5;
    font-size: 1.05rem;
}

.system {
    color: var(--text-secondary);
    font-style: italic;
    font-size: 0.9rem;
    padding: 0;
}

.user-msg {
    border-left: 2px solid var(--border-color);
    padding-left: 1rem;
}

.agent-msg {
    border-left: 2px solid var(--accent-color);
    background-color: rgba(0,0,0,0.02);
}

.input-group {
    display: flex;
    gap: 0.5rem;
}

input[type="text"] {
    flex: 1;
    padding: 0.8rem 1rem;
    font-family: 'Times New Roman', 'Libre Baskerville', serif;
    font-size: 1rem;
    border: 1px solid var(--border-color);
    background-color: transparent;
    outline: none;
}

input[type="text"]:focus {
    border-color: var(--accent-color);
}
""",
    "frontend/app.js": """
const API_BASE = "http://127.0.0.1:8000";

const chatHistory = document.getElementById('chatHistory');
const chatInput = document.getElementById('chatInput');
const sendBtn = document.getElementById('sendBtn');
const loginBtn = document.getElementById('loginBtn');
const ingestBtn = document.getElementById('ingestBtn');

function appendMessage(text, type) {
    const div = document.createElement('div');
    div.className = `message ${type}-msg`;
    if (typeof text === 'object') {
        const pre = document.createElement('pre');
        pre.style.fontFamily = "monospace";
        pre.style.fontSize = "0.85rem";
        pre.textContent = JSON.stringify(text, null, 2);
        div.appendChild(pre);
    } else {
        div.textContent = text;
    }
    chatHistory.appendChild(div);
    chatHistory.scrollTop = chatHistory.scrollHeight;
}

loginBtn.addEventListener('click', () => {
    window.location.href = `${API_BASE}/login`;
});

ingestBtn.addEventListener('click', async () => {
    appendMessage("Initializing ingestion sequence...", "system");
    try {
        const res = await fetch(`${API_BASE}/ingest`);
        const data = await res.json();
        appendMessage(`Ingested ${data.ingested} tracks into Qdrant memory.`, "system");
        
        chatInput.disabled = false;
        sendBtn.disabled = false;
    } catch (err) {
        appendMessage(`Error: ${err.message}`, "system");
    }
});

sendBtn.addEventListener('click', async () => {
    const q = chatInput.value.trim();
    if (!q) return;
    
    appendMessage(q, "user");
    chatInput.value = "";
    
    try {
        const res = await fetch(`${API_BASE}/chat?q=${encodeURIComponent(q)}`);
        const data = await res.json();
        appendMessage(data.response, "agent");
    } catch (err) {
        appendMessage(`Agent Error: ${err.message}`, "agent");
    }
});

chatInput.addEventListener('keypress', (e) => {
    if (e.key === 'Enter') sendBtn.click();
});
"""
}

# Clear out the root old ones
old_files = ["backend/spotify.py", "backend/qdrant_client.py", "backend/recommender.py", "backend/tools.py", "backend/agent.py"]
for f in old_files:
    if os.path.exists(f):
        os.remove(f)

# Create folders
os.makedirs("backend/tools", exist_ok=True)
os.makedirs("backend/agent", exist_ok=True)
os.makedirs("frontend", exist_ok=True)

for path, content in files.items():
    with open(path, "w") as f:
        f.write(content)

print("Scaffolding complete!")
