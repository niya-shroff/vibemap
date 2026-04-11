from sentence_transformers import SentenceTransformer

model = SentenceTransformer("all-MiniLM-L6-v2")

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
        
    return model.encode(text).tolist()

def embed_text(text):
    return model.encode(text).tolist()
