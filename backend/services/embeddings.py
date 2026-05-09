import os
import requests

def get_huggingface_embedding(text: str):
    api_url = "https://api-inference.huggingface.co/pipeline/feature-extraction/sentence-transformers/all-MiniLM-L6-v2"
    token = os.getenv("HF_TOKEN")
    headers = {"Authorization": f"Bearer {token}"} if token else {}
    
    try:
        response = requests.post(api_url, headers=headers, json={"inputs": [text], "options": {"wait_for_model": True}})
        if response.status_code == 200:
            return response.json()[0]
    except Exception as e:
        print("[Embeddings] Error contacting HF API:", e)
        
    print("[Embeddings] Fallback to zero vector")
    return [0.0] * 384

def embed_text(text: str):
    try:
        # Try local execution first if installed
        from sentence_transformers import SentenceTransformer
        # Note: In production we may not want to instantiate it every time, but this fallback
        # path is primarily for local testing where performance is less critical.
        model = SentenceTransformer("all-MiniLM-L6-v2")
        return model.encode(text).tolist()
    except ImportError:
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
