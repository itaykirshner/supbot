"""
Caching layer for embeddings and responses
"""
import json
import hashlib
import logging
from typing import Optional, List, Dict, Any, Union
from datetime import datetime, timedelta
import asyncio
import numpy as np

from .config import settings
from .models import EmbeddingCacheEntry, LLMCacheEntry

logger = logging.getLogger(__name__)

# Global cache instances
_redis_client = None
_memory_cache = {}


async def get_redis_client():
    """Get Redis client instance"""
    global _redis_client
    
    if _redis_client is None and settings.redis_enabled:
        try:
            import redis.asyncio as redis
            
            _redis_client = redis.Redis(
                host=settings.redis_host,
                port=settings.redis_port,
                password=settings.redis_password,
                db=settings.redis_db,
                decode_responses=True
            )
            
            # Test connection
            await _redis_client.ping()
            logger.info("Redis client initialized successfully")
            
        except ImportError:
            logger.warning("Redis not available, falling back to memory cache")
            _redis_client = None
        except Exception as e:
            logger.warning(f"Failed to initialize Redis client: {e}, falling back to memory cache")
            _redis_client = None
    
    return _redis_client


def _generate_cache_key(prefix: str, content: str) -> str:
    """Generate cache key from content"""
    content_hash = hashlib.md5(content.encode('utf-8')).hexdigest()
    return f"{prefix}:{content_hash}"


async def get_cached_embedding(text: str) -> Optional[np.ndarray]:
    """Get cached embedding for text"""
    if not text or not text.strip():
        return None
    
    cache_key = _generate_cache_key("embedding", text)
    
    try:
        # Try Redis first
        redis_client = await get_redis_client()
        if redis_client:
            cached_data = await redis_client.get(cache_key)
            if cached_data:
                entry = EmbeddingCacheEntry.parse_raw(cached_data)
                if entry.expires_at > datetime.utcnow():
                    logger.debug(f"Cache hit for embedding: {text[:50]}...")
                    return np.array(entry.embedding)
                else:
                    # Expired, remove from cache
                    await redis_client.delete(cache_key)
        
        # Try memory cache
        if cache_key in _memory_cache:
            entry = _memory_cache[cache_key]
            if entry.expires_at > datetime.utcnow():
                logger.debug(f"Memory cache hit for embedding: {text[:50]}...")
                return np.array(entry.embedding)
            else:
                # Expired, remove from memory cache
                del _memory_cache[cache_key]
    
    except Exception as e:
        logger.warning(f"Error getting cached embedding: {e}")
    
    return None


async def cache_embedding(text: str, embedding: np.ndarray, ttl: Optional[int] = None) -> None:
    """Cache embedding for text"""
    if not text or not text.strip() or embedding is None:
        return
    
    ttl = ttl or settings.cache_ttl_embeddings
    expires_at = datetime.utcnow() + timedelta(seconds=ttl)
    
    cache_key = _generate_cache_key("embedding", text)
    entry = EmbeddingCacheEntry(
        text=text,
        embedding=embedding.tolist(),
        created_at=datetime.utcnow(),
        expires_at=expires_at
    )
    
    try:
        # Cache in Redis
        redis_client = await get_redis_client()
        if redis_client:
            await redis_client.setex(
                cache_key,
                ttl,
                entry.json()
            )
            logger.debug(f"Cached embedding in Redis: {text[:50]}...")
        
        # Cache in memory as backup
        _memory_cache[cache_key] = entry
        logger.debug(f"Cached embedding in memory: {text[:50]}...")
        
    except Exception as e:
        logger.warning(f"Error caching embedding: {e}")


async def get_cached_llm_response(query_hash: str) -> Optional[str]:
    """Get cached LLM response"""
    if not query_hash:
        return None
    
    cache_key = _generate_cache_key("llm", query_hash)
    
    try:
        # Try Redis first
        redis_client = await get_redis_client()
        if redis_client:
            cached_data = await redis_client.get(cache_key)
            if cached_data:
                entry = LLMCacheEntry.parse_raw(cached_data)
                if entry.expires_at > datetime.utcnow():
                    logger.debug(f"Cache hit for LLM response: {query_hash[:16]}...")
                    return entry.response
                else:
                    # Expired, remove from cache
                    await redis_client.delete(cache_key)
        
        # Try memory cache
        if cache_key in _memory_cache:
            entry = _memory_cache[cache_key]
            if entry.expires_at > datetime.utcnow():
                logger.debug(f"Memory cache hit for LLM response: {query_hash[:16]}...")
                return entry.response
            else:
                # Expired, remove from memory cache
                del _memory_cache[cache_key]
    
    except Exception as e:
        logger.warning(f"Error getting cached LLM response: {e}")
    
    return None


async def cache_llm_response(query_hash: str, response: str, ttl: Optional[int] = None) -> None:
    """Cache LLM response"""
    if not query_hash or not response:
        return
    
    ttl = ttl or settings.cache_ttl_responses
    expires_at = datetime.utcnow() + timedelta(seconds=ttl)
    
    cache_key = _generate_cache_key("llm", query_hash)
    entry = LLMCacheEntry(
        query_hash=query_hash,
        response=response,
        created_at=datetime.utcnow(),
        expires_at=expires_at
    )
    
    try:
        # Cache in Redis
        redis_client = await get_redis_client()
        if redis_client:
            await redis_client.setex(
                cache_key,
                ttl,
                entry.json()
            )
            logger.debug(f"Cached LLM response in Redis: {query_hash[:16]}...")
        
        # Cache in memory as backup
        _memory_cache[cache_key] = entry
        logger.debug(f"Cached LLM response in memory: {query_hash[:16]}...")
        
    except Exception as e:
        logger.warning(f"Error caching LLM response: {e}")


def generate_query_hash(messages: List[Dict[str, Any]], context: Optional[str] = None) -> str:
    """Generate hash for query caching"""
    query_data = {
        "messages": messages,
        "context": context or ""
    }
    query_str = json.dumps(query_data, sort_keys=True)
    return hashlib.md5(query_str.encode('utf-8')).hexdigest()


async def get_cached_rag_context(query: str) -> Optional[str]:
    """Get cached RAG context"""
    if not query or not query.strip():
        return None
    
    cache_key = _generate_cache_key("rag", query)
    
    try:
        # Try Redis first
        redis_client = await get_redis_client()
        if redis_client:
            cached_data = await redis_client.get(cache_key)
            if cached_data:
                logger.debug(f"Cache hit for RAG context: {query[:50]}...")
                return cached_data
        
        # Try memory cache
        if cache_key in _memory_cache:
            logger.debug(f"Memory cache hit for RAG context: {query[:50]}...")
            return _memory_cache[cache_key]
    
    except Exception as e:
        logger.warning(f"Error getting cached RAG context: {e}")
    
    return None


async def cache_rag_context(query: str, context: str, ttl: Optional[int] = None) -> None:
    """Cache RAG context"""
    if not query or not context:
        return
    
    ttl = ttl or settings.cache_ttl_embeddings
    cache_key = _generate_cache_key("rag", query)
    
    try:
        # Cache in Redis
        redis_client = await get_redis_client()
        if redis_client:
            await redis_client.setex(
                cache_key,
                ttl,
                context
            )
            logger.debug(f"Cached RAG context in Redis: {query[:50]}...")
        
        # Cache in memory as backup
        _memory_cache[cache_key] = context
        logger.debug(f"Cached RAG context in memory: {query[:50]}...")
        
    except Exception as e:
        logger.warning(f"Error caching RAG context: {e}")


async def clear_cache(pattern: str = "*") -> int:
    """Clear cache entries matching pattern"""
    cleared_count = 0
    
    try:
        # Clear Redis cache
        redis_client = await get_redis_client()
        if redis_client:
            keys = await redis_client.keys(pattern)
            if keys:
                cleared_count += await redis_client.delete(*keys)
                logger.info(f"Cleared {cleared_count} entries from Redis cache")
        
        # Clear memory cache
        if pattern == "*":
            cleared_count += len(_memory_cache)
            _memory_cache.clear()
            logger.info(f"Cleared {cleared_count} entries from memory cache")
        else:
            # Clear specific pattern from memory cache
            keys_to_remove = [k for k in _memory_cache.keys() if pattern.replace("*", "") in k]
            for key in keys_to_remove:
                del _memory_cache[key]
            cleared_count += len(keys_to_remove)
            logger.info(f"Cleared {len(keys_to_remove)} entries from memory cache")
    
    except Exception as e:
        logger.warning(f"Error clearing cache: {e}")
    
    return cleared_count


async def get_cache_stats() -> Dict[str, Any]:
    """Get cache statistics"""
    stats = {
        "redis_enabled": settings.redis_enabled,
        "memory_cache_size": len(_memory_cache),
        "redis_connected": False,
        "redis_memory_usage": 0
    }
    
    try:
        redis_client = await get_redis_client()
        if redis_client:
            stats["redis_connected"] = True
            info = await redis_client.info("memory")
            stats["redis_memory_usage"] = info.get("used_memory", 0)
    
    except Exception as e:
        logger.warning(f"Error getting cache stats: {e}")
    
    return stats
