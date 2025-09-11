"""
Text embedding generation - Functional approach
"""
import logging
from typing import List, Union, Optional
from sentence_transformers import SentenceTransformer
import numpy as np

from ..slack_app.config import settings

logger = logging.getLogger(__name__)

# Global embedding model instance
_embedding_model = None


def get_embedding_service() -> SentenceTransformer:
    """Get embedding model instance"""
    global _embedding_model
    
    if _embedding_model is None:
        try:
            logger.info(f"Loading embedding model: {settings.embedding_model}")
            _embedding_model = SentenceTransformer(settings.embedding_model)
            logger.info("Embedding model loaded successfully")
        except Exception as e:
            logger.error(f"Failed to load embedding model: {e}")
            raise
    
    return _embedding_model


def encode_text(texts: Union[str, List[str]]) -> Union[np.ndarray, List[np.ndarray]]:
    """Generate embeddings for text(s)"""
    # Early returns for error conditions
    if not texts:
        logger.warning("No text provided for embedding")
        return np.array([]) if isinstance(texts, str) else []
    
    if isinstance(texts, str) and not texts.strip():
        logger.warning("Empty text provided for embedding")
        return np.array([])
    
    if isinstance(texts, list) and not any(text.strip() for text in texts if text):
        logger.warning("All texts are empty")
        return []
    
    try:
        model = get_embedding_service()
        return model.encode(texts)
    except Exception as e:
        logger.error(f"Failed to generate embeddings: {e}")
        raise


def encode_batch(texts: List[str], batch_size: Optional[int] = None) -> List[np.ndarray]:
    """Generate embeddings for a batch of texts"""
    # Early returns for error conditions
    if not texts:
        return []
    
    if not any(text and text.strip() for text in texts):
        logger.warning("All texts are empty")
        return []
    
    batch_size = batch_size or settings.batch_size_embeddings
    
    try:
        model = get_embedding_service()
        embeddings = []
        
        for i in range(0, len(texts), batch_size):
            batch = texts[i:i + batch_size]
            # Filter out empty texts
            valid_batch = [text for text in batch if text and text.strip()]
            
            if not valid_batch:
                continue
            
            batch_embeddings = model.encode(valid_batch)
            
            if isinstance(batch_embeddings, np.ndarray) and len(batch_embeddings.shape) == 1:
                # Single embedding
                embeddings.append(batch_embeddings)
            else:
                # Multiple embeddings
                embeddings.extend(batch_embeddings)
        
        logger.debug(f"Generated {len(embeddings)} embeddings for {len(texts)} texts")
        return embeddings
        
    except Exception as e:
        logger.error(f"Failed to generate batch embeddings: {e}")
        raise


# Backward compatibility - create an EmbeddingService class that wraps the functional API
class EmbeddingService:
    """Backward compatibility wrapper for embedding operations"""
    
    def __init__(self, model_name: str = None):
        # Store model name for potential future use
        self.model_name = model_name or settings.embedding_model
    
    def encode(self, texts: Union[str, List[str]]) -> Union[np.ndarray, List[np.ndarray]]:
        """Generate embeddings for text(s)"""
        return encode_text(texts)
    
    def encode_batch(self, texts: List[str], batch_size: int = 32) -> List[np.ndarray]:
        """Generate embeddings for a batch of texts"""
        return encode_batch(texts, batch_size)
