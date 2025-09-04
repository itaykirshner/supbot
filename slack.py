import logging
import os
import re
import json
import requests
import time
import threading
from concurrent.futures import ThreadPoolExecutor
from typing import List, Dict, Optional

from slack_sdk import WebClient
from slack_sdk.errors import SlackApiError
from slack_bolt import App
from slack_bolt.adapter.socket_mode import SocketModeHandler

# Enhanced logging configuration
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Environment variables
SLACK_APP_TOKEN = os.environ.get("SLACK_APP_TOKEN")
SLACK_BOT_TOKEN = os.environ.get("SLACK_BOT_TOKEN")
LLM_API_ENDPOINT = os.environ.get("LLM_API_ENDPOINT")
LLM_API_KEY = os.environ.get("LLM_API_KEY")

# Configuration constants
MAX_HISTORY_MESSAGES = 3
MAX_MESSAGE_LENGTH = 4000
LLM_TIMEOUT = 45
MAX_TOKENS = 300

# Validation
if not all([SLACK_APP_TOKEN, SLACK_BOT_TOKEN, LLM_API_ENDPOINT]):
    logger.error("Missing required environment variables: SLACK_APP_TOKEN, SLACK_BOT_TOKEN, LLM_API_ENDPOINT")
    exit(1)

# Initialize app
app = App(token=SLACK_BOT_TOKEN)

# Thread pool for async operations
executor = ThreadPoolExecutor(max_workers=10)

class MessageProcessor:
    """Handles message processing and context management"""

    def __init__(self, client: WebClient):
        self.client = client
        self.bot_user_id = None
        self._get_bot_user_id()

    def _get_bot_user_id(self):
        """Cache bot user ID to avoid repeated API calls"""
        try:
            response = self.client.auth_test()
            self.bot_user_id = response["user_id"]
            logger.info(f"Bot User ID: {self.bot_user_id}")
        except SlackApiError as e:
            logger.error(f"Error getting bot user ID: {e}")
            raise

    def get_conversation_history(self, channel_id: str, limit: int = MAX_HISTORY_MESSAGES) -> List[Dict]:
        """Fetch recent messages with better error handling and filtering"""
        try:
            response = self.client.conversations_history(
                channel=channel_id,
                limit=limit * 3  # Get more to account for filtering
            )

            messages = response.get('messages', [])

            # Filter out bot messages, system messages, and empty messages
            filtered_messages = []
            for msg in messages:
                if (msg.get('type') == 'message' and
                    'text' in msg and
                    msg.get('user') != self.bot_user_id and
                    not msg.get('bot_id') and
                    msg.get('text', '').strip() and
                    not msg.get('subtype')):  # Exclude message edits, deletes, etc.
                    filtered_messages.append(msg)

                if len(filtered_messages) >= limit:
                    break

            filtered_messages.reverse()  # Oldest to newest
            return filtered_messages

        except SlackApiError as e:
            logger.error(f"Error fetching conversation history: {e}")
            return []

    def clean_message_text(self, text: str) -> str:
        """Enhanced message cleaning"""
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

    def format_messages_for_llm(self, messages: List[Dict], current_query: str) -> List[Dict]:
        """Create optimized prompt with better context management"""
        formatted_messages = []

        # Add system message for technical context
        system_prompt = {
            "role": "system",
            "content": ("You are a helpful technical assistant in a Slack workspace. "
                       "Provide concise, accurate answers focused on the specific question. "
                       "If you don't know something, say so clearly. "
                       "Keep responses under 2000 characters when possible. "
                       "Format code with backticks for readability.")
        }
        formatted_messages.append(system_prompt)

        # Add conversation history (limited and cleaned)
        total_chars = len(system_prompt["content"])

        for msg in messages:
            cleaned_text = self.clean_message_text(msg.get('text', ''))

            if not cleaned_text:
                continue

            # Limit individual message length
            if len(cleaned_text) > 500:
                cleaned_text = cleaned_text[:497] + "..."

            # Check total length to avoid token limits
            if total_chars + len(cleaned_text) > 2000:
                break

            formatted_messages.append({
                "role": "user",
                "content": cleaned_text
            })
            total_chars += len(cleaned_text)

        # Add current query
        current_query = self.clean_message_text(current_query)
        if current_query:
            formatted_messages.append({
                "role": "user",
                "content": current_query
            })

        return formatted_messages

class LLMService:
    """Handles LLM API interactions with optimizations"""

    def __init__(self, endpoint: str, api_key: Optional[str] = None):
        self.endpoint = endpoint
        self.api_key = api_key
        self.session = requests.Session()

    def call_llm(self, messages: List[Dict]) -> str:
        """Optimized LLM call with better error handling"""
        payload = {
            "messages": messages,
            "temperature": 0.3,
            "max_tokens": MAX_TOKENS,
            "top_p": 0.9,
            "stream": False
        }

        headers = {
            "Content-Type": "application/json",
            "User-Agent": "SlackBot/1.0"
        }

        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"

        try:
            logger.info(f"Sending LLM request with {len(messages)} messages")

            response = self.session.post(
                self.endpoint,
                headers=headers,
                json=payload,
                timeout=LLM_TIMEOUT
            )

            response.raise_for_status()
            result = response.json()

            if (result and 'choices' in result and
                result['choices'] and
                'message' in result['choices'][0] and
                'content' in result['choices'][0]['message']):

                content = result['choices'][0]['message']['content'].strip()

                # Truncate if too long for Slack
                if len(content) > MAX_MESSAGE_LENGTH:
                    content = content[:MAX_MESSAGE_LENGTH-50] + "... [truncated]"

                return content
            else:
                logger.error(f"Unexpected LLM response format: {result}")
                return "I received an unexpected response format. Please try again."

        except requests.exceptions.Timeout:
            logger.error("LLM request timed out")
            return "The request took too long to process. Please try a simpler question."

        except requests.exceptions.RequestException as e:
            logger.error(f"LLM request failed: {e}")
            return "I'm having trouble connecting to my knowledge base. Please try again later."

        except Exception as e:
            logger.error(f"Unexpected error in LLM call: {e}")
            return "An unexpected error occurred. Please try again."

def process_llm_request(channel_id: str, user_query: str, thinking_message_ts: str = None):
    """Process LLM request in background thread with message cleanup"""
    try:
        # Get conversation history
        history = message_processor.get_conversation_history(channel_id)

        # Format messages for LLM
        formatted_messages = message_processor.format_messages_for_llm(history, user_query)

        # Call LLM
        llm_response = llm_service.call_llm(formatted_messages)

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

@app.event("app_mention")
def handle_app_mention_events(event, say, ack):
    """Optimized app mention handler with async processing"""
    ack()

    try:
        user_query = message_processor.clean_message_text(event.get('text', ''))
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
        try:
            say("Sorry, I encountered an error. Please try again.")
        except:
            pass

@app.event("message")
def handle_direct_messages(event, say, ack):
    """Handle direct messages to the bot"""
    # Only respond to DMs, not channel messages
    if event.get('channel_type') != 'im':
        return

    # Don't respond to bot messages or messages without user
    if (event.get('bot_id') or
        event.get('user') == message_processor.bot_user_id or
        not event.get('user')):
        return

    ack()

    user_query = message_processor.clean_message_text(event.get('text', ''))

    if not user_query or len(user_query.strip()) < 2:
        return

    channel_id = event['channel']

    logger.info(f"Processing DM: '{user_query[:100]}...'")

    # Send thinking message
    thinking_response = say("🤔 Processing your question...")
    thinking_ts = thinking_response.get('ts') if thinking_response else None

    # Process in background
    executor.submit(process_llm_request, channel_id, user_query, thinking_ts)

@app.error
def handle_errors(error):
    """Global error handler"""
    logger.error(f"Slack app error: {error}")

def health_check():
    """Health check function for monitoring"""
    return {
        "status": "healthy",
        "bot_id": getattr(message_processor, 'bot_user_id', None),
        "llm_endpoint": LLM_API_ENDPOINT
    }

# Initialize services globally
message_processor = None
llm_service = None

if __name__ == "__main__":
    logger.info("Starting Slack bot...")

    try:
        # Initialize services
        message_processor = MessageProcessor(app.client)
        llm_service = LLMService(LLM_API_ENDPOINT, LLM_API_KEY)

        # Test health check
        health = health_check()
        logger.info(f"Health check: {health}")

        # Start the app
        handler = SocketModeHandler(app, SLACK_APP_TOKEN)
        logger.info("Bot started successfully!")
        handler.start()

    except KeyboardInterrupt:
        logger.info("Bot stopped by user")
    except Exception as e:
        logger.error(f"Failed to start bot: {e}")
        raise
    finally:
        executor.shutdown(wait=True)
        logger.info("Executor shutdown complete")