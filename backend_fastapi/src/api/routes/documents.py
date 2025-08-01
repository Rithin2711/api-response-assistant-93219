"""
Document management API endpoints.
Handles document upload, processing, and retrieval.
"""

import logging
from typing import List, Optional
from uuid import UUID

from fastapi import APIRouter, File, Form, HTTPException, UploadFile, status
from fastapi.responses import Response

from models.document import Document, DocumentSummary, DocumentType, DocumentUpload
from services.document_service import DocumentService

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/documents", tags=["Documents"])
document_service = DocumentService()


@router.post("/upload", 
             response_model=Document,
             status_code=status.HTTP_201_CREATED,
             summary="Upload API documentation",
             description="Upload OpenAPI specs, JSON samples, Postman collections, or YAML files for processing")
async def upload_document(
    file: UploadFile = File(..., description="Document file to upload"),
    name: str = Form(..., description="Document name"),
    type: DocumentType = Form(..., description="Document type"),
    description: Optional[str] = Form(None, description="Document description"),
    tags: Optional[str] = Form(None, description="Comma-separated tags")
):
    """
    Upload and process API documentation.
    
    Accepts various document formats:
    - OpenAPI 3.x specifications (JSON/YAML)
    - Swagger 2.x specifications  
    - JSON sample responses
    - Postman collections
    - Generic YAML files
    
    The document will be processed asynchronously and indexed for search.
    """
    try:
        # Validate file size (10MB limit)
        if file.size and file.size > 10 * 1024 * 1024:
            raise HTTPException(
                status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                detail="File size exceeds 10MB limit"
            )
        
        # Read file content
        content = await file.read()
        if not content:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Empty file uploaded"
            )
        
        # Parse tags
        tag_list = []
        if tags:
            tag_list = [tag.strip() for tag in tags.split(",") if tag.strip()]
        
        # Create upload data
        upload_data = DocumentUpload(
            name=name,
            type=type,
            description=description,
            tags=tag_list
        )
        
        # Upload document
        document = document_service.upload_document(
            upload_data, content, file.filename or "unknown"
        )
        
        logger.info(f"Document uploaded: {document.id}")
        return document
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Document upload failed: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Upload failed: {str(e)}"
        )


@router.get("/", 
            response_model=List[DocumentSummary],
            summary="List documents",
            description="Get list of uploaded documents with optional filtering")
async def list_documents(
    type: Optional[DocumentType] = None,
    status: Optional[str] = None
):
    """
    List all uploaded documents with optional filtering.
    
    Filter by document type or processing status.
    """
    try:
        documents = document_service.list_documents(doc_type=type)
        
        # Convert to summary format
        summaries = []
        for doc in documents:
            summary = DocumentSummary(
                id=doc.id,
                name=doc.name,
                type=doc.type,
                status=doc.status,
                file_size=doc.file_size,
                created_at=doc.created_at,
                updated_at=doc.updated_at
            )
            summaries.append(summary)
        
        return summaries
        
    except Exception as e:
        logger.error(f"Failed to list documents: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to list documents: {str(e)}"
        )


@router.get("/{document_id}",
            response_model=Document,
            summary="Get document details",
            description="Retrieve detailed information about a specific document")
async def get_document(document_id: UUID):
    """
    Get detailed information about a specific document.
    
    Returns full document metadata including processing status and extracted content.
    """
    document = document_service.get_document(document_id)
    if not document:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Document not found"
        )
    
    return document


@router.get("/{document_id}/content",
            summary="Download document content",
            description="Download the original document file content")
async def get_document_content(document_id: UUID):
    """
    Download the original document file content.
    
    Returns the binary content of the uploaded file.
    """
    document = document_service.get_document(document_id)
    if not document:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Document not found"
        )
    
    content = document_service.get_document_content(document_id)
    if not content:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Document content not found"
        )
    
    # Determine content type
    content_type = document.metadata.get("mime_type", "application/octet-stream")
    
    return Response(
        content=content,
        media_type=content_type,
        headers={
            "Content-Disposition": f"attachment; filename={document.original_filename}"
        }
    )


@router.delete("/{document_id}",
               status_code=status.HTTP_204_NO_CONTENT,
               summary="Delete document",
               description="Delete a document and its associated content")
async def delete_document(document_id: UUID):
    """
    Delete a document and its associated content.
    
    This will permanently remove the document and its indexed content.
    """
    success = document_service.delete_document(document_id)
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Document not found"
        )
    
    logger.info(f"Document deleted: {document_id}")


@router.get("/search/",
            response_model=List[DocumentSummary],
            summary="Search documents",
            description="Search documents by text query")
async def search_documents(q: str):
    """
    Search documents by text query.
    
    Searches document names, descriptions, and indexed content.
    """
    if not q or len(q.strip()) < 2:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Search query must be at least 2 characters"
        )
    
    try:
        documents = document_service.search_documents(q.strip())
        
        # Convert to summary format
        summaries = []
        for doc in documents:
            summary = DocumentSummary(
                id=doc.id,
                name=doc.name,
                type=doc.type,
                status=doc.status,
                file_size=doc.file_size,
                created_at=doc.created_at,
                updated_at=doc.updated_at
            )
            summaries.append(summary)
        
        return summaries
        
    except Exception as e:
        logger.error(f"Document search failed: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Search failed: {str(e)}"
        )
