import logging
import os
from typing import List, Union
from sentence_transformers import SentenceTransformer
import numpy as np

logger = logging.getLogger(__name__)

class EmbeddingService:
    """Handles text embedding generation"""
    
    def __init__(self, model_name: str = None):
        self.model_name = model_name or os.environ.get("EMBEDDING_MODEL", "all-MiniLM-L6-v2")
        self.model = None
        self._initialize_model()
    
    def _initialize_model(self):
        """Initialize the embedding model"""
        try:
            logger.info(f"Loading embedding model: {self.model_name}")
            self.model = SentenceTransformer(self.model_name)
            logger.info("Embedding model loaded successfully")
        except Exception as e:
            logger.error(f"Failed to load embedding model: {e}")
            raise
    
    def encode(self, texts: Union[str, List[str]]) -> Union[np.ndarray, List[np.ndarray]]:
        """Generate embeddings for text(s)"""
        if not self.model:
            raise RuntimeError("Embedding model not initialized")
        
        try:
            if isinstance(texts, str):
                return self.model.encode(texts)
            else:
                return self.model.encode(texts)
        except Exception as e:
            logger.error(f"Failed to generate embeddings: {e}")
            raise
    
    def encode_batch(self, texts: List[str], batch_size: int = 32) -> List[np.ndarray]:
        """Generate embeddings for a batch of texts"""
        if not texts:
            return []
        
        embeddings = []
        for i in range(0, len(texts), batch_size):
            batch = texts[i:i + batch_size]
            batch_embeddings = self.encode(batch)
            if isinstance(batch_embeddings, np.ndarray) and len(batch_embeddings.shape) == 1:
                # Single embedding
                embeddings.append(batch_embeddings)
            else:
                # Multiple embeddings
                embeddings.extend(batch_embeddings)
        
        return embeddings
