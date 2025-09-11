"""
LLM service functions - Functional approach with async support
"""
import logging
import asyncio
import aiohttp
import json
import hashlib
from typing import List, Optional

from .models import LLMMessage
from .config import settings
from .cache import get_cached_llm_response, cache_llm_response, generate_query_hash

logger = logging.getLogger(__name__)


async def call_llm_async(
    messages: List[LLMMessage], 
    context: Optional[str] = None
) -> str:
    """Enhanced async LLM call with optional RAG context and caching"""
    # Early returns for error conditions
    if not messages:
        logger.warning("No messages provided for LLM call")
        return "I need a message to process. Please try again."
    
    if not any(msg.content.strip() for msg in messages):
        logger.warning("All messages are empty")
        return "I received empty messages. Please try again."
    
    try:
        # Convert Pydantic models to dict for API call
        messages_dict = [{"role": msg.role.value, "content": msg.content} for msg in messages]
        
        # If context is provided, enhance the system message
        if context and messages_dict:
            enhanced_system = messages_dict[0].copy()
            enhanced_system["content"] += f"\n\nRelevant context from knowledge base:\n{context}"
            messages_dict = [enhanced_system] + messages_dict[1:]
        
        # Generate query hash for caching
        query_hash = generate_query_hash(messages_dict, context)
        
        # Check cache first
        cached_response = await get_cached_llm_response(query_hash)
        if cached_response:
            logger.debug("Using cached LLM response")
            return cached_response
        
        # Prepare payload
        payload = {
            "messages": messages_dict,
            "temperature": 0.3,
            "max_tokens": settings.max_tokens,
            "top_p": 0.9,
            "stream": False
        }
        
        headers = {
            "Content-Type": "application/json",
            "User-Agent": "SlackBot/1.0"
        }
        
        if settings.llm_api_key:
            headers["Authorization"] = f"Bearer {settings.llm_api_key}"
        
        # Make async request
        async with aiohttp.ClientSession() as session:
            async with session.post(
                settings.llm_api_endpoint,
                headers=headers,
                json=payload,
                timeout=aiohttp.ClientTimeout(total=settings.llm_timeout)
            ) as response:
                
                response.raise_for_status()
                result = await response.json()
                
                if (result and 'choices' in result and 
                    result['choices'] and 
                    'message' in result['choices'][0] and
                    'content' in result['choices'][0]['message']):
                    
                    content = result['choices'][0]['message']['content'].strip()
                    
                    # Truncate if too long for Slack
                    if len(content) > settings.max_message_length:
                        content = content[:settings.max_message_length-50] + "... [truncated]"
                    
                    # Cache the response
                    await cache_llm_response(query_hash, content)
                    
                    logger.info(f"LLM request completed successfully, response length: {len(content)}")
                    return content
                else:
                    logger.error(f"Unexpected LLM response format: {result}")
                    return "I received an unexpected response format. Please try again."
                    
    except asyncio.TimeoutError:
        logger.error("LLM request timed out")
        return "The request took too long to process. Please try a simpler question."
        
    except aiohttp.ClientError as e:
        logger.error(f"LLM request failed: {e}")
        return "I'm having trouble connecting to my knowledge base. Please try again later."
        
    except Exception as e:
        logger.error(f"Unexpected error in LLM call: {e}")
        return "An unexpected error occurred. Please try again."


def call_llm_sync(messages: List[LLMMessage], context: Optional[str] = None) -> str:
    """Synchronous wrapper for LLM calls (for backward compatibility)"""
    return asyncio.run(call_llm_async(messages, context))


# Backward compatibility - create an LLMService class that wraps the functional API
class LLMService:
    """Backward compatibility wrapper for LLM operations"""
    
    def __init__(self, endpoint: str = None, api_key: Optional[str] = None):
        # Store these for potential future use
        self.endpoint = endpoint or settings.llm_api_endpoint
        self.api_key = api_key or settings.llm_api_key
    
    async def call_llm(self, messages: List[LLMMessage], context: Optional[str] = None) -> str:
        """Call LLM with async support"""
        return await call_llm_async(messages, context)
    
    def call_llm_sync(self, messages: List[LLMMessage], context: Optional[str] = None) -> str:
        """Call LLM synchronously"""
        return call_llm_sync(messages, context)
