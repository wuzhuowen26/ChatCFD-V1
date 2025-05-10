from sentence_transformers import SentenceTransformer
import torch

"""
Repo directory: /home/hk/bge-base-en-v1.5
"""

# Check AMD GPU availability
print(f"GPU Available: {torch.cuda.is_available()}")
print(f"GPU Name: {torch.cuda.get_device_name(0) if torch.cuda.is_available() else 'None'}")

# Load model with AMD optimization
# model = SentenceTransformer('sentence-transformers/all-mpnet-base-v2', 
#                           device='cuda' if torch.cuda.is_available() else 'cpu')
# model = SentenceTransformer("/home/hk/bge-base-en-v1.5")
model = SentenceTransformer("/home/hk/all-mpnet-base-v2")

# Test embeddings
sentences = [
    "Turbulence model: SST k-omega with wall functions",
    "Finite volume discretization using second-order upwind scheme",
    "Mesh independence study with 1.2 million hexahedral cells"
]

embeddings = model.encode(sentences)

# Quick similarity check
print(f"Similarity 0-1: {embeddings[0] @ embeddings[1].T:.3f}")
print(f"Similarity 0-2: {embeddings[0] @ embeddings[2].T:.3f}")
