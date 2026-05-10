import os
os.environ["TOKENIZERS_PARALLELISM"] = "false"
import requests

def get_huggingface_embedding(text: str):
    api_url = "https://api-inference.huggingface.co/pipeline/feature-extraction/sentence-transformers/all-MiniLM-L6-v2"
    token = os.getenv("HUGGING_FACE_TOKEN")
    headers = {"Authorization": f"Bearer {token}"} if token else {}
    
    print(f"[Embeddings] Calling Hugging Face API for text: {text[:50]}...")
    try:
        response = requests.post(api_url, headers=headers, json={"inputs": [text], "options": {"wait_for_model": True}})
        if response.status_code == 200:
            print("[Embeddings] Successfully got embedding from HF API")
            return response.json()[0]
        else:
            print(f"[Embeddings] HF API returned status {response.status_code}: {response.text}")
    except Exception as e:
        print("[Embeddings] Error contacting HF API:", e)
        
    print("[Embeddings] Fallback to zero vector")
    return [0.0] * 384

# Initialize SentenceTransformer globally to prevent deadlocks in multithreaded environments
LOCAL_MODEL = None
try:
    from sentence_transformers import SentenceTransformer
    print("[Embeddings] Loading local SentenceTransformer model...")
    LOCAL_MODEL = SentenceTransformer("all-MiniLM-L6-v2")
    print("[Embeddings] Local model loaded successfully.")
except ImportError:
    print("[Embeddings] SentenceTransformer not installed, using HF API fallback.")

def embed_text(text: str):
    if LOCAL_MODEL is not None:
        try:
            print("[Embeddings] Creating local embedding...")
            result = LOCAL_MODEL.encode(text).tolist()
            return result
        except Exception as e:
            print(f"[Embeddings] Local embedding failed: {e}")
            return get_huggingface_embedding(text)
    else:
        # On Vercel, use API fallback
        return get_huggingface_embedding(text)

def embed_track(track):
    text = f"{track['name']} {track['artists'][0]['name']}"
    
    # Infuse sonic properties into semantic space if available
    af = track.get("audio_features")
    if af:
        metrics = [
            f"danceable score {af.get('danceability', 0)}",
            f"energy {af.get('energy', 0)}", 
            f"valence {af.get('valence', 0)}",
            f"acousticness {af.get('acousticness', 0)}",
            f"instrumentalness {af.get('instrumentalness', 0)}"
        ]
        text += f" | Sonic features: {', '.join(metrics)}"
        
    return embed_text(text)
