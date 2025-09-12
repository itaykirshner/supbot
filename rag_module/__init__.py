"""
RAG Module for Slack Bot
Provides vector search and retrieval capabilities
"""

from rag_module.rag_client import RAGClient
from rag_module.embeddings import EmbeddingService
from rag_module.utils import clean_text, chunk_text

__version__ = "1.0.0"
__all__ = ["RAGClient", "EmbeddingService", "clean_text", "chunk_text"]
