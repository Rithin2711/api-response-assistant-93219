"""
Mock request and response storage implementation.
"""

from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional
from uuid import UUID

from models.mock_request import MockRequest, MockResponse, RequestStatus
from storage.base import BaseStorage


class MockStorage(BaseStorage[MockRequest]):
    """File-based storage for mock requests."""
    
    def __init__(self, storage_dir: str = "data/mock_requests"):
        """Initialize mock request storage."""
        super().__init__(storage_dir, MockRequest)
    
    def _update_index_entry(self, entry: Dict[str, Any], item: MockRequest) -> None:
        """Update index entry with request-specific fields."""
        entry.update({
            "method": item.method.value,
            "path": item.path,
            "status": item.status.value,
            "llm_provider": item.llm_provider,
            "user_id": item.user_id,
            "session_id": item.session_id,
        })
    
    # PUBLIC_INTERFACE
    def search_by_method(self, method: str) -> List[MockRequest]:
        """
        Search requests by HTTP method.
        
        Args:
            method: HTTP method to search for
            
        Returns:
            Matching requests
        """
        return self.search({"method": method.upper()})
    
    # PUBLIC_INTERFACE
    def search_by_path(self, path: str) -> List[MockRequest]:
        """
        Search requests by path pattern.
        
        Args:
            path: Path pattern to search for
            
        Returns:
            Matching requests
        """
        requests = self.list_all()
        return [req for req in requests if path.lower() in req.path.lower()]
    
    # PUBLIC_INTERFACE
    def search_by_user(self, user_id: str) -> List[MockRequest]:
        """
        Search requests by user.
        
        Args:
            user_id: User identifier
            
        Returns:
            User's requests
        """
        return self.search({"user_id": user_id})
    
    # PUBLIC_INTERFACE
    def search_by_session(self, session_id: str) -> List[MockRequest]:
        """
        Search requests by session.
        
        Args:
            session_id: Session identifier
            
        Returns:
            Session's requests
        """
        return self.search({"session_id": session_id})
    
    # PUBLIC_INTERFACE
    def get_recent_requests(self, hours: int = 24) -> List[MockRequest]:
        """
        Get recent requests within specified hours.
        
        Args:
            hours: Hours to look back
            
        Returns:
            Recent requests
        """
        cutoff_time = datetime.utcnow() - timedelta(hours=hours)
        requests = self.list_all()
        
        return [
            req for req in requests 
            if req.created_at >= cutoff_time
        ]
    
    # PUBLIC_INTERFACE
    def update_status(self, request_id: UUID, status: RequestStatus) -> Optional[MockRequest]:
        """
        Update request status.
        
        Args:
            request_id: Request identifier
            status: New status
            
        Returns:
            Updated request if found
        """
        request = self.get(request_id)
        if not request:
            return None
        
        request.status = status
        if status in [RequestStatus.COMPLETED, RequestStatus.FAILED]:
            request.processed_at = datetime.utcnow()
        
        return self.update(request)


class MockResponseStorage(BaseStorage[MockResponse]):
    """File-based storage for mock responses."""
    
    def __init__(self, storage_dir: str = "data/mock_responses"):
        """Initialize mock response storage."""
        super().__init__(storage_dir, MockResponse)
    
    def _update_index_entry(self, entry: Dict[str, Any], item: MockResponse) -> None:
        """Update index entry with response-specific fields."""
        entry.update({
            "request_id": str(item.request_id),
            "status_code": item.status_code,
            "llm_provider": item.llm_provider,
            "confidence_score": item.confidence_score,
            "generation_time_ms": item.generation_time_ms,
        })
    
    # PUBLIC_INTERFACE
    def get_by_request(self, request_id: UUID) -> Optional[MockResponse]:
        """
        Get response by request ID.
        
        Args:
            request_id: Request identifier
            
        Returns:
            Response if found
        """
        responses = self.search({"request_id": str(request_id)})
        return responses[0] if responses else None
    
    # PUBLIC_INTERFACE
    def search_by_status_code(self, status_code: int) -> List[MockResponse]:
        """
        Search responses by HTTP status code.
        
        Args:
            status_code: HTTP status code
            
        Returns:
            Matching responses
        """
        return self.search({"status_code": status_code})
    
    # PUBLIC_INTERFACE
    def search_by_provider(self, provider: str) -> List[MockResponse]:
        """
        Search responses by LLM provider.
        
        Args:
            provider: LLM provider name
            
        Returns:
            Matching responses
        """
        return self.search({"llm_provider": provider})
    
    # PUBLIC_INTERFACE
    def get_performance_stats(self) -> Dict[str, Any]:
        """
        Get response performance statistics.
        
        Returns:
            Performance statistics
        """
        responses = self.list_all()
        if not responses:
            return {"total_responses": 0}
        
        generation_times = [r.generation_time_ms for r in responses]
        confidence_scores = [r.confidence_score for r in responses if r.confidence_score]
        
        return {
            "total_responses": len(responses),
            "avg_generation_time_ms": sum(generation_times) / len(generation_times),
            "min_generation_time_ms": min(generation_times),
            "max_generation_time_ms": max(generation_times),
            "avg_confidence_score": sum(confidence_scores) / len(confidence_scores) if confidence_scores else 0.0,
            "success_rate": len([r for r in responses if 200 <= r.status_code < 300]) / len(responses),
        }
