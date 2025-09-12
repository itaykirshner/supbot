"""
RAG Module for Slack Bot
Provides vector search and retrieval capabilities
"""

# Import functional methods
from rag_module.rag_client import (
    add_document, add_documents_batch, search, delete_documents, 
    get_collection_stats, health_check, RAGClient
)
from rag_module.embeddings import (
    encode_text, encode_batch, get_embedding_service, EmbeddingService
)
from rag_module.utils import clean_text, chunk_text

__version__ = "1.0.0"
__all__ = [
    "add_document", "add_documents_batch", "search", "delete_documents", 
    "get_collection_stats", "health_check", "RAGClient",
    "encode_text", "encode_batch", "get_embedding_service", "EmbeddingService",
    "clean_text", "chunk_text"
]
