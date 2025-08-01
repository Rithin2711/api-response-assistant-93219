"""
Document storage implementation for file-based persistence.
"""

import hashlib
from datetime import datetime
from typing import Any, Dict, List, Optional
from uuid import UUID

from models.document import Document, DocumentType, DocumentStatus
from storage.base import BaseStorage


class DocumentStorage(BaseStorage[Document]):
    """File-based storage for Document objects."""
    
    def __init__(self, storage_dir: str = "data/documents"):
        """Initialize document storage."""
        super().__init__(storage_dir, Document)
        self.content_dir = self.storage_dir / "content"
        self.content_dir.mkdir(exist_ok=True)
    
    def _update_index_entry(self, entry: Dict[str, Any], item: Document) -> None:
        """Update index entry with document-specific fields."""
        entry.update({
            "name": item.name,
            "type": item.type.value,
            "status": item.status.value,
            "original_filename": item.original_filename,
            "file_size": item.file_size,
            "content_hash": item.content_hash,
        })
    
    def _store_content_file(self, document_id: UUID, content: bytes) -> str:
        """Store document content as separate file."""
        content_file = self.content_dir / f"{str(document_id)}.bin"
        
        with open(content_file, 'wb') as f:
            f.write(content)
        
        return str(content_file)
    
    def _load_content_file(self, document_id: UUID) -> Optional[bytes]:
        """Load document content from file."""
        content_file = self.content_dir / f"{str(document_id)}.bin"
        
        if not content_file.exists():
            return None
        
        try:
            with open(content_file, 'rb') as f:
                return f.read()
        except Exception:
            return None
    
    # PUBLIC_INTERFACE
    def create_with_content(self, document: Document, content: bytes) -> Document:
        """
        Create document with binary content.
        
        Args:
            document: Document metadata
            content: Binary file content
            
        Returns:
            Created document
        """
        # Calculate content hash
        content_hash = hashlib.sha256(content).hexdigest()
        document.content_hash = content_hash
        document.file_size = len(content)
        
        # Store content file
        self._store_content_file(document.id, content)
        
        # Create document record
        return self.create(document)
    
    # PUBLIC_INTERFACE
    def get_content(self, document_id: UUID) -> Optional[bytes]:
        """
        Get document binary content.
        
        Args:
            document_id: Document identifier
            
        Returns:
            Binary content if found
        """
        return self._load_content_file(document_id)
    
    # PUBLIC_INTERFACE
    def update_status(self, document_id: UUID, status: DocumentStatus, 
                     error_message: Optional[str] = None) -> Optional[Document]:
        """
        Update document processing status.
        
        Args:
            document_id: Document identifier
            status: New status
            error_message: Error message for failed status
            
        Returns:
            Updated document if found
        """
        document = self.get(document_id)
        if not document:
            return None
        
        document.status = status
        document.updated_at = datetime.utcnow()
        
        if status == DocumentStatus.COMPLETED:
            document.processed_at = datetime.utcnow()
        elif status == DocumentStatus.FAILED and error_message:
            document.error_message = error_message
        
        return self.update(document)
    
    # PUBLIC_INTERFACE
    def search_by_type(self, doc_type: DocumentType) -> List[Document]:
        """
        Search documents by type.
        
        Args:
            doc_type: Document type to search for
            
        Returns:
            Matching documents
        """
        return self.search({"type": doc_type})
    
    # PUBLIC_INTERFACE
    def search_by_status(self, status: DocumentStatus) -> List[Document]:
        """
        Search documents by status.
        
        Args:
            status: Status to search for
            
        Returns:
            Matching documents
        """
        return self.search({"status": status})
    
    # PUBLIC_INTERFACE
    def get_storage_stats(self) -> Dict[str, Any]:
        """
        Get storage statistics.
        
        Returns:
            Storage statistics
        """
        documents = self.list_all()
        total_size = sum(doc.file_size for doc in documents)
        
        type_counts = {}
        status_counts = {}
        
        for doc in documents:
            # Count by type
            type_key = doc.type.value
            type_counts[type_key] = type_counts.get(type_key, 0) + 1
            
            # Count by status
            status_key = doc.status.value
            status_counts[status_key] = status_counts.get(status_key, 0) + 1
        
        return {
            "total_documents": len(documents),
            "total_size_bytes": total_size,
            "total_size_mb": round(total_size / (1024 * 1024), 2),
            "by_type": type_counts,
            "by_status": status_counts,
            "storage_path": str(self.storage_dir),
        }
    
    def delete(self, item_id: UUID) -> bool:
        """Delete document and its content file."""
        # Delete content file first
        content_file = self.content_dir / f"{str(item_id)}.bin"
        if content_file.exists():
            try:
                content_file.unlink()
            except Exception:
                pass  # Continue with document deletion even if content fails
        
        # Delete document record
        return super().delete(item_id)
