"""
Message processing functions - Functional approach
"""
import logging
import re
from typing import List, Dict, Optional
from slack_sdk import WebClient
from slack_sdk.errors import SlackApiError

from models import SlackMessage, LLMMessage, MessageRole
from config import settings

logger = logging.getLogger(__name__)


def clean_message_text(text: str) -> str:
    """Enhanced message cleaning with early returns"""
    if not text:
        return ""
    
    # Remove bot mentions
    text = re.sub(r'<@[A-Z0-9]+>', '', text)
    
    # Clean up Slack formatting
    text = re.sub(r'<#[A-Z0-9]+\|([^>]+)>', r'#\1', text)  # Channel mentions
    text = re.sub(r'<@[A-Z0-9]+\|([^>]+)>', r'@\1', text)  # User mentions with names
    text = re.sub(r'<([^>|]+)\|([^>]+)>', r'\2', text)      # Links with text
    text = re.sub(r'<([^>]+)>', r'\1', text)                # Simple links
    
    # Remove excessive whitespace
    text = re.sub(r'\s+', ' ', text).strip()
    
    return text


async def get_conversation_history(
    client: WebClient, 
    channel_id: str, 
    bot_user_id: str,
    limit: int = None
) -> List[SlackMessage]:
    """Fetch recent messages with better error handling and filtering"""
    # Early returns for error conditions
    if not channel_id or not channel_id.strip():
        logger.warning("Channel ID cannot be empty")
        return []
    
    if not bot_user_id or not bot_user_id.strip():
        logger.warning("Bot user ID cannot be empty")
        return []
    
    limit = limit or settings.max_history_messages
    
    try:
        response = client.conversations_history(
            channel=channel_id,
            limit=limit * 3  # Get more to account for filtering
        )
        
        messages = response.get('messages', [])
        if not messages:
            logger.debug(f"No messages found in channel {channel_id}")
            return []
        
        # Filter and format messages
        filtered_messages = []
        for msg in messages:
            if not _is_valid_message(msg, bot_user_id):
                continue
                
            try:
                slack_message = SlackMessage(
                    text=msg.get('text', ''),
                    user=msg.get('user', ''),
                    channel=channel_id,
                    timestamp=msg.get('ts', ''),
                    type=msg.get('type', 'message'),
                    bot_id=msg.get('bot_id'),
                    subtype=msg.get('subtype')
                )
                filtered_messages.append(slack_message)
                
                if len(filtered_messages) >= limit:
                    break
            except Exception as e:
                logger.warning(f"Failed to create SlackMessage from raw message: {e}")
                continue
        
        # Reverse to get oldest to newest
        filtered_messages.reverse()
        logger.debug(f"Retrieved {len(filtered_messages)} valid messages from channel {channel_id}")
        return filtered_messages
        
    except SlackApiError as e:
        logger.error(f"Error fetching conversation history: {e}")
        return []
    except Exception as e:
        logger.error(f"Unexpected error fetching conversation history: {e}")
        return []


def _is_valid_message(msg: Dict, bot_user_id: str) -> bool:
    """Check if message is valid for processing"""
    if not msg:
        return False
    
    if msg.get('type') != 'message':
        return False
    
    if not msg.get('text') or not msg.get('text').strip():
        return False
    
    if msg.get('user') == bot_user_id:
        return False
    
    if msg.get('bot_id'):
        return False
    
    if msg.get('subtype'):  # Exclude message edits, deletes, etc.
        return False
    
    return True


def format_messages_for_llm(
    messages: List[SlackMessage], 
    current_query: str
) -> List[LLMMessage]:
    """Create optimized prompt with better context management"""
    # Early returns for error conditions
    if not messages and not current_query:
        logger.warning("No messages or query provided")
        return []
    
    formatted_messages = []
    
    # Add system message for technical context
    system_prompt = LLMMessage(
        role=MessageRole.SYSTEM,
        content=(
            "You are a helpful technical assistant in a Slack workspace. "
            "Provide concise, accurate answers focused on the specific question. "
            "If you don't know something, say so clearly. "
            "Keep responses under 2000 characters when possible. "
            "Format code with backticks for readability. "
            "For simple greetings like 'hi' or 'hello', respond with a friendly greeting and ask how you can help."
        )
    )
    formatted_messages.append(system_prompt)
    
    # Add conversation history (limited and cleaned)
    total_chars = len(system_prompt.content)
    
    for msg in messages:
        cleaned_text = clean_message_text(msg.text)
        
        if not cleaned_text:
            continue
            
        # Limit individual message length
        if len(cleaned_text) > 500:
            cleaned_text = cleaned_text[:497] + "..."
        
        # Check total length to avoid token limits
        if total_chars + len(cleaned_text) > 2000:
            break
            
        formatted_messages.append(LLMMessage(
            role=MessageRole.USER,
            content=cleaned_text
        ))
        total_chars += len(cleaned_text)
    
    # Add current query
    if current_query:
        current_query_cleaned = clean_message_text(current_query)
        if current_query_cleaned:
            formatted_messages.append(LLMMessage(
                role=MessageRole.USER,
                content=current_query_cleaned
            ))
    
    logger.debug(f"Formatted {len(formatted_messages)} messages for LLM")
    return formatted_messages


def is_simple_greeting(query: str) -> bool:
    """Check if the query is a simple greeting that doesn't need RAG context"""
    if not query or not query.strip():
        return False
    
    simple_greetings = [
        'hi', 'hello', 'hey', 'good morning', 'good afternoon', 'good evening',
        'how are you', 'whats up', "what's up", 'sup', 'yo', 'greetings'
    ]
    
    query_lower = query.lower().strip()
    return any(greeting in query_lower for greeting in simple_greetings) and len(query_lower) < 50


def get_bot_user_id(client: WebClient) -> Optional[str]:
    """Get bot user ID with error handling"""
    try:
        response = client.auth_test()
        bot_user_id = response.get("user_id")
        if not bot_user_id:
            logger.error("Bot user ID not found in auth response")
            return None
        
        logger.info(f"Bot User ID: {bot_user_id}")
        return bot_user_id
        
    except SlackApiError as e:
        logger.error(f"Error getting bot user ID: {e}")
        return None
    except Exception as e:
        logger.error(f"Unexpected error getting bot user ID: {e}")
        return None
