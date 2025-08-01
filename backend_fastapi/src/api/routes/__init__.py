"""
API routes package for IntelliMock backend.
"""

from .documents import router as documents_router
from .mock import router as mock_router
from .validation import router as validation_router
from .reports import router as reports_router

__all__ = [
    "documents_router",
    "mock_router",
    "validation_router", 
    "reports_router",
]
