import logging
import os
import sys
import signal
import asyncio
from pathlib import Path

from concurrent.futures import ThreadPoolExecutor
from typing import List, Dict, Optional
import re
import json
import requests
import time

from slack_sdk import WebClient
from slack_sdk.errors import SlackApiError
from slack_bolt import App
from slack_bolt.adapter.socket_mode import SocketModeHandler

# Import our modules
from config import settings
from health import HealthChecker, HealthServer
from rag_module.rag_client import search as search_rag, health_check as rag_health_check
from message_processing import get_conversation_history, format_messages_for_llm, is_simple_greeting, get_bot_user_id, clean_message_text
from llm_service import call_llm_async
from cache import get_cached_rag_context, cache_rag_context

# Configure logging BEFORE importing other modules
logging.basicConfig(
    level=getattr(logging, settings.log_level.value),
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

# Set specific loggers to DEBUG level to reduce noise
logging.getLogger("httpx").setLevel(logging.WARNING)  # Reduce httpx noise
logging.getLogger("chromadb").setLevel(logging.WARNING)  # Reduce ChromaDB noise
logging.getLogger("sentence_transformers").setLevel(logging.WARNING)  # Reduce model loading noise

logger = logging.getLogger(__name__)

# Initialize Slack app
app = App(token=settings.slack_bot_token)

# Thread pool for async operations
executor = ThreadPoolExecutor(max_workers=settings.max_concurrent_requests)

# Global variables
bot_user_id: Optional[str] = None
health_server: Optional[HealthServer] = None


async def process_llm_request_async(
    channel_id: str, 
    user_query: str, 
    thinking_message_ts: Optional[str] = None
) -> None:
    """Process LLM request with async operations and caching"""
    try:
        # Get conversation history
        history = await get_conversation_history(
            app.client, 
            channel_id, 
            bot_user_id, 
            settings.max_history_messages
        )
        
        # Format messages for LLM
        formatted_messages = format_messages_for_llm(history, user_query)
        
        # Try RAG retrieval if enabled and not a simple greeting
        context = None
        if settings.rag_enabled and not is_simple_greeting(user_query):
            try:
                # Check cache first
                cached_context = await get_cached_rag_context(user_query)
                if cached_context:
                    context = cached_context
                    logger.debug("Using cached RAG context")
                else:
                    # Search RAG system
                    search_results = await search_rag(user_query, top_k=3, filters=None)
                    if search_results:
                        context_parts = []
                        for result in search_results:
                            title = result.title
                            content = result.content[:500]  # Limit context length
                            url = result.url
                            
                            context_parts.append(f"**{title}**\n{content}")
                            if url:
                                context_parts[-1] += f"\nSource: {url}"
                        
                        context = "\n\n---\n\n".join(context_parts)
                        
                        # Cache the context
                        await cache_rag_context(user_query, context)
                        
                        logger.info(f"Found {len(search_results)} relevant documents for query")
                    else:
                        logger.debug("No relevant documents found in knowledge base")
            except Exception as e:
                logger.warning(f"RAG search failed, proceeding without context: {e}")
        
        # Call LLM with or without context
        llm_response = await call_llm_async(formatted_messages, context)
        
        # Delete the thinking message if provided
        if thinking_message_ts:
            try:
                app.client.chat_delete(
                    channel=channel_id,
                    ts=thinking_message_ts
                )
            except SlackApiError as e:
                logger.warning(f"Could not delete thinking message: {e}")
        
        # Send the actual response
        app.client.chat_postMessage(
            channel=channel_id, 
            text=llm_response
        )
            
    except Exception as e:
        logger.error(f"Error in background LLM processing: {e}")
        
        # Delete thinking message on error too
        if thinking_message_ts:
            try:
                app.client.chat_delete(
                    channel=channel_id,
                    ts=thinking_message_ts
                )
            except SlackApiError:
                pass
        
        # Send error message
        try:
            app.client.chat_postMessage(
                channel=channel_id, 
                text="I encountered an error processing your request. Please try again."
            )
        except Exception as send_error:
            logger.error(f"Failed to send error message: {send_error}")


def process_llm_request(
    channel_id: str, 
    user_query: str, 
    thinking_message_ts: Optional[str] = None
) -> None:
    """Synchronous wrapper for async LLM processing"""
    asyncio.run(process_llm_request_async(channel_id, user_query, thinking_message_ts))


@app.event("app_mention")
def handle_app_mention_events(event, say, ack):
    """Optimized app mention handler with async processing"""
    ack()
    
    try:
        user_query = clean_message_text(event.get('text', ''))
        channel_id = event['channel']
        
        logger.info(f"Processing mention in channel {channel_id}: '{user_query[:100]}...'")
        
        # Validate query
        if not user_query or len(user_query.strip()) < 2:
            say("👋 Hi! I'm here to help with technical questions. Please ask me something specific!")
            return
        
        # Send thinking message and capture its timestamp
        thinking_response = say("🤔 Let me think about that...")
        thinking_ts = thinking_response.get('ts') if thinking_response else None
        
        # Process in background thread
        executor.submit(process_llm_request, channel_id, user_query, thinking_ts)
        
    except Exception as e:
        logger.error(f"Error in app mention handler: {e}")
        say("I encountered an error processing your request. Please try again.")


@app.event("message")
def handle_direct_messages(event, say, ack):
    """Handle direct messages to the bot"""
    ack()
    
    # Skip if it's a bot message or doesn't have text
    if event.get('bot_id') or not event.get('text'):
        return
    
    # Skip if it's not a direct message
    if event.get('channel_type') != 'im':
        return
    
    try:
        user_query = clean_message_text(event.get('text', ''))
        channel_id = event['channel']
        
        logger.info(f"Processing DM in channel {channel_id}: '{user_query[:100]}...'")
        
        # Validate query
        if not user_query or len(user_query.strip()) < 2:
            say("👋 Hi! I'm here to help with technical questions. Please ask me something specific!")
            return
        
        # Send thinking message and capture its timestamp
        thinking_response = say("🤔 Let me think about that...")
        thinking_ts = thinking_response.get('ts') if thinking_response else None
        
        # Process in background thread
        executor.submit(process_llm_request, channel_id, user_query, thinking_ts)
        
    except Exception as e:
        logger.error(f"Error in DM handler: {e}")
        say("I encountered an error processing your request. Please try again.")


def signal_handler(signum, frame):
    """Handle shutdown signals"""
    logger.info("Received shutdown signal, cleaning up...")
    
    if health_server:
        health_server.stop()
    
    executor.shutdown(wait=True)
    logger.info("Shutdown complete")
    sys.exit(0)


async def initialize_services():
    """Initialize all services asynchronously"""
    global bot_user_id, health_server
    
    try:
        # Get bot user ID
        bot_user_id = get_bot_user_id(app.client)
        if not bot_user_id:
            raise Exception("Failed to get bot user ID")
        
        # Test RAG system if enabled
        if settings.rag_enabled:
            try:
                rag_healthy = await rag_health_check()
                if not rag_healthy:
                    logger.warning("RAG system health check failed, disabling RAG")
                    settings.rag_enabled = False
                else:
                    logger.info("RAG system initialized successfully")
            except Exception as e:
                logger.warning(f"RAG system initialization failed: {e}")
                logger.warning("Proceeding without RAG functionality")
                settings.rag_enabled = False
        
        # Start health check server
        health_checker = HealthChecker()
        health_server = HealthServer(settings.health_check_port, health_checker)
        health_server.start()
        
        logger.info("🚀 All services initialized successfully!")
        
    except Exception as e:
        logger.error(f"Failed to initialize services: {e}")
        raise


if __name__ == "__main__":
    logger.info("Starting Slack bot with RAG integration...")
    
    # Register signal handlers
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    try:
        # Initialize services
        asyncio.run(initialize_services())
        
        # Start the Slack app
        handler = SocketModeHandler(app, settings.slack_app_token)
        logger.info("🚀 Slack bot started successfully with RAG integration!")
        handler.start()
        
    except KeyboardInterrupt:
        logger.info("Bot stopped by user")
    except Exception as e:
        logger.error(f"Failed to start bot: {e}")
        raise
    finally:
        if health_server:
            health_server.stop()
        executor.shutdown(wait=True)
        logger.info("Executor shutdown complete")
