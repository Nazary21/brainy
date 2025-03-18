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
        
        # Convert to absolute path if it's relative
        if not os.path.isabs(self.db_path):
            self.db_path = os.path.abspath(self.db_path)
            logger.debug(f"Converted vector DB path to absolute: {self.db_path}")
        
        # Ensure the directory exists
        os.makedirs(self.db_path, exist_ok=True)
        
        # Collection name
        self.collection_name = collection_name
        
        # Initialize ChromaDB client
        self.client = chromadb.PersistentClient(path=self.db_path)
        
        # Initialize the embedding function - always use SentenceTransformer with 384 dimensions
        logger.info(f"Initializing with SentenceTransformer embeddings (384 dimensions)")
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
            error_str = str(e)
            if "dimensionality" in error_str.lower():
                # We have a dimension mismatch - this means the collection was created with different dimensions
                logger.error(f"Dimension mismatch detected with collection '{self.collection_name}'.")
                logger.error(f"The database was created with a different embedding model than the current 384-dimension model.")
                logger.error(f"To resolve this, the existing collection needs to be deleted and recreated.")
                
                # Try to delete the incompatible collection and create a new one
                try:
                    logger.warning(f"Deleting incompatible collection '{self.collection_name}'...")
                    self.client.delete_collection(name=self.collection_name)
                    logger.info(f"Successfully deleted incompatible collection.")
                    
                    # Create a new collection with the correct dimensions
                    collection = self.client.create_collection(
                        name=self.collection_name,
                        embedding_function=self.embedding_function
                    )
                    logger.info(f"Created new collection '{self.collection_name}' with 384-dimensional embeddings")
                    return collection
                except Exception as del_e:
                    logger.error(f"Failed to delete/recreate incompatible collection: {del_e}")
                    raise Exception(f"Cannot continue with incompatible vector database. Please manually delete the data/vectordb directory and restart.")
            
            # If the collection doesn't exist or there's another non-dimension error, create a new one
            logger.info(f"Creating new collection '{self.collection_name}'")
            try:
                collection = self.client.create_collection(
                    name=self.collection_name,
                    embedding_function=self.embedding_function
                )
                logger.info(f"Created new collection '{self.collection_name}'")
                return collection
            except Exception as create_e:
                logger.error(f"Error creating collection: {create_e}")
                raise
    
    async def add_document(
        self,
        text: str,
        metadata: Optional[Dict[str, Any]] = None,
        document_id: Optional[str] = None
    ) -> str:
        """
        Add a document to the vector store.
        
        Args:
            text: Text of the document
            metadata: Optional metadata to associate with the document
            document_id: Optional ID for the document, generated if not provided
            
        Returns:
            ID of the added document
        """
        # Generate document ID if not provided
        if document_id is None:
            document_id = str(uuid.uuid4())
        
        # Add document to collection
        collection = self._get_or_create_collection()
        
        try:
            logger.info(f"Adding document to vector store: id={document_id}, length={len(text)}, metadata={metadata}")
            
            # Add the document
            collection.add(
                documents=[text],
                metadatas=[metadata or {}],
                ids=[document_id]
            )
            
            logger.info(f"Successfully added document to vector store: {document_id}")
            return document_id
        except Exception as e:
            logger.error(f"Error adding document to vector store: {str(e)}")
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
            filter_metadata: Optional metadata filter
            limit: Maximum number of results to return
            
        Returns:
            List of documents with their text, metadata, and distance
        """
        collection = self._get_or_create_collection()
        
        try:
            logger.info(f"Querying vector store: query='{query_text[:50]}...', filter={filter_metadata}, limit={limit}")
            
            # Query the collection
            results = collection.query(
                query_texts=[query_text],
                n_results=limit,
                where=filter_metadata
            )
            
            # Format the results
            documents = []
            if results and results.get("documents"):
                docs = results["documents"][0]
                metadatas = results["metadatas"][0]
                distances = results["distances"][0]
                ids = results["ids"][0]
                
                for i, (doc, metadata, distance, doc_id) in enumerate(zip(docs, metadatas, distances, ids)):
                    documents.append({
                        "id": doc_id,
                        "text": doc,
                        "metadata": metadata,
                        "distance": distance
                    })
            
            logger.info(f"Vector store query returned {len(documents)} results")
            
            return documents
        except Exception as e:
            logger.error(f"Error querying vector store: {str(e)}")
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