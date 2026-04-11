from sentence_transformers import SentenceTransformer

model = SentenceTransformer('all-MiniLM-L6-v2')

def embed_track(track):
    text = f"{track['name']} by {track['artist']}"
    return model.encode(text).tolist()
