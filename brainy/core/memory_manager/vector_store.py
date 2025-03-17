"""
Vector store implementation using ChromaDB.

This module provides vector database functionality for semantic search capabilities.
"""
import os
import shutil
from typing import Dict, List, Any, Optional, Tuple
import uuid
from pathlib import Path

import chromadb
from chromadb.utils import embedding_functions

from brainy.config import settings
from brainy.utils.logging import get_logger

# Initialize logger
logger = get_logger(__name__)


class VectorStore:
    """
    Vector store for semantic search capabilities.
    
    This class uses ChromaDB to store and retrieve documents with
    vector embeddings for semantic similarity search.
    """
    
    def __init__(self, collection_name: str = "messages", db_path: Optional[str] = None):
        """
        Initialize the vector store.
        
        Args:
            collection_name: Name of the collection to use
            db_path: Optional path to the ChromaDB directory.
                If not provided, uses the path from settings.
        """
        # Set the path to the ChromaDB directory
        self.db_path = db_path or settings.VECTOR_DB_PATH
        
        # Ensure the directory exists
        os.makedirs(self.db_path, exist_ok=True)
        
        # Collection name
        self.collection_name = collection_name
        
        # Initialize ChromaDB client
        self.client = chromadb.PersistentClient(path=self.db_path)
        
        # Initialize the embedding function
        # Use the local sentence-transformers embedding function with 384 dimensions
        # instead of OpenAI embeddings with 1536 dimensions
        self.embedding_function = embedding_functions.SentenceTransformerEmbeddingFunction(
            model_name="all-MiniLM-L6-v2"
        )
        
        # Get or create the collection with the embedding function
        self.collection = self._get_or_create_collection()
        
        logger.info(f"Initialized vector store at {self.db_path}")
    
    def _get_or_create_collection(self):
        """Get or create the ChromaDB collection."""
        try:
            # Try to get the existing collection
            collection = self.client.get_collection(
                name=self.collection_name,
                embedding_function=self.embedding_function
            )
            logger.info(f"Using existing collection '{self.collection_name}'")
            return collection
        except Exception as e:
            # If it doesn't exist or has incompatible dimensions, create a new one
            # First, try to delete any existing collection with the same name
            try:
                self.client.delete_collection(name=self.collection_name)
                logger.warning(f"Deleted existing collection '{self.collection_name}' due to potential embedding mismatch")
            except Exception:
                # Collection might not exist, which is fine
                pass
            
            # Create a new collection
            collection = self.client.create_collection(
                name=self.collection_name,
                embedding_function=self.embedding_function
            )
            logger.info(f"Created new collection '{self.collection_name}'")
            return collection
    
    async def add_document(
        self,
        text: str,
        metadata: Optional[Dict[str, Any]] = None,
        document_id: Optional[str] = None
    ) -> str:
        """
        Add a document to the vector store.
        
        Args:
            text: Text content of the document
            metadata: Optional metadata for the document
            document_id: Optional ID for the document. Will be generated if not provided.
            
        Returns:
            The ID of the added document
        """
        # Generate an ID if not provided
        doc_id = document_id or str(uuid.uuid4())
        
        try:
            # Add the document to the collection (the embedding will be generated automatically)
            self.collection.add(
                documents=[text],
                metadatas=[metadata or {}],
                ids=[doc_id]
            )
            
            logger.debug(f"Added document to vector store", document_id=doc_id)
            
            return doc_id
        except Exception as e:
            logger.error(f"Error adding document to vector store: {e}")
            raise
    
    def query(
        self,
        query_text: str,
        filter_metadata: Optional[Dict[str, Any]] = None,
        limit: int = 5
    ) -> List[Dict[str, Any]]:
        """
        Query the vector store for similar documents.
        
        Args:
            query_text: Text to find similar documents for
            filter_metadata: Optional metadata filter to apply
            limit: Maximum number of results to return
            
        Returns:
            List of matching documents with their metadata and distances
        """
        try:
            # Use the embedding function to get embeddings for the query
            results = self.collection.query(
                query_texts=[query_text],
                n_results=limit,
                where=filter_metadata
            )
            
            # Process results
            documents = []
            if results["documents"] and results["documents"][0]:
                for i, doc in enumerate(results["documents"][0]):
                    document = {
                        "text": doc,
                        "id": results["ids"][0][i] if results["ids"] and results["ids"][0] else None,
                        "metadata": results["metadatas"][0][i] if results["metadatas"] and results["metadatas"][0] else {},
                        "distance": results["distances"][0][i] if results["distances"] and results["distances"][0] else None
                    }
                    documents.append(document)
            
            logger.debug(f"Query returned {len(documents)} results")
            
            return documents
        except Exception as e:
            logger.error(f"Error querying vector store: {e}")
            return []
    
    def delete_document(self, document_id: str) -> bool:
        """
        Delete a document from the vector store.
        
        Args:
            document_id: ID of the document to delete
            
        Returns:
            True if successful, False if an error occurred
        """
        try:
            self.collection.delete(ids=[document_id])
            logger.debug(f"Deleted document from vector store", document_id=document_id)
            return True
        except Exception as e:
            logger.error(f"Error deleting document from vector store: {e}", document_id=document_id)
            return False
    
    def delete_by_metadata(self, filter_metadata: Dict[str, Any]) -> bool:
        """
        Delete documents matching metadata filter.
        
        Args:
            filter_metadata: Metadata filter to apply for deletion
            
        Returns:
            True if successful, False if an error occurred
        """
        try:
            self.collection.delete(where=filter_metadata)
            logger.debug(f"Deleted documents by metadata", filter=filter_metadata)
            return True
        except Exception as e:
            logger.error(f"Error deleting documents by metadata: {e}", filter=filter_metadata)
            return False
    
    def get_document(self, document_id: str) -> Optional[Dict[str, Any]]:
        """
        Get a document by ID.
        
        Args:
            document_id: ID of the document to get
            
        Returns:
            The document if found, None otherwise
        """
        try:
            result = self.collection.get(ids=[document_id])
            
            if not result["documents"]:
                return None
            
            document = {
                "text": result["documents"][0],
                "id": document_id,
                "metadata": result["metadatas"][0] if result["metadatas"] else {}
            }
            
            return document
        except Exception as e:
            logger.error(f"Error getting document from vector store: {e}", document_id=document_id)
            return None


# Singleton instance
_vector_store: Optional[Dict[str, VectorStore]] = {}


def get_vector_store(collection_name: str = "messages") -> VectorStore:
    """
    Get the vector store instance.
    
    Args:
        collection_name: Name of the collection to use
        
    Returns:
        The vector store instance
    """
    global _vector_store
    if collection_name not in _vector_store:
        _vector_store[collection_name] = VectorStore(collection_name=collection_name)
    
    return _vector_store[collection_name] 