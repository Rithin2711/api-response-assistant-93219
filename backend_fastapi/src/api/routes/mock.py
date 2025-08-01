"""
Mock API endpoints for request simulation and response generation.
"""

import logging
from typing import List, Optional
from uuid import UUID

from fastapi import APIRouter, BackgroundTasks, HTTPException, status

from models.mock_request import MockRequest, MockResponse
from services.mock_service import MockService

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/mock", tags=["Mock API"])
mock_service = MockService()


@router.post("/requests",
             response_model=MockRequest,
             status_code=status.HTTP_201_CREATED,
             summary="Create mock request",
             description="Create a new mock API request for processing")
async def create_mock_request(request: MockRequest):
    """
    Create a new mock API request.
    
    The request will be processed asynchronously using the specified documents
    and LLM provider to generate a realistic API response.
    """
    try:
        created_request = mock_service.create_mock_request(request)
        logger.info(f"Mock request created: {created_request.id}")
        return created_request
        
    except Exception as e:
        logger.error(f"Failed to create mock request: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create request: {str(e)}"
        )


@router.post("/requests/{request_id}/process",
             response_model=MockResponse,
             summary="Process mock request",
             description="Process a mock request and generate response")
async def process_mock_request(request_id: UUID, background_tasks: BackgroundTasks):
    """
    Process a mock request and generate response.
    
    This endpoint triggers the RAG-based response generation using the
    associated documents and configured LLM provider.
    """
    # Check if request exists
    request = mock_service.get_mock_request(request_id)
    if not request:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Mock request not found"
        )
    
    try:
        # Process request (this might take a while with real LLM)
        response = mock_service.process_mock_request(request_id)
        
        if not response:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to generate response"
            )
        
        logger.info(f"Mock request processed: {request_id}")
        return response
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to process mock request {request_id}: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Processing failed: {str(e)}"
        )


@router.get("/requests",
            response_model=List[MockRequest],
            summary="List mock requests",
            description="Get list of mock requests with optional filtering")
async def list_mock_requests(
    user_id: Optional[str] = None,
    session_id: Optional[str] = None,
    hours: Optional[int] = None
):
    """
    List mock requests with optional filtering.
    
    Filter by user ID, session ID, or time range.
    """
    try:
        if hours:
            requests = mock_service.get_request_history(hours)
        else:
            requests = mock_service.list_requests(user_id=user_id, session_id=session_id)
        
        return requests
        
    except Exception as e:
        logger.error(f"Failed to list mock requests: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to list requests: {str(e)}"
        )


@router.get("/requests/{request_id}",
            response_model=MockRequest,
            summary="Get mock request",
            description="Retrieve details of a specific mock request")
async def get_mock_request(request_id: UUID):
    """
    Get details of a specific mock request.
    """
    request = mock_service.get_mock_request(request_id)
    if not request:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Mock request not found"
        )
    
    return request


@router.get("/requests/{request_id}/response",
            response_model=MockResponse,
            summary="Get mock response",
            description="Get the generated response for a mock request")
async def get_mock_response(request_id: UUID):
    """
    Get the generated response for a mock request.
    """
    response = mock_service.get_response_by_request(request_id)
    if not response:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Mock response not found"
        )
    
    return response


@router.delete("/requests/{request_id}",
               status_code=status.HTTP_204_NO_CONTENT,
               summary="Delete mock request",
               description="Delete a mock request and its response")
async def delete_mock_request(request_id: UUID):
    """
    Delete a mock request and its associated response.
    """
    success = mock_service.delete_request(request_id)
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Mock request not found"
        )
    
    logger.info(f"Mock request deleted: {request_id}")


# Convenience endpoint for quick mock generation
@router.post("/generate",
             response_model=MockResponse,
             summary="Generate mock response",
             description="One-step endpoint to create request and generate response")
async def generate_mock_response(request: MockRequest):
    """
    One-step endpoint to create a mock request and generate response.
    
    This is a convenience endpoint that combines request creation and processing
    into a single API call for quick testing.
    """
    try:
        # Create request
        created_request = mock_service.create_mock_request(request)
        
        # Process immediately
        response = mock_service.process_mock_request(created_request.id)
        
        if not response:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to generate response"
            )
        
        logger.info(f"Mock response generated for request: {created_request.id}")
        return response
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to generate mock response: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Generation failed: {str(e)}"
        )
