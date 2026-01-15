"""
Embedding Model wrapper for sentence-transformers.
"""

import numpy as np
from sentence_transformers import SentenceTransformer


class EmbeddingModel:
    """
    Wrapper for generating text embeddings.
    
    Usage:
        model = EmbeddingModel()
        embedding = model.embed("blue Nike shoes")
    """
    
    def __init__(self, model_name: str = "sentence-transformers/all-MiniLM-L6-v2"):
        """
        Initialize the embedding model.
        
        Args:
            model_name: HuggingFace model name or path.
        """
        self.model = SentenceTransformer(model_name)
        self.dimension = self.model.get_sentence_embedding_dimension()
    
    def embed(self, text: str) -> np.ndarray:
        """
        Generate embedding for a single text.
        
        Args:
            text: Input text to embed.
            
        Returns:
            Embedding vector as numpy array.
        """
        return self.model.encode(text, convert_to_numpy=True)
    
    def embed_batch(self, texts: list[str]) -> np.ndarray:
        """
        Generate embeddings for multiple texts.
        
        Args:
            texts: List of input texts.
            
        Returns:
            Matrix of embeddings (n_texts x dimension).
        """
        return self.model.encode(texts, convert_to_numpy=True)
    
    def similarity(self, text1: str, text2: str) -> float:
        """
        Calculate cosine similarity between two texts.
        
        Args:
            text1: First text.
            text2: Second text.
            
        Returns:
            Similarity score between 0 and 1.
        """
        emb1 = self.embed(text1)
        emb2 = self.embed(text2)
        
        return float(
            np.dot(emb1, emb2) / (np.linalg.norm(emb1) * np.linalg.norm(emb2))
        )
