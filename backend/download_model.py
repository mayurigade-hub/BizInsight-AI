from sentence_transformers import SentenceTransformer
import os

MODEL_ID = "Pardhiv17/bizinsight-complaint-embedder"
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
LOCAL_PATH = os.path.join(BASE_DIR, "models", "finetuned_complaint_model_final")

print(f"Downloading model from {MODEL_ID}...")
model = SentenceTransformer(MODEL_ID)
os.makedirs(LOCAL_PATH, exist_ok=True)
model.save(LOCAL_PATH)
print(f"Model saved to {LOCAL_PATH}")