"""
Mock request and response models for API simulation.
"""

from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional
from uuid import UUID, uuid4

from pydantic import BaseModel, Field, validator


class HTTPMethod(str, Enum):
    """Supported HTTP methods."""
    GET = "GET"
    POST = "POST"
    PUT = "PUT"
    PATCH = "PATCH"
    DELETE = "DELETE"
    HEAD = "HEAD"
    OPTIONS = "OPTIONS"


class RequestStatus(str, Enum):
    """Mock request processing status."""
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"


class MockRequest(BaseModel):
    """Model for incoming API mock requests."""
    
    id: UUID = Field(default_factory=uuid4, description="Unique request identifier")
    
    # HTTP request details
    method: HTTPMethod = Field(..., description="HTTP method")
    path: str = Field(..., min_length=1, description="API endpoint path")
    headers: Dict[str, str] = Field(default_factory=dict, description="Request headers")
    query_params: Dict[str, Any] = Field(default_factory=dict, description="Query parameters")
    body: Optional[Dict[str, Any]] = Field(None, description="Request body")
    
    # Context and configuration
    document_ids: List[UUID] = Field(..., description="Documents to use for context")
    llm_provider: str = Field(..., description="LLM provider to use")
    llm_config: Dict[str, Any] = Field(default_factory=dict, description="LLM configuration")
    
    # Processing information
    status: RequestStatus = Field(default=RequestStatus.PENDING, description="Processing status")
    created_at: datetime = Field(default_factory=datetime.utcnow, description="Creation timestamp")
    processed_at: Optional[datetime] = Field(None, description="Processing completion timestamp")
    
    # User context
    user_id: Optional[str] = Field(None, description="User identifier")
    session_id: Optional[str] = Field(None, description="Session identifier")
    
    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat(),
            UUID: lambda v: str(v)
        }
        schema_extra = {
            "example": {
                "method": "POST",
                "path": "/api/users",
                "headers": {
                    "Content-Type": "application/json",
                    "Authorization": "Bearer token123"
                },
                "body": {
                    "name": "John Doe",
                    "email": "john@example.com"
                },
                "document_ids": ["123e4567-e89b-12d3-a456-426614174000"],
                "llm_provider": "gemini",
                "llm_config": {
                    "temperature": 0.7,
                    "max_tokens": 1000
                }
            }
        }

    @validator('path')
    def validate_path(cls, v):
        """Ensure path starts with /."""
        if not v.startswith('/'):
            return f"/{v}"
        return v

    @validator('headers')
    def normalize_headers(cls, v):
        """Normalize header names to lowercase."""
        return {k.lower(): str(val) for k, val in v.items()}


class MockResponse(BaseModel):
    """Model for generated API responses."""
    
    request_id: UUID = Field(..., description="Associated request ID")
    
    # HTTP response details
    status_code: int = Field(..., ge=100, le=599, description="HTTP status code")
    headers: Dict[str, str] = Field(default_factory=dict, description="Response headers")
    body: Optional[Dict[str, Any]] = Field(None, description="Response body")
    
    # Generation metadata
    llm_provider: str = Field(..., description="LLM provider used")
    generation_time_ms: int = Field(..., ge=0, description="Generation time in milliseconds")
    context_documents: List[UUID] = Field(..., description="Documents used for context")
    
    # Quality metrics
    confidence_score: float = Field(..., ge=0.0, le=1.0, description="Response confidence (0-1)")
    context_relevance: float = Field(..., ge=0.0, le=1.0, description="Context relevance (0-1)")
    
    # RAG information
    retrieved_chunks: List[str] = Field(..., description="Retrieved context chunks")
    embedding_similarity: List[float] = Field(..., description="Similarity scores for chunks")
    
    # Timestamps
    generated_at: datetime = Field(default_factory=datetime.utcnow, description="Generation timestamp")
    
    # Error handling
    error_message: Optional[str] = Field(None, description="Error message if generation failed")
    
    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat(),
            UUID: lambda v: str(v)
        }
        schema_extra = {
            "example": {
                "request_id": "123e4567-e89b-12d3-a456-426614174000",
                "status_code": 201,
                "headers": {
                    "content-type": "application/json",
                    "location": "/api/users/12345"
                },
                "body": {
                    "id": 12345,
                    "name": "John Doe",
                    "email": "john@example.com",
                    "created_at": "2024-01-01T00:00:00Z"
                },
                "llm_provider": "gemini",
                "generation_time_ms": 1500,
                "confidence_score": 0.85,
                "context_relevance": 0.92,
                "retrieved_chunks": ["User creation endpoint", "POST /api/users schema"]
            }
        }


class MockRequestBatch(BaseModel):
    """Model for batch mock request processing."""
    
    id: UUID = Field(default_factory=uuid4, description="Batch identifier")
    requests: List[MockRequest] = Field(..., min_items=1, max_items=100, description="Batch requests")
    
    # Batch configuration
    parallel_processing: bool = Field(default=True, description="Process requests in parallel")
    stop_on_error: bool = Field(default=False, description="Stop batch on first error")
    
    # Status tracking
    status: RequestStatus = Field(default=RequestStatus.PENDING, description="Batch status")
    completed_count: int = Field(default=0, ge=0, description="Number of completed requests")
    failed_count: int = Field(default=0, ge=0, description="Number of failed requests")
    
    # Timestamps
    created_at: datetime = Field(default_factory=datetime.utcnow, description="Creation timestamp")
    started_at: Optional[datetime] = Field(None, description="Processing start timestamp")
    completed_at: Optional[datetime] = Field(None, description="Completion timestamp")
    
    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat(),
            UUID: lambda v: str(v)
        }

    @validator('requests')
    def validate_batch_size(cls, v):
        """Validate batch size limits."""
        if len(v) > 100:
            raise ValueError("Batch size cannot exceed 100 requests")
        return v
