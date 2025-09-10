import os
import logging

class Config:
    """Application configuration"""
    
    # Slack Configuration
    SLACK_APP_TOKEN = os.environ.get("SLACK_APP_TOKEN")
    SLACK_BOT_TOKEN = os.environ.get("SLACK_BOT_TOKEN")
    
    # LLM Configuration
    LLM_API_ENDPOINT = os.environ.get("LLM_API_ENDPOINT")
    LLM_API_KEY = os.environ.get("LLM_API_KEY")
    
    # RAG Configuration
    RAG_ENABLED = os.environ.get("RAG_ENABLED", "true").lower() == "true"
    CHROMADB_HOST = os.environ.get("CHROMADB_HOST", "chromadb-service.bot-infra.svc.cluster.local")
    CHROMADB_PORT = int(os.environ.get("CHROMADB_PORT", "8000"))
    
    # Application Configuration
    MAX_HISTORY_MESSAGES = int(os.environ.get("MAX_HISTORY_MESSAGES", "3"))
    MAX_MESSAGE_LENGTH = int(os.environ.get("MAX_MESSAGE_LENGTH", "4000"))
    LLM_TIMEOUT = int(os.environ.get("LLM_TIMEOUT", "45"))
    MAX_TOKENS = int(os.environ.get("MAX_TOKENS", "300"))
    HEALTH_CHECK_PORT = int(os.environ.get("HEALTH_CHECK_PORT", "8080"))
    
    # Logging Configuration
    LOG_LEVEL = os.environ.get("LOG_LEVEL", "INFO").upper()
    
    @classmethod
    def validate(cls):
        """Validate required configuration"""
        required = [
            cls.SLACK_APP_TOKEN,
            cls.SLACK_BOT_TOKEN, 
            cls.LLM_API_ENDPOINT
        ]
        
        missing = [name for name, value in [
            ("SLACK_APP_TOKEN", cls.SLACK_APP_TOKEN),
            ("SLACK_BOT_TOKEN", cls.SLACK_BOT_TOKEN),
            ("LLM_API_ENDPOINT", cls.LLM_API_ENDPOINT)
        ] if not value]
        
        if missing:
            raise ValueError(f"Missing required environment variables: {', '.join(missing)}")
        
        return True
