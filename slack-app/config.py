"""
Application configuration using Pydantic BaseSettings
"""
import logging
from pydantic import Field, validator
from pydantic_settings import BaseSettings
from typing import Optional, List
from enum import Enum


class LogLevel(str, Enum):
    """Logging levels"""
    DEBUG = "DEBUG"
    INFO = "INFO"
    WARNING = "WARNING"
    ERROR = "ERROR"
    CRITICAL = "CRITICAL"


class Settings(BaseSettings):
    """Application configuration with validation"""
    
    # Slack Configuration
    slack_app_token: str = Field(..., description="Slack app token", env="SLACK_APP_TOKEN")
    slack_bot_token: str = Field(..., description="Slack bot token", env="SLACK_BOT_TOKEN")
    
    # LLM Configuration
    llm_api_endpoint: str = Field(..., description="LLM API endpoint", env="LLM_API_ENDPOINT")
    llm_api_key: Optional[str] = Field(None, description="LLM API key", env="LLM_API_KEY")
    
    # RAG Configuration
    rag_enabled: bool = Field(True, description="Enable RAG functionality", env="RAG_ENABLED")
    chromadb_host: str = Field("chromadb-service.bot-infra.svc.cluster.local", description="ChromaDB host", env="CHROMADB_HOST")
    chromadb_port: int = Field(8000, ge=1, le=65535, description="ChromaDB port", env="CHROMADB_PORT")
    embedding_model: str = Field("all-MiniLM-L6-v2", description="Embedding model name", env="EMBEDDING_MODEL")
    
    # Application Configuration
    max_history_messages: int = Field(3, ge=1, le=10, description="Maximum conversation history messages", env="MAX_HISTORY_MESSAGES")
    max_message_length: int = Field(4000, ge=100, le=10000, description="Maximum message length", env="MAX_MESSAGE_LENGTH")
    llm_timeout: int = Field(45, ge=5, le=300, description="LLM request timeout in seconds", env="LLM_TIMEOUT")
    max_tokens: int = Field(300, ge=50, le=2000, description="Maximum tokens for LLM response", env="MAX_TOKENS")
    health_check_port: int = Field(8080, ge=1024, le=65535, description="Health check server port", env="HEALTH_CHECK_PORT")
    
    # Caching Configuration
    redis_enabled: bool = Field(False, description="Enable Redis caching", env="REDIS_ENABLED")
    redis_host: str = Field("localhost", description="Redis host", env="REDIS_HOST")
    redis_port: int = Field(6379, ge=1, le=65535, description="Redis port", env="REDIS_PORT")
    redis_password: Optional[str] = Field(None, description="Redis password", env="REDIS_PASSWORD")
    redis_db: int = Field(0, ge=0, le=15, description="Redis database number", env="REDIS_DB")
    cache_ttl_embeddings: int = Field(3600, ge=60, le=86400, description="Embedding cache TTL in seconds", env="CACHE_TTL_EMBEDDINGS")
    cache_ttl_responses: int = Field(1800, ge=60, le=86400, description="Response cache TTL in seconds", env="CACHE_TTL_RESPONSES")
    
    # Performance Configuration
    max_concurrent_requests: int = Field(10, ge=1, le=100, description="Maximum concurrent requests", env="MAX_CONCURRENT_REQUESTS")
    batch_size_embeddings: int = Field(32, ge=1, le=128, description="Batch size for embedding generation", env="BATCH_SIZE_EMBEDDINGS")
    
    # Logging Configuration
    log_level: LogLevel = Field(LogLevel.INFO, description="Logging level", env="LOG_LEVEL")
    
    @validator('llm_api_endpoint')
    def validate_llm_endpoint(cls, v):
        if not v.startswith(('http://', 'https://')):
            raise ValueError('LLM endpoint must be a valid URL')
        return v
    
    @validator('chromadb_host')
    def validate_chromadb_host(cls, v):
        if not v or not v.strip():
            raise ValueError('ChromaDB host cannot be empty')
        return v.strip()
    
    @validator('embedding_model')
    def validate_embedding_model(cls, v):
        if not v or not v.strip():
            raise ValueError('Embedding model cannot be empty')
        return v.strip()
    
    class Config:
        env_file = ".env"
        case_sensitive = False
        env_prefix = ""


# Global settings instance
settings = Settings()

# Backward compatibility - create a Config class that mimics the old interface
class Config:
    """Backward compatibility wrapper for old Config class"""
    
    # Slack Configuration
    SLACK_APP_TOKEN = settings.slack_app_token
    SLACK_BOT_TOKEN = settings.slack_bot_token
    
    # LLM Configuration
    LLM_API_ENDPOINT = settings.llm_api_endpoint
    LLM_API_KEY = settings.llm_api_key
    
    # RAG Configuration
    RAG_ENABLED = settings.rag_enabled
    CHROMADB_HOST = settings.chromadb_host
    CHROMADB_PORT = settings.chromadb_port
    EMBEDDING_MODEL = settings.embedding_model
    
    # Application Configuration
    MAX_HISTORY_MESSAGES = settings.max_history_messages
    MAX_MESSAGE_LENGTH = settings.max_message_length
    LLM_TIMEOUT = settings.llm_timeout
    MAX_TOKENS = settings.max_tokens
    HEALTH_CHECK_PORT = settings.health_check_port
    
    # Caching Configuration
    REDIS_ENABLED = settings.redis_enabled
    REDIS_HOST = settings.redis_host
    REDIS_PORT = settings.redis_port
    REDIS_PASSWORD = settings.redis_password
    REDIS_DB = settings.redis_db
    CACHE_TTL_EMBEDDINGS = settings.cache_ttl_embeddings
    CACHE_TTL_RESPONSES = settings.cache_ttl_responses
    
    # Performance Configuration
    MAX_CONCURRENT_REQUESTS = settings.max_concurrent_requests
    BATCH_SIZE_EMBEDDINGS = settings.batch_size_embeddings
    
    # Logging Configuration
    LOG_LEVEL = settings.log_level.value
    
    @classmethod
    def validate(cls):
        """Validate required configuration - now handled by Pydantic"""
        return True
