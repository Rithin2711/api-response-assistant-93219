"""
Vector-based search service for RAG functionality.
Placeholder implementation without external vector database dependencies.
"""

import logging
import re
from typing import List, Optional, Tuple
from uuid import UUID

from models.document import Document
from storage.document_storage import DocumentStorage

logger = logging.getLogger(__name__)


class VectorService:
    """Service for vector-based document search and retrieval."""
    
    def __init__(self, storage_dir: str = "data/documents"):
        """
        Initialize vector service.
        
        Args:
            storage_dir: Document storage directory
        """
        self.document_storage = DocumentStorage(storage_dir)
    
    # PUBLIC_INTERFACE
    def generate_embeddings(self, document_id: UUID) -> bool:
        """
        Generate embeddings for a document.
        Placeholder implementation using simple text processing.
        
        Args:
            document_id: Document identifier
            
        Returns:
            True if embeddings generated successfully
        """
        try:
            document = self.document_storage.get(document_id)
            if not document or not document.chunks:
                return False
            
            # Placeholder: Generate simple term frequency vectors
            embeddings = []
            for chunk in document.chunks:
                embedding = self._create_simple_embedding(chunk)
                embeddings.append(embedding)
            
            # Update document with embeddings
            document.vector_embeddings = embeddings
            self.document_storage.update(document)
            
            logger.info(f"Generated embeddings for document {document_id}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to generate embeddings for {document_id}: {str(e)}")
            return False
    
    def _create_simple_embedding(self, text: str) -> List[float]:
        """
        Create simple embedding using term frequency.
        This is a placeholder - in production, use proper embedding models.
        
        Args:
            text: Text to embed
            
        Returns:
            Simple numeric vector
        """
        # Normalize text
        text = text.lower()
        words = re.findall(r'\b\w+\b', text)
        
        # Create vocabulary of common API terms
        api_terms = [
            'api', 'endpoint', 'request', 'response', 'method', 'parameter',
            'header', 'body', 'json', 'get', 'post', 'put', 'delete', 'patch',
            'authentication', 'authorization', 'token', 'schema', 'validation',
            'error', 'status', 'code', 'data', 'id', 'name', 'user', 'create',
            'update', 'retrieve', 'list', 'search', 'filter', 'sort', 'limit',
            'offset', 'page', 'query', 'path', 'url', 'http', 'https', 'rest'
        ]
        
        # Create term frequency vector
        embedding = []
        for term in api_terms:
            count = words.count(term)
            frequency = count / len(words) if words else 0.0
            embedding.append(frequency)
        
        # Pad or truncate to fixed size (32 dimensions)
        target_size = 32
        if len(embedding) > target_size:
            embedding = embedding[:target_size]
        else:
            embedding.extend([0.0] * (target_size - len(embedding)))
        
        return embedding
    
    # PUBLIC_INTERFACE
    def search_similar(self, query: str, document_ids: Optional[List[UUID]] = None,
                      limit: int = 5) -> List[Tuple[Document, List[str], float]]:
        """
        Search for similar content using vector similarity.
        Placeholder implementation using text matching.
        
        Args:
            query: Search query
            document_ids: Optional list of document IDs to search within
            limit: Maximum number of results
            
        Returns:
            List of (document, matching_chunks, similarity_score) tuples
        """
        try:
            # Get documents to search
            if document_ids:
                documents = [self.document_storage.get(doc_id) for doc_id in document_ids]
                documents = [doc for doc in documents if doc is not None]
            else:
                documents = self.document_storage.list_all()
            
            # Filter to documents with content
            documents = [doc for doc in documents if doc.chunks]
            
            # Create query embedding
            query_embedding = self._create_simple_embedding(query)
            query_terms = set(re.findall(r'\b\w+\b', query.lower()))
            
            results = []
            
            for document in documents:
                matching_chunks = []
                chunk_scores = []
                
                # Check each chunk
                for i, chunk in enumerate(document.chunks):
                    # Simple text similarity
                    chunk_terms = set(re.findall(r'\b\w+\b', chunk.lower()))
                    common_terms = query_terms.intersection(chunk_terms)
                    
                    if common_terms:
                        # Calculate similarity score
                        similarity = len(common_terms) / len(query_terms.union(chunk_terms))
                        
                        # Also consider embedding similarity if available
                        if document.vector_embeddings and i < len(document.vector_embeddings):
                            embedding_similarity = self._cosine_similarity(
                                query_embedding, document.vector_embeddings[i]
                            )
                            similarity = (similarity + embedding_similarity) / 2
                        
                        if similarity > 0.1:  # Minimum threshold
                            matching_chunks.append(chunk)
                            chunk_scores.append(similarity)
                
                if matching_chunks:
                    # Overall document score is max chunk score
                    max_score = max(chunk_scores)
                    results.append((document, matching_chunks, max_score))
            
            # Sort by similarity score and limit results
            results.sort(key=lambda x: x[2], reverse=True)
            return results[:limit]
            
        except Exception as e:
            logger.error(f"Vector search failed: {str(e)}")
            return []
    
    def _cosine_similarity(self, vec1: List[float], vec2: List[float]) -> float:
        """
        Calculate cosine similarity between two vectors.
        
        Args:
            vec1: First vector
            vec2: Second vector
            
        Returns:
            Cosine similarity score (0-1)
        """
        try:
            # Ensure vectors are same length
            min_len = min(len(vec1), len(vec2))
            vec1 = vec1[:min_len]
            vec2 = vec2[:min_len]
            
            # Calculate dot product
            dot_product = sum(a * b for a, b in zip(vec1, vec2))
            
            # Calculate magnitudes
            mag1 = sum(a * a for a in vec1) ** 0.5
            mag2 = sum(b * b for b in vec2) ** 0.5
            
            if mag1 == 0 or mag2 == 0:
                return 0.0
            
            return dot_product / (mag1 * mag2)
            
        except Exception:
            return 0.0
    
    # PUBLIC_INTERFACE
    def get_context_for_request(self, method: str, path: str, 
                              document_ids: List[UUID]) -> List[str]:
        """
        Get relevant context chunks for an API request.
        
        Args:
            method: HTTP method
            path: API path
            document_ids: Documents to search in
            
        Returns:
            Relevant context chunks
        """
        # Create search query from request
        query = f"{method} {path}"
        
        # Add common API terms
        path_parts = path.strip('/').split('/')
        query += " " + " ".join(path_parts)
        
        # Search for similar content
        results = self.search_similar(query, document_ids, limit=10)
        
        # Extract and deduplicate chunks
        context_chunks = []
        seen_chunks = set()
        
        for document, chunks, score in results:
            for chunk in chunks:
                if chunk not in seen_chunks:
                    context_chunks.append(chunk)
                    seen_chunks.add(chunk)
        
        return context_chunks[:20]  # Limit context size
    
    # PUBLIC_INTERFACE
    def reindex_all_documents(self) -> int:
        """
        Regenerate embeddings for all documents.
        
        Returns:
            Number of documents reindexed
        """
        documents = self.document_storage.list_all()
        reindexed_count = 0
        
        for document in documents:
            if self.generate_embeddings(document.id):
                reindexed_count += 1
        
        logger.info(f"Reindexed {reindexed_count} documents")
        return reindexed_count
