"""
RAG operations with ChromaDB - Functional approach with async support
"""
import logging
import asyncio
from typing import List, Dict, Optional, Any, Tuple
import chromadb
from chromadb.config import Settings
import numpy as np

from .embeddings import get_embedding_service
from .utils import clean_text
from ..slack_app.cache import get_cached_embedding, cache_embedding
from ..slack_app.models import RAGSearchResult, DocumentChunk
from ..slack_app.config import settings

logger = logging.getLogger(__name__)

# Global ChromaDB client and collection
_chroma_client = None
_chroma_collection = None


async def get_chroma_client() -> chromadb.HttpClient:
    """Get ChromaDB client instance"""
    global _chroma_client
    
    if _chroma_client is None:
        try:
            logger.info(f"Connecting to ChromaDB at {settings.chromadb_host}:{settings.chromadb_port}")
            
            _chroma_client = chromadb.HttpClient(
                host=settings.chromadb_host,
                port=settings.chromadb_port,
                settings=Settings(
                    anonymized_telemetry=False,
                    allow_reset=False
                )
            )
            
            # Test connection
            heartbeat = _chroma_client.heartbeat()
            logger.info(f"ChromaDB connection successful: {heartbeat}")
            
        except Exception as e:
            logger.error(f"Failed to initialize ChromaDB client: {e}")
            raise
    
    return _chroma_client


async def get_chroma_collection(collection_name: str = "knowledge_base") -> Any:
    """Get ChromaDB collection instance"""
    global _chroma_collection
    
    if _chroma_collection is None:
        try:
            client = await get_chroma_client()
            
            # Get or create collection
            _chroma_collection = client.get_or_create_collection(
                name=collection_name,
                metadata={"description": "Knowledge base for Slack bot"}
            )
            
            logger.info(f"Connected to collection: {collection_name}")
            
        except Exception as e:
            logger.error(f"Failed to get ChromaDB collection: {e}")
            raise
    
    return _chroma_collection


async def add_document(
    document_id: str, 
    content: str, 
    metadata: Dict[str, Any],
    collection_name: str = "knowledge_base"
) -> bool:
    """Add a single document to the knowledge base"""
    # Early returns for error conditions
    if not document_id or not document_id.strip():
        logger.warning("Document ID cannot be empty")
        return False
    
    if not content or not content.strip():
        logger.warning(f"Document {document_id} has no content")
        return False
    
    if not metadata:
        logger.warning(f"Document {document_id} has no metadata")
        return False
    
    try:
        # Get collection
        collection = await get_chroma_collection(collection_name)
        
        # Check cache first
        cached_embedding = await get_cached_embedding(content)
        if cached_embedding is not None:
            embedding = cached_embedding
            logger.debug(f"Using cached embedding for document: {document_id}")
        else:
            # Generate embedding
            embedding_service = get_embedding_service()
            embedding = embedding_service.encode(content)
            
            # Cache the embedding
            await cache_embedding(content, embedding)
            logger.debug(f"Generated and cached embedding for document: {document_id}")
        
        # Add to collection
        collection.add(
            ids=[document_id],
            embeddings=[embedding.tolist()],
            documents=[content],
            metadatas=[metadata]
        )
        
        logger.debug(f"Added document: {document_id}")
        return True
        
    except Exception as e:
        logger.error(f"Failed to add document {document_id}: {e}")
        return False


async def add_documents_batch(
    documents: List[DocumentChunk],
    collection_name: str = "knowledge_base"
) -> int:
    """Add multiple documents in batch"""
    if not documents:
        return 0
    
    try:
        # Get collection
        collection = await get_chroma_collection(collection_name)
        
        ids = []
        contents = []
        metadatas = []
        texts_to_embed = []
        embedding_indices = []
        
        # Prepare data and check cache
        for i, doc in enumerate(documents):
            if not doc.id or not doc.content:
                logger.warning(f"Skipping invalid document at index {i}")
                continue
                
            ids.append(doc.id)
            contents.append(doc.content)
            metadatas.append(doc.metadata)
            
            # Check if we have cached embedding
            cached_embedding = await get_cached_embedding(doc.content)
            if cached_embedding is not None:
                # We'll handle cached embeddings separately
                texts_to_embed.append(None)
                embedding_indices.append((i, cached_embedding))
            else:
                texts_to_embed.append(doc.content)
                embedding_indices.append(i)
        
        # Generate embeddings for non-cached texts
        embedding_service = get_embedding_service()
        texts_to_embed_filtered = [text for text in texts_to_embed if text is not None]
        
        if texts_to_embed_filtered:
            new_embeddings = embedding_service.encode_batch(texts_to_embed_filtered)
            
            # Cache new embeddings
            for text, embedding in zip(texts_to_embed_filtered, new_embeddings):
                await cache_embedding(text, embedding)
        
        # Prepare final embeddings list
        embeddings = []
        text_index = 0
        
        for i, item in enumerate(embedding_indices):
            if isinstance(item, tuple):
                # Cached embedding
                embeddings.append(item[1].tolist())
            else:
                # New embedding
                embeddings.append(new_embeddings[text_index].tolist())
                text_index += 1
        
        # Add to collection
        collection.add(
            ids=ids,
            embeddings=embeddings,
            documents=contents,
            metadatas=metadatas
        )
        
        logger.info(f"Added {len(documents)} documents to knowledge base")
        return len(documents)
        
    except Exception as e:
        logger.error(f"Failed to add document batch: {e}")
        return 0


async def search(
    query: str, 
    top_k: int = 5,
    filters: Optional[Dict[str, Any]] = None,
    collection_name: str = "knowledge_base"
) -> List[RAGSearchResult]:
    """Search for relevant documents"""
    # Early returns for error conditions
    if not query or not query.strip():
        logger.warning("Search query cannot be empty")
        return []
    
    if top_k <= 0:
        logger.warning(f"Invalid top_k value: {top_k}")
        return []
    
    try:
        # Get collection
        collection = await get_chroma_collection(collection_name)
        
        # Clean query
        clean_query = clean_text(query)
        if not clean_query:
            logger.warning("Query became empty after cleaning")
            return []
        
        # Check cache for query embedding
        cached_embedding = await get_cached_embedding(clean_query)
        if cached_embedding is not None:
            query_embedding = cached_embedding
            logger.debug(f"Using cached embedding for query: {query[:50]}...")
        else:
            # Generate embedding
            embedding_service = get_embedding_service()
            query_embedding = embedding_service.encode(clean_query)
            
            # Cache the embedding
            await cache_embedding(clean_query, query_embedding)
            logger.debug(f"Generated and cached embedding for query: {query[:50]}...")
        
        # Prepare search parameters
        search_params = {
            "query_embeddings": [query_embedding.tolist()],
            "n_results": top_k
        }
        
        # Only add where clause if filters exist and are not empty
        if filters and any(filters.values() if isinstance(filters, dict) else [filters]):
            search_params["where"] = filters
        
        # Search collection
        results = collection.query(**search_params)
        
        # Format results using Pydantic models
        formatted_results = []
        if results['documents'] and results['documents'][0]:
            for i, doc in enumerate(results['documents'][0]):
                metadata = results['metadatas'][0][i] if results['metadatas'][0] else {}
                distance = results['distances'][0][i] if results['distances'] else None
                
                try:
                    result = RAGSearchResult(
                        content=doc,
                        metadata=metadata,
                        score=1 - distance if distance is not None else 0.0,
                        title=metadata.get('title', 'Untitled'),
                        url=metadata.get('url', ''),
                        type=metadata.get('type', 'unknown')
                    )
                    formatted_results.append(result)
                except Exception as e:
                    logger.warning(f"Failed to create RAGSearchResult for document {i}: {e}")
                    continue
        
        logger.debug(f"Found {len(formatted_results)} results for query: {query[:50]}...")
        return formatted_results
        
    except Exception as e:
        logger.error(f"Search failed for query '{query}': {e}")
        return []


async def delete_documents(
    document_ids: List[str],
    collection_name: str = "knowledge_base"
) -> bool:
    """Delete documents by IDs"""
    # Early returns for error conditions
    if not document_ids:
        logger.warning("No document IDs provided for deletion")
        return False
    
    if not all(doc_id and doc_id.strip() for doc_id in document_ids):
        logger.warning("Some document IDs are empty or invalid")
        return False
    
    try:
        collection = await get_chroma_collection(collection_name)
        collection.delete(ids=document_ids)
        logger.info(f"Deleted {len(document_ids)} documents")
        return True
    except Exception as e:
        logger.error(f"Failed to delete documents: {e}")
        return False


async def get_collection_stats(collection_name: str = "knowledge_base") -> Dict[str, Any]:
    """Get collection statistics"""
    try:
        collection = await get_chroma_collection(collection_name)
        count = collection.count()
        return {
            'collection_name': collection_name,
            'document_count': count,
            'status': 'healthy'
        }
    except Exception as e:
        logger.error(f"Failed to get collection stats: {e}")
        return {
            'collection_name': collection_name,
            'document_count': 0,
            'status': 'error',
            'error': str(e)
        }


async def health_check() -> bool:
    """Check if RAG system is healthy"""
    try:
        # Get client and test connection
        client = await get_chroma_client()
        
        # Try heartbeat first
        try:
            heartbeat = client.heartbeat()
            logger.debug(f"ChromaDB heartbeat successful: {heartbeat}")
        except Exception as e:
            # If heartbeat fails, try list_collections as alternative
            logger.debug(f"Heartbeat failed, trying alternative health check: {e}")
            collections = client.list_collections()
            logger.debug(f"Alternative health check successful: {len(collections)} collections")
        
        # Test collection access
        collection = await get_chroma_collection()
        collection.count()
        return True
    except Exception as e:
        logger.error(f"RAG health check failed: {e}")
        return False


# Backward compatibility - create a RAGClient class that wraps the functional API
class RAGClient:
    """Backward compatibility wrapper for RAG operations"""
    
    def __init__(self, 
                 chroma_host: str = None, 
                 chroma_port: int = None,
                 collection_name: str = "knowledge_base"):
        self.collection_name = collection_name
        # Store these for potential future use
        self._chroma_host = chroma_host
        self._chroma_port = chroma_port
    
    async def add_document(self, document_id: str, content: str, metadata: Dict[str, Any]) -> bool:
        """Add a single document to the knowledge base"""
        return await add_document(document_id, content, metadata, self.collection_name)
    
    async def add_documents_batch(self, documents: List[DocumentChunk]) -> int:
        """Add multiple documents in batch"""
        return await add_documents_batch(documents, self.collection_name)
    
    async def search(self, query: str, top_k: int = 5, filters: Optional[Dict[str, Any]] = None) -> List[RAGSearchResult]:
        """Search for relevant documents"""
        return await search(query, top_k, filters, self.collection_name)
    
    async def delete_documents(self, document_ids: List[str]) -> bool:
        """Delete documents by IDs"""
        return await delete_documents(document_ids, self.collection_name)
    
    async def get_collection_stats(self) -> Dict[str, Any]:
        """Get collection statistics"""
        return await get_collection_stats(self.collection_name)
    
    async def health_check(self) -> bool:
        """Check if RAG system is healthy"""
        return await health_check()
