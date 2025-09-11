"""
Example usage of the new functional API
"""
import asyncio
import logging
from typing import List

from models import LLMMessage, MessageRole, RAGSearchResult
from message_processing import get_conversation_history, format_messages_for_llm
from llm_service import call_llm_async
from rag_module.rag_client import search, add_document, health_check
from cache import get_cached_embedding, cache_embedding, get_cache_stats

logger = logging.getLogger(__name__)


async def example_rag_search():
    """Example of using the new RAG search functionality"""
    print("🔍 Example: RAG Search")
    
    # Search for relevant documents
    query = "How do I reset a password?"
    results = await search(query, top_k=3)
    
    print(f"Found {len(results)} results for query: '{query}'")
    for i, result in enumerate(results, 1):
        print(f"{i}. {result.title} (Score: {result.score:.3f})")
        print(f"   Content: {result.content[:100]}...")
        print(f"   URL: {result.url}")
        print()


async def example_llm_with_context():
    """Example of using LLM with RAG context"""
    print("🤖 Example: LLM with RAG Context")
    
    # Create messages
    messages = [
        LLMMessage(role=MessageRole.SYSTEM, content="You are a helpful assistant."),
        LLMMessage(role=MessageRole.USER, content="How do I reset a password?")
    ]
    
    # Get RAG context
    rag_results = await search("password reset", top_k=2)
    context = "\n".join([f"**{r.title}**\n{r.content}" for r in rag_results])
    
    # Call LLM with context
    response = await call_llm_async(messages, context)
    print(f"LLM Response: {response}")
    print()


async def example_caching():
    """Example of caching functionality"""
    print("💾 Example: Caching")
    
    # Check cache stats
    stats = await get_cache_stats()
    print(f"Cache stats: {stats}")
    
    # Example of embedding caching (would normally be done internally)
    text = "This is a test document for caching"
    cached_embedding = await get_cached_embedding(text)
    
    if cached_embedding is not None:
        print("Found cached embedding")
    else:
        print("No cached embedding found (this is expected for new text)")
    print()


async def example_health_checks():
    """Example of health checks"""
    print("🏥 Example: Health Checks")
    
    # Check RAG system health
    rag_healthy = await health_check()
    print(f"RAG system healthy: {rag_healthy}")
    
    # Check cache stats
    cache_stats = await get_cache_stats()
    print(f"Cache stats: {cache_stats}")
    print()


async def main():
    """Run all examples"""
    print("🚀 Running Functional API Examples\n")
    
    try:
        await example_rag_search()
        await example_llm_with_context()
        await example_caching()
        await example_health_checks()
        
        print("✅ All examples completed successfully!")
        
    except Exception as e:
        print(f"❌ Error running examples: {e}")
        logger.error(f"Example error: {e}")


if __name__ == "__main__":
    # Configure logging
    logging.basicConfig(level=logging.INFO)
    
    # Run examples
    asyncio.run(main())
