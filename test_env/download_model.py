import os
os.environ["HF_ENDPOINT"] = "https://hf-mirror.com"
from sentence_transformers import SentenceTransformer

# This will automatically download and cache the model
model = SentenceTransformer('BAAI/bge-base-en-v1.5')
print("Model downloaded successfully!")
