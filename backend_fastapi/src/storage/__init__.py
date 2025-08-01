"""
File-based storage system for IntelliMock.
Provides JSON file persistence without database dependencies.
"""

from .base import BaseStorage, StorageError
from .document_storage import DocumentStorage
from .mock_storage import MockStorage
from .report_storage import ReportStorage

__all__ = [
    "BaseStorage",
    "StorageError",
    "DocumentStorage", 
    "MockStorage",
    "ReportStorage",
]
