"""
LLM provider models and configuration.
"""

from datetime import datetime
from enum import Enum
from typing import List, Optional
from uuid import UUID, uuid4

from pydantic import BaseModel, Field, validator


class LLMProvider(str, Enum):
    """Supported LLM providers."""
    GEMINI = "gemini"
    OPENAI = "openai"
    ANTHROPIC = "anthropic"
    MOCK = "mock"  # For testing purposes


class LLMRequest(BaseModel):
    """LLM request model."""
    
    id: UUID = Field(default_factory=uuid4, description="Request identifier")
    
    # Provider configuration
    provider: LLMProvider = Field(..., description="LLM provider")
    model: str = Field(..., description="Model name")
    api_key: Optional[str] = Field(None, description="API key (not stored)")
    
    # Request content
    prompt: str = Field(..., min_length=1, description="Input prompt")
    context: List[str] = Field(default_factory=list, description="Context documents")
    system_message: Optional[str] = Field(None, description="System message")
    
    # Generation parameters
    temperature: float = Field(default=0.7, ge=0.0, le=2.0, description="Sampling temperature")
    max_tokens: int = Field(default=1000, ge=1, le=4000, description="Maximum tokens to generate")
    top_p: float = Field(default=1.0, ge=0.0, le=1.0, description="Top-p sampling")
    frequency_penalty: float = Field(default=0.0, ge=-2.0, le=2.0, description="Frequency penalty")
    presence_penalty: float = Field(default=0.0, ge=-2.0, le=2.0, description="Presence penalty")
    
    # Metadata
    user_id: Optional[str] = Field(None, description="User identifier")
    session_id: Optional[str] = Field(None, description="Session identifier")
    created_at: datetime = Field(default_factory=datetime.utcnow, description="Creation timestamp")
    
    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat(),
            UUID: lambda v: str(v)
        }
        schema_extra = {
            "example": {
                "provider": "gemini",
                "model": "gemini-pro",
                "prompt": "Generate a JSON response for creating a user",
                "context": ["User API documentation", "Schema definitions"],
                "temperature": 0.7,
                "max_tokens": 1000
            }
        }

    @validator('api_key')
    def mask_api_key(cls, v):
        """Mask API key for logging/storage."""
        if v and len(v) > 8:
            return f"{v[:4]}...{v[-4:]}"
        return v


class LLMResponse(BaseModel):
    """LLM response model."""
    
    request_id: UUID = Field(..., description="Associated request ID")
    
    # Response content
    content: str = Field(..., description="Generated content")
    finish_reason: str = Field(..., description="Completion reason")
    
    # Usage statistics
    prompt_tokens: int = Field(..., ge=0, description="Tokens used in prompt")
    completion_tokens: int = Field(..., ge=0, description="Tokens generated")
    total_tokens: int = Field(..., ge=0, description="Total tokens used")
    
    # Performance metrics
    response_time_ms: int = Field(..., ge=0, description="Response time in milliseconds")
    provider: LLMProvider = Field(..., description="Provider used")
    model: str = Field(..., description="Model used")
    
    # Quality metrics
    confidence_score: Optional[float] = Field(None, ge=0.0, le=1.0, description="Response confidence")
    
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
                "content": '{"id": 123, "name": "John Doe", "email": "john@example.com"}',
                "finish_reason": "stop",
                "prompt_tokens": 150,
                "completion_tokens": 50,
                "total_tokens": 200,
                "response_time_ms": 1200,
                "provider": "gemini",
                "model": "gemini-pro",
                "confidence_score": 0.95
            }
        }

    @validator('total_tokens')
    def validate_token_sum(cls, v, values):
        """Ensure total tokens equals prompt + completion tokens."""
        prompt_tokens = values.get('prompt_tokens', 0)
        completion_tokens = values.get('completion_tokens', 0)
        expected_total = prompt_tokens + completion_tokens
        
        if v != expected_total:
            return expected_total  # Auto-correct the total
        return v


class LLMConfig(BaseModel):
    """LLM provider configuration."""
    
    provider: LLMProvider = Field(..., description="Provider name")
    model: str = Field(..., description="Default model")
    api_endpoint: Optional[str] = Field(None, description="Custom API endpoint")
    
    # Default parameters
    default_temperature: float = Field(default=0.7, ge=0.0, le=2.0)
    default_max_tokens: int = Field(default=1000, ge=1, le=4000)
    default_top_p: float = Field(default=1.0, ge=0.0, le=1.0)
    
    # Rate limiting
    rate_limit_requests_per_minute: int = Field(default=60, ge=1)
    rate_limit_tokens_per_minute: int = Field(default=50000, ge=1)
    
    # Retry configuration
    max_retries: int = Field(default=3, ge=0, le=10)
    retry_delay_seconds: float = Field(default=1.0, ge=0.1, le=60.0)
    
    # Validation
    enabled: bool = Field(default=True, description="Whether provider is enabled")
    
    class Config:
        schema_extra = {
            "example": {
                "provider": "gemini",
                "model": "gemini-pro",
                "default_temperature": 0.7,
                "default_max_tokens": 1000,
                "rate_limit_requests_per_minute": 60,
                "enabled": True
            }
        }
