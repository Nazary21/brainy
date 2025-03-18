"""
Reset Vector Database Script

This script:
1. Backs up the existing vector database
2. Creates a new empty database for 384-dimensional embeddings
3. Ensures the RAG system is properly initialized with the new dimensions
"""
import os
import shutil
import logging
from datetime import datetime
from pathlib import Path

# Configure logging
logging.basicConfig(level=logging.INFO, 
                   format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def backup_vector_database():
    """Backup the existing vector database."""
    from brainy.config import settings
    
    # Get the vector store path
    vector_db_path = settings.VECTOR_DB_PATH
    if not os.path.isabs(vector_db_path):
        vector_db_path = os.path.abspath(vector_db_path)
    
    # Check if the directory exists
    if not os.path.exists(vector_db_path):
        logger.info(f"No existing vector database found at {vector_db_path}")
        return False
    
    # Create backup directory name with timestamp
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_path = f"{vector_db_path}_backup_{timestamp}"
    
    # Backup the directory
    try:
        logger.info(f"Backing up vector database from {vector_db_path} to {backup_path}")
        shutil.copytree(vector_db_path, backup_path)
        logger.info(f"Successfully backed up vector database to {backup_path}")
        return True
    except Exception as e:
        logger.error(f"Failed to backup vector database: {e}")
        return False

def delete_vector_database():
    """Delete the existing vector database."""
    from brainy.config import settings
    
    # Get the vector store path
    vector_db_path = settings.VECTOR_DB_PATH
    if not os.path.isabs(vector_db_path):
        vector_db_path = os.path.abspath(vector_db_path)
    
    # Check if the directory exists
    if not os.path.exists(vector_db_path):
        logger.info(f"No vector database to delete at {vector_db_path}")
        return True
    
    # Delete the directory
    try:
        logger.info(f"Deleting vector database at {vector_db_path}")
        shutil.rmtree(vector_db_path)
        logger.info(f"Successfully deleted vector database")
        return True
    except Exception as e:
        logger.error(f"Failed to delete vector database: {e}")
        return False

def create_new_database():
    """Create a new vector database with 384-dimensional embeddings."""
    # Import after potential deletion to ensure fresh state
    from brainy.core.memory_manager.vector_store import get_vector_store
    
    try:
        logger.info("Initializing new vector store with 384-dimensional embeddings")
        vector_store = get_vector_store("messages")
        logger.info(f"Successfully created new vector store at {vector_store.db_path}")
        
        # Test adding a document to confirm functionality
        test_id = "test_document"
        text = "This is a test document to verify 384-dimensional embeddings"
        metadata = {"test": True}
        
        import asyncio
        document_id = asyncio.run(vector_store.add_document(text=text, metadata=metadata, document_id=test_id))
        logger.info(f"Successfully added test document with ID: {document_id}")
        
        # Test querying to confirm functionality
        results = vector_store.query(query_text="test verification", limit=1)
        logger.info(f"Successfully queried vector store, found {len(results)} results")
        
        # Delete the test document
        vector_store.delete_document(test_id)
        logger.info("Successfully deleted test document")
        
        return True
    except Exception as e:
        logger.error(f"Failed to create new vector database: {e}")
        return False

def main():
    """Execute the vector database reset process."""
    logger.info("=" * 50)
    logger.info("Starting Vector Database Reset")
    logger.info("=" * 50)
    
    # Backup existing database
    if backup_vector_database():
        logger.info("✓ Backup completed successfully")
    else:
        logger.warning("⚠ Backup incomplete or not needed")
    
    # Delete existing database
    if delete_vector_database():
        logger.info("✓ Database deletion completed successfully")
    else:
        logger.error("✗ Failed to delete existing database")
        logger.error("Cannot continue. Please manually delete the vector database directory.")
        return
    
    # Create new database
    if create_new_database():
        logger.info("✓ Successfully created new 384-dimensional vector database")
    else:
        logger.error("✗ Failed to create new vector database")
        return
    
    logger.info("=" * 50)
    logger.info("Vector Database Reset Complete")
    logger.info("Your system is now configured to use 384-dimensional embeddings for RAG")
    logger.info("=" * 50)

if __name__ == "__main__":
    main() 