"""
Mock API service for generating simulated responses.
Orchestrates document retrieval, LLM generation, and response formatting.
"""

import json
import logging
from datetime import datetime
from typing import Any, Dict, List, Optional
from uuid import UUID

from models.mock_request import MockRequest, MockResponse, RequestStatus
from storage.mock_storage import MockStorage, MockResponseStorage
from services.document_service import DocumentService
from services.vector_service import VectorService
from services.llm_service import LLMService

logger = logging.getLogger(__name__)


class MockService:
    """Service for handling mock API requests and generating responses."""
    
    def __init__(self, storage_dir: str = "data"):
        """
        Initialize mock service.
        
        Args:
            storage_dir: Base storage directory
        """
        self.request_storage = MockStorage(f"{storage_dir}/mock_requests")
        self.response_storage = MockResponseStorage(f"{storage_dir}/mock_responses")
        self.document_service = DocumentService(f"{storage_dir}/documents")
        self.vector_service = VectorService(f"{storage_dir}/documents")
        self.llm_service = LLMService()
    
    # PUBLIC_INTERFACE
    def create_mock_request(self, request: MockRequest) -> MockRequest:
        """
        Create a new mock request.
        
        Args:
            request: Mock request to create
            
        Returns:
            Created request
        """
        return self.request_storage.create(request)
    
    # PUBLIC_INTERFACE
    def process_mock_request(self, request_id: UUID) -> Optional[MockResponse]:
        """
        Process a mock request and generate response.
        
        Args:
            request_id: Request identifier
            
        Returns:
            Generated response if successful
        """
        try:
            # Get request
            request = self.request_storage.get(request_id)
            if not request:
                logger.error(f"Request {request_id} not found")
                return None
            
            # Update status to processing
            self.request_storage.update_status(request_id, RequestStatus.PROCESSING)
            
            start_time = datetime.utcnow()
            
            # Get context from documents
            context_chunks = self.vector_service.get_context_for_request(
                request.method.value, request.path, request.document_ids
            )
            
            if not context_chunks:
                logger.warning(f"No context found for request {request_id}")
                context_chunks = ["No specific documentation found for this endpoint."]
            
            # Generate response using LLM
            llm_response = self.llm_service.generate_mock_response(
                request, context_chunks
            )
            
            if not llm_response:
                # Mark request as failed
                self.request_storage.update_status(request_id, RequestStatus.FAILED)
                return None
            
            # Parse LLM response
            response_data = self._parse_llm_response(llm_response.content)
            
            # Create mock response
            generation_time = (datetime.utcnow() - start_time).total_seconds() * 1000
            
            mock_response = MockResponse(
                request_id=request_id,
                status_code=response_data.get("status_code", 200),
                headers=response_data.get("headers", {"content-type": "application/json"}),
                body=response_data.get("body"),
                llm_provider=request.llm_provider,
                generation_time_ms=int(generation_time),
                context_documents=request.document_ids,
                confidence_score=llm_response.confidence_score or 0.8,
                context_relevance=self._calculate_context_relevance(context_chunks, request),
                retrieved_chunks=context_chunks,
                embedding_similarity=[0.8] * len(context_chunks),  # Placeholder
            )
            
            # Store response
            response = self.response_storage.create(mock_response)
            
            # Mark request as completed
            self.request_storage.update_status(request_id, RequestStatus.COMPLETED)
            
            logger.info(f"Generated mock response for request {request_id}")
            return response
            
        except Exception as e:
            logger.error(f"Failed to process mock request {request_id}: {str(e)}")
            self.request_storage.update_status(request_id, RequestStatus.FAILED)
            return None
    
    def _parse_llm_response(self, llm_content: str) -> Dict[str, Any]:
        """
        Parse LLM response content into structured format.
        
        Args:
            llm_content: Raw LLM response content
            
        Returns:
            Parsed response data
        """
        try:
            # Try to parse as JSON
            if llm_content.strip().startswith('{'):
                return json.loads(llm_content)
            
            # Extract JSON from text if wrapped
            json_start = llm_content.find('{')
            json_end = llm_content.rfind('}') + 1
            
            if json_start >= 0 and json_end > json_start:
                json_str = llm_content[json_start:json_end]
                return json.loads(json_str)
            
            # Fallback: create response from text
            return {
                "status_code": 200,
                "headers": {"content-type": "application/json"},
                "body": {"message": llm_content.strip()}
            }
            
        except json.JSONDecodeError:
            # Return text response
            return {
                "status_code": 200,
                "headers": {"content-type": "text/plain"},
                "body": llm_content
            }
    
    def _calculate_context_relevance(self, context_chunks: List[str], 
                                   request: MockRequest) -> float:
        """
        Calculate how relevant the context is to the request.
        
        Args:
            context_chunks: Retrieved context chunks
            request: Mock request
            
        Returns:
            Relevance score (0-1)
        """
        if not context_chunks:
            return 0.0
        
        request_terms = set()
        request_terms.add(request.method.value.lower())
        request_terms.update(request.path.lower().split('/'))
        
        if request.body:
            body_str = json.dumps(request.body).lower()
            request_terms.update(body_str.split())
        
        # Count matches in context
        total_matches = 0
        total_terms = len(request_terms)
        
        for chunk in context_chunks:
            chunk_lower = chunk.lower()
            matches = sum(1 for term in request_terms if term in chunk_lower)
            total_matches += matches
        
        if total_terms == 0:
            return 0.5  # Default relevance
        
        relevance = min(total_matches / (total_terms * len(context_chunks)), 1.0)
        return max(relevance, 0.1)  # Minimum relevance
    
    # PUBLIC_INTERFACE
    def get_mock_request(self, request_id: UUID) -> Optional[MockRequest]:
        """
        Get mock request by ID.
        
        Args:
            request_id: Request identifier
            
        Returns:
            Request if found
        """
        return self.request_storage.get(request_id)
    
    # PUBLIC_INTERFACE
    def get_mock_response(self, response_id: UUID) -> Optional[MockResponse]:
        """
        Get mock response by ID.
        
        Args:
            response_id: Response identifier
            
        Returns:
            Response if found
        """
        return self.response_storage.get(response_id)
    
    # PUBLIC_INTERFACE
    def get_response_by_request(self, request_id: UUID) -> Optional[MockResponse]:
        """
        Get response for a specific request.
        
        Args:
            request_id: Request identifier
            
        Returns:
            Associated response if found
        """
        return self.response_storage.get_by_request(request_id)
    
    # PUBLIC_INTERFACE
    def list_requests(self, user_id: Optional[str] = None, 
                     session_id: Optional[str] = None) -> List[MockRequest]:
        """
        List mock requests with optional filtering.
        
        Args:
            user_id: Filter by user ID
            session_id: Filter by session ID
            
        Returns:
            Filtered list of requests
        """
        if user_id:
            return self.request_storage.search_by_user(user_id)
        elif session_id:
            return self.request_storage.search_by_session(session_id)
        else:
            return self.request_storage.list_all()
    
    # PUBLIC_INTERFACE
    def get_request_history(self, hours: int = 24) -> List[MockRequest]:
        """
        Get recent request history.
        
        Args:
            hours: Hours to look back
            
        Returns:
            Recent requests
        """
        return self.request_storage.get_recent_requests(hours)
    
    # PUBLIC_INTERFACE
    def delete_request(self, request_id: UUID) -> bool:
        """
        Delete mock request and associated response.
        
        Args:
            request_id: Request identifier
            
        Returns:
            True if deleted successfully
        """
        # Delete associated response first
        response = self.response_storage.get_by_request(request_id)
        if response:
            self.response_storage.delete(response.request_id)
        
        # Delete request
        return self.request_storage.delete(request_id)
