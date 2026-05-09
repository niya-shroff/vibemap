import torch, os
from datasets import load_dataset
from transformers import ClapModel, ClapProcessor

from qdrant_client import QdrantClient
from qdrant_client.models import PointStruct

from core.config import *

DEVICE = "cuda" if torch.cuda.is_available() else "cpu"
SAMPLE_RATE = 48000
BATCH_SIZE = 8
COLLECTION_NAME = "audio_embeddings"

client = QdrantClient(url=QDRANT_URL, api_key=QDRANT_API_KEY)
model = ClapModel.from_pretrained("laion/clap-htsat-fused").to(DEVICE)
processor = ClapProcessor.from_pretrained("laion/clap-htsat-fused")

dataset = load_dataset("ashraq/esc50", split="train")

def index_audio():
    points = []
    for idx, sample in enumerate(dataset):
        waveform = sample["audio"]["array"]
        sr = sample["audio"]["sampling_rate"]
        emb = get_embedding(waveform)
        points.append(
            PointStruct(
                id=idx,
                vector=emb.tolist(),
                payload={
                    "label": sample["category"], 
                    "filename": sample["filename"],
                    "fold": sample["fold"],
                    "target": sample["target"],
                    "esc10": sample["esc10"],
                    "type": "env_sound"
                }
            )
        )
        if len(points) >= BATCH_SIZE:
            client.upsert(
                collection_name=COLLECTION_NAME,
                points=points,
                wait=True
            )
            print(f"Upserted {idx} samples")
            points = []
    if points:
        client.upsert(
            collection_name=COLLECTION_NAME,
            points=points,
            wait=True
        )

def get_embedding(audio_waveform):
    inputs = processor(
        audio=audio_waveform,
        sampling_rate=SAMPLE_RATE,
        return_tensors="pt"
    ).to(DEVICE)
    with torch.no_grad():
        emb = model.get_audio_features(**inputs)
    return emb.squeeze().cpu().numpy()

def search_audio(audio_waveform):
    emb = get_embedding(audio_waveform)
    results = client.query_points(
        collection_name=COLLECTION_NAME,
        query=emb.tolist(),
        limit=5
    )
    print(results)

if __name__ == "__main__":
    index_audio()
    sample = dataset[0]["audio"]["array"]
    search_audio(sample)