"""
Document models for IntelliMock application.
Handles OpenAPI specs, JSON samples, and Postman collections.
"""

from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional
from uuid import UUID, uuid4

from pydantic import BaseModel, Field, validator


class DocumentType(str, Enum):
    """Supported document types for ingestion."""
    OPENAPI = "openapi"
    JSON_SAMPLE = "json_sample"
    POSTMAN_COLLECTION = "postman_collection"
    YAML = "yaml"
    SWAGGER = "swagger"


class DocumentStatus(str, Enum):
    """Document processing status."""
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"


class Document(BaseModel):
    """Main document model for storing uploaded API documentation."""
    
    id: UUID = Field(default_factory=uuid4, description="Unique document identifier")
    name: str = Field(..., min_length=1, max_length=255, description="Document name")
    type: DocumentType = Field(..., description="Type of document")
    status: DocumentStatus = Field(default=DocumentStatus.PENDING, description="Processing status")
    
    # File information
    original_filename: str = Field(..., description="Original uploaded filename")
    file_size: int = Field(..., gt=0, description="File size in bytes")
    content_hash: str = Field(..., description="SHA-256 hash of file content")
    
    # Content and metadata
    content: Optional[Dict[str, Any]] = Field(None, description="Parsed document content")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Additional metadata")
    
    # Vector storage information
    vector_embeddings: Optional[List[List[float]]] = Field(None, description="Document embeddings for RAG")
    chunks: Optional[List[str]] = Field(None, description="Text chunks for vector search")
    
    # Timestamps
    created_at: datetime = Field(default_factory=datetime.utcnow, description="Creation timestamp")
    updated_at: datetime = Field(default_factory=datetime.utcnow, description="Last update timestamp")
    processed_at: Optional[datetime] = Field(None, description="Processing completion timestamp")
    
    # Error handling
    error_message: Optional[str] = Field(None, description="Error message if processing failed")
    
    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat(),
            UUID: lambda v: str(v)
        }

    @validator('content')
    def validate_content(cls, v, values):
        """Validate content based on document type."""
        if v is None:
            return v
            
        doc_type = values.get('type')
        if doc_type == DocumentType.OPENAPI:
            required_fields = ['openapi', 'info', 'paths']
            if not all(field in v for field in required_fields):
                raise ValueError(f"OpenAPI document must contain: {required_fields}")
        elif doc_type == DocumentType.POSTMAN_COLLECTION:
            if 'collection' not in v or 'item' not in v.get('collection', {}):
                raise ValueError("Postman collection must contain collection.item")
                
        return v


class DocumentUpload(BaseModel):
    """Model for document upload requests."""
    
    name: str = Field(..., min_length=1, max_length=255, description="Document name")
    type: DocumentType = Field(..., description="Document type")
    description: Optional[str] = Field(None, max_length=1000, description="Document description")
    tags: List[str] = Field(default_factory=list, description="Document tags")
    
    class Config:
        schema_extra = {
            "example": {
                "name": "User Management API",
                "type": "openapi",
                "description": "OpenAPI specification for user management endpoints",
                "tags": ["users", "authentication", "v1"]
            }
        }


class DocumentSummary(BaseModel):
    """Lightweight document summary for listings."""
    
    id: UUID
    name: str
    type: DocumentType
    status: DocumentStatus
    file_size: int
    created_at: datetime
    updated_at: datetime
    
    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat(),
            UUID: lambda v: str(v)
        }


class DocumentSearchResult(BaseModel):
    """Search result with relevance scoring."""
    
    document: DocumentSummary
    relevance_score: float = Field(..., ge=0.0, le=1.0, description="Relevance score (0-1)")
    matched_chunks: List[str] = Field(..., description="Matching text chunks")
    
    class Config:
        schema_extra = {
            "example": {
                "document": {
                    "id": "123e4567-e89b-12d3-a456-426614174000",
                    "name": "User API",
                    "type": "openapi",
                    "status": "completed",
                    "file_size": 2048,
                    "created_at": "2024-01-01T00:00:00Z",
                    "updated_at": "2024-01-01T00:00:00Z"
                },
                "relevance_score": 0.85,
                "matched_chunks": ["User authentication endpoint", "POST /auth/login"]
            }
        }
