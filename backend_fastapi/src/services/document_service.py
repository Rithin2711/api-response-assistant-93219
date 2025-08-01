"""
Document ingestion service for processing uploaded API documentation.
Handles OpenAPI specs, JSON samples, and Postman collections.
"""

import json
import logging
import mimetypes
from typing import Any, Dict, List, Optional
from uuid import UUID

import yaml

from models.document import Document, DocumentType, DocumentStatus, DocumentUpload
from storage.document_storage import DocumentStorage

logger = logging.getLogger(__name__)


class DocumentService:
    """Service for document ingestion and processing."""
    
    def __init__(self, storage_dir: str = "data/documents"):
        """
        Initialize document service.
        
        Args:
            storage_dir: Directory for document storage
        """
        self.storage = DocumentStorage(storage_dir)
    
    # PUBLIC_INTERFACE
    def upload_document(self, upload_data: DocumentUpload, file_content: bytes,
                       original_filename: str) -> Document:
        """
        Upload and process a new document.
        
        Args:
            upload_data: Document metadata
            file_content: Binary file content
            original_filename: Original filename
            
        Returns:
            Created document
            
        Raises:
            ValueError: If document processing fails
        """
        try:
            # Create document record
            document = Document(
                name=upload_data.name,
                type=upload_data.type,
                original_filename=original_filename,
                file_size=len(file_content),
                content_hash="",  # Will be set by storage
                metadata={
                    "description": upload_data.description,
                    "tags": upload_data.tags,
                    "mime_type": mimetypes.guess_type(original_filename)[0],
                }
            )
            
            # Store document with content
            document = self.storage.create_with_content(document, file_content)
            
            # Process document content asynchronously
            self._process_document_content(document.id, file_content)
            
            logger.info(f"Document uploaded successfully: {document.id}")
            return document
            
        except Exception as e:
            logger.error(f"Failed to upload document: {str(e)}")
            raise ValueError(f"Document upload failed: {str(e)}")
    
    def _process_document_content(self, document_id: UUID, content: bytes) -> None:
        """
        Process document content and extract structured data.
        
        Args:
            document_id: Document identifier
            content: File content to process
        """
        try:
            # Update status to processing
            self.storage.update_status(document_id, DocumentStatus.PROCESSING)
            
            # Get document for type information
            document = self.storage.get(document_id)
            if not document:
                raise ValueError("Document not found")
            
            # Parse content based on type
            parsed_content = self._parse_content(content, document.type)
            
            # Update document with parsed content
            document.content = parsed_content
            document.chunks = self._extract_text_chunks(parsed_content, document.type)
            
            # Mark as completed
            document = self.storage.update(document)
            self.storage.update_status(document_id, DocumentStatus.COMPLETED)
            
            logger.info(f"Document processed successfully: {document_id}")
            
        except Exception as e:
            error_msg = f"Failed to process document: {str(e)}"
            logger.error(f"Document processing failed for {document_id}: {error_msg}")
            self.storage.update_status(document_id, DocumentStatus.FAILED, error_msg)
    
    def _parse_content(self, content: bytes, doc_type: DocumentType) -> Dict[str, Any]:
        """
        Parse content based on document type.
        
        Args:
            content: File content
            doc_type: Document type
            
        Returns:
            Parsed content structure
        """
        content_str = content.decode('utf-8')
        
        if doc_type == DocumentType.OPENAPI:
            return self._parse_openapi(content_str)
        elif doc_type == DocumentType.JSON_SAMPLE:
            return self._parse_json(content_str)
        elif doc_type == DocumentType.POSTMAN_COLLECTION:
            return self._parse_postman(content_str)
        elif doc_type == DocumentType.YAML:
            return self._parse_yaml(content_str)
        elif doc_type == DocumentType.SWAGGER:
            return self._parse_swagger(content_str)
        else:
            return {"raw_content": content_str}
    
    def _parse_openapi(self, content: str) -> Dict[str, Any]:
        """Parse OpenAPI specification."""
        try:
            # Try JSON first
            data = json.loads(content)
        except json.JSONDecodeError:
            # Try YAML
            data = yaml.safe_load(content)
        
        # Validate OpenAPI structure
        required_fields = ['openapi', 'info', 'paths']
        if not all(field in data for field in required_fields):
            raise ValueError(f"Invalid OpenAPI document. Required fields: {required_fields}")
        
        return data
    
    def _parse_json(self, content: str) -> Dict[str, Any]:
        """Parse JSON sample."""
        return json.loads(content)
    
    def _parse_postman(self, content: str) -> Dict[str, Any]:
        """Parse Postman collection."""
        data = json.loads(content)
        
        # Validate Postman structure
        if 'collection' not in data or 'item' not in data.get('collection', {}):
            raise ValueError("Invalid Postman collection format")
        
        return data
    
    def _parse_yaml(self, content: str) -> Dict[str, Any]:
        """Parse YAML file."""
        return yaml.safe_load(content)
    
    def _parse_swagger(self, content: str) -> Dict[str, Any]:
        """Parse Swagger specification."""
        try:
            # Try JSON first
            data = json.loads(content)
        except json.JSONDecodeError:
            # Try YAML
            data = yaml.safe_load(content)
        
        # Validate Swagger structure
        if 'swagger' not in data or 'info' not in data:
            raise ValueError("Invalid Swagger document")
        
        return data
    
    def _extract_text_chunks(self, content: Dict[str, Any], doc_type: DocumentType) -> List[str]:
        """
        Extract text chunks for vector search.
        
        Args:
            content: Parsed content
            doc_type: Document type
            
        Returns:
            Text chunks for indexing
        """
        chunks = []
        
        if doc_type == DocumentType.OPENAPI:
            chunks.extend(self._extract_openapi_chunks(content))
        elif doc_type == DocumentType.POSTMAN_COLLECTION:
            chunks.extend(self._extract_postman_chunks(content))
        else:
            # Generic text extraction
            chunks.extend(self._extract_generic_chunks(content))
        
        return chunks
    
    def _extract_openapi_chunks(self, content: Dict[str, Any]) -> List[str]:
        """Extract meaningful chunks from OpenAPI spec."""
        chunks = []
        
        # API info
        if 'info' in content:
            info = content['info']
            chunks.append(f"API: {info.get('title', 'Unknown')} - {info.get('description', '')}")
        
        # Paths and operations
        if 'paths' in content:
            for path, path_obj in content['paths'].items():
                for method, operation in path_obj.items():
                    if isinstance(operation, dict):
                        summary = operation.get('summary', '')
                        description = operation.get('description', '')
                        chunk = f"{method.upper()} {path}"
                        if summary:
                            chunk += f" - {summary}"
                        if description:
                            chunk += f": {description}"
                        chunks.append(chunk)
                        
                        # Parameters
                        if 'parameters' in operation:
                            for param in operation['parameters']:
                                param_info = f"Parameter {param.get('name')}: {param.get('description', '')}"
                                chunks.append(param_info)
                        
                        # Request body
                        if 'requestBody' in operation:
                            req_body = operation['requestBody']
                            chunks.append(f"Request body for {method.upper()} {path}: {req_body.get('description', '')}")
                        
                        # Responses
                        if 'responses' in operation:
                            for status, response in operation['responses'].items():
                                resp_desc = response.get('description', '')
                                chunks.append(f"Response {status} for {method.upper()} {path}: {resp_desc}")
        
        # Components/schemas
        if 'components' in content and 'schemas' in content['components']:
            for schema_name, schema_def in content['components']['schemas'].items():
                schema_desc = schema_def.get('description', '')
                chunks.append(f"Schema {schema_name}: {schema_desc}")
        
        return chunks
    
    def _extract_postman_chunks(self, content: Dict[str, Any]) -> List[str]:
        """Extract chunks from Postman collection."""
        chunks = []
        
        collection = content.get('collection', {})
        
        # Collection info
        if 'info' in collection:
            info = collection['info']
            chunks.append(f"Collection: {info.get('name', 'Unknown')} - {info.get('description', '')}")
        
        # Items (requests)
        def extract_from_items(items):
            for item in items:
                if 'name' in item:
                    item_chunk = f"Request: {item['name']}"
                    if 'request' in item:
                        request = item['request']
                        if 'method' in request:
                            item_chunk += f" ({request['method']})"
                        if 'url' in request:
                            url = request['url']
                            if isinstance(url, dict):
                                raw_url = url.get('raw', '')
                            else:
                                raw_url = str(url)
                            item_chunk += f" - {raw_url}"
                    chunks.append(item_chunk)
                
                # Recursive for nested items
                if 'item' in item:
                    extract_from_items(item['item'])
        
        if 'item' in collection:
            extract_from_items(collection['item'])
        
        return chunks
    
    def _extract_generic_chunks(self, content: Dict[str, Any]) -> List[str]:
        """Extract generic text chunks from any JSON structure."""
        chunks = []
        
        def extract_strings(obj, path=""):
            if isinstance(obj, dict):
                for key, value in obj.items():
                    new_path = f"{path}.{key}" if path else key
                    if isinstance(value, str) and len(value.strip()) > 10:
                        chunks.append(f"{new_path}: {value}")
                    else:
                        extract_strings(value, new_path)
            elif isinstance(obj, list):
                for i, item in enumerate(obj):
                    extract_strings(item, f"{path}[{i}]")
        
        extract_strings(content)
        return chunks
    
    # PUBLIC_INTERFACE
    def get_document(self, document_id: UUID) -> Optional[Document]:
        """
        Get document by ID.
        
        Args:
            document_id: Document identifier
            
        Returns:
            Document if found
        """
        return self.storage.get(document_id)
    
    # PUBLIC_INTERFACE
    def list_documents(self, doc_type: Optional[DocumentType] = None,
                      status: Optional[DocumentStatus] = None) -> List[Document]:
        """
        List documents with optional filtering.
        
        Args:
            doc_type: Filter by document type
            status: Filter by status
            
        Returns:
            Filtered list of documents
        """
        if doc_type and status:
            return self.storage.search({"type": doc_type, "status": status})
        elif doc_type:
            return self.storage.search_by_type(doc_type)
        elif status:
            return self.storage.search_by_status(status)
        else:
            return self.storage.list_all()
    
    # PUBLIC_INTERFACE
    def delete_document(self, document_id: UUID) -> bool:
        """
        Delete document and its content.
        
        Args:
            document_id: Document identifier
            
        Returns:
            True if deleted successfully
        """
        return self.storage.delete(document_id)
    
    # PUBLIC_INTERFACE
    def get_document_content(self, document_id: UUID) -> Optional[bytes]:
        """
        Get document binary content.
        
        Args:
            document_id: Document identifier
            
        Returns:
            Binary content if found
        """
        return self.storage.get_content(document_id)
    
    # PUBLIC_INTERFACE
    def search_documents(self, query: str) -> List[Document]:
        """
        Search documents by text query.
        
        Args:
            query: Search query
            
        Returns:
            Matching documents
        """
        # Simple text search in document names and chunks
        all_docs = self.storage.list_all()
        query_lower = query.lower()
        
        matching_docs = []
        for doc in all_docs:
            # Search in name
            if query_lower in doc.name.lower():
                matching_docs.append(doc)
                continue
            
            # Search in chunks
            if doc.chunks:
                for chunk in doc.chunks:
                    if query_lower in chunk.lower():
                        matching_docs.append(doc)
                        break
        
        return matching_docs
