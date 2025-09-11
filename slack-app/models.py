"""
Pydantic models for data validation and type safety
"""
from pydantic import BaseModel, Field, validator
from typing import List, Dict, Optional, Union, Any
from datetime import datetime
from enum import Enum


class MessageRole(str, Enum):
    """Message roles for LLM conversations"""
    SYSTEM = "system"
    USER = "user"
    ASSISTANT = "assistant"


class SlackMessage(BaseModel):
    """Slack message model"""
    text: str
    user: str
    channel: str
    timestamp: str
    type: str = "message"
    bot_id: Optional[str] = None
    subtype: Optional[str] = None

    @validator('text')
    def text_must_not_be_empty(cls, v):
        if not v or not v.strip():
            raise ValueError('Message text cannot be empty')
        return v.strip()


class LLMMessage(BaseModel):
    """LLM conversation message model"""
    role: MessageRole
    content: str

    @validator('content')
    def content_must_not_be_empty(cls, v):
        if not v or not v.strip():
            raise ValueError('Message content cannot be empty')
        return v.strip()


class RAGSearchResult(BaseModel):
    """RAG search result model"""
    content: str
    title: str
    url: str
    score: float
    metadata: Dict[str, Any]
    type: str = "unknown"

    @validator('score')
    def score_must_be_valid(cls, v):
        if not 0 <= v <= 1:
            raise ValueError('Score must be between 0 and 1')
        return v


class ConfluencePage(BaseModel):
    """Confluence page model"""
    id: str
    title: str
    content: str
    space_key: str
    url: str
    created_date: Optional[datetime] = None
    modified_date: Optional[datetime] = None
    version: Optional[int] = None

    @validator('id')
    def id_must_not_be_empty(cls, v):
        if not v or not v.strip():
            raise ValueError('Page ID cannot be empty')
        return v.strip()


class JiraIssue(BaseModel):
    """Jira issue model"""
    key: str
    summary: str
    description: str
    project_key: str
    issue_type: str
    status: str
    resolution: Optional[str] = None
    url: str
    created: Optional[datetime] = None
    resolved: Optional[datetime] = None

    @validator('key')
    def key_must_not_be_empty(cls, v):
        if not v or not v.strip():
            raise ValueError('Issue key cannot be empty')
        return v.strip()


class ZohoDeskTicket(BaseModel):
    """Zoho Desk ticket model"""
    id: str
    subject: str
    description: str
    status: str
    department: Optional[str] = None
    url: str
    created: Optional[datetime] = None
    modified: Optional[datetime] = None

    @validator('id')
    def id_must_not_be_empty(cls, v):
        if not v or not v.strip():
            raise ValueError('Ticket ID cannot be empty')
        return v.strip()


class DocumentChunk(BaseModel):
    """Document chunk for vector storage"""
    id: str
    content: str
    metadata: Dict[str, Any]
    chunk_index: int
    total_chunks: int

    @validator('content')
    def content_must_not_be_empty(cls, v):
        if not v or not v.strip():
            raise ValueError('Chunk content cannot be empty')
        return v.strip()


class HealthStatus(BaseModel):
    """Health check status model"""
    status: str
    timestamp: str
    components: Dict[str, Any]

    @validator('status')
    def status_must_be_valid(cls, v):
        valid_statuses = ['healthy', 'unhealthy', 'degraded']
        if v not in valid_statuses:
            raise ValueError(f'Status must be one of: {valid_statuses}')
        return v


class ReadinessStatus(BaseModel):
    """Readiness check status model"""
    ready: bool
    timestamp: str
    components: Dict[str, bool]


class SyncResult(BaseModel):
    """Data synchronization result model"""
    start_time: float
    confluence_count: int = 0
    jira_count: int = 0
    zoho_desk_count: int = 0
    total_count: int = 0
    success: bool
    errors: List[str] = []
    duration: Optional[float] = None

    @validator('total_count')
    def total_count_matches_sum(cls, v, values):
        confluence = values.get('confluence_count', 0)
        jira = values.get('jira_count', 0)
        zoho_desk = values.get('zoho_desk_count', 0)
        expected_total = confluence + jira + zoho_desk
        if v != expected_total:
            raise ValueError(f'Total count {v} does not match sum of individual counts {expected_total}')
        return v


class EmbeddingCacheEntry(BaseModel):
    """Embedding cache entry model"""
    text: str
    embedding: List[float]
    created_at: datetime
    expires_at: datetime

    @validator('embedding')
    def embedding_must_not_be_empty(cls, v):
        if not v or len(v) == 0:
            raise ValueError('Embedding cannot be empty')
        return v


class LLMCacheEntry(BaseModel):
    """LLM response cache entry model"""
    query_hash: str
    response: str
    created_at: datetime
    expires_at: datetime

    @validator('query_hash')
    def query_hash_must_not_be_empty(cls, v):
        if not v or not v.strip():
            raise ValueError('Query hash cannot be empty')
        return v.strip()
