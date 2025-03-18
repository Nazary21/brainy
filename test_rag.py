"""
Test script to verify RAG (Retrieval-Augmented Generation) functionality.

This script will:
1. Check if the vector database exists and is accessible
2. Add some test messages to the vector store
3. Perform test queries to verify retrieval
"""
import os
import asyncio
import logging
from datetime import datetime
from dotenv import load_dotenv

# Configure logging
logging.basicConfig(level=logging.INFO, 
                   format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Load environment variables
load_dotenv()

# Import needed components
from brainy.core.memory_manager import get_memory_manager, ConversationMessage, MessageRole
from brainy.core.memory_manager.vector_store import get_vector_store

async def test_vector_store_path():
    """Test if the vector store path exists and is accessible."""
    # Get the vector store path from settings
    from brainy.config import settings
    vector_db_path = settings.VECTOR_DB_PATH
    
    logger.info(f"Vector DB Path: {vector_db_path}")
    absolute_path = os.path.abspath(vector_db_path)
    logger.info(f"Absolute Path: {absolute_path}")
    
    if os.path.exists(absolute_path):
        logger.info(f"✓ Vector DB directory exists")
        
        # List contents
        files = os.listdir(absolute_path)
        logger.info(f"Vector DB contains {len(files)} files/directories:")
        for f in files:
            full_path = os.path.join(absolute_path, f)
            if os.path.isdir(full_path):
                logger.info(f"  - {f}/ (directory)")
            else:
                logger.info(f"  - {f} ({os.path.getsize(full_path)} bytes)")
        
        return True
    else:
        logger.error(f"✗ Vector DB directory does not exist")
        return False

async def test_add_messages():
    """Test adding messages to the vector store."""
    # Get the memory manager
    memory_manager = get_memory_manager()
    
    # Create a test conversation ID
    conversation_id = "test_rag:12345"
    
    # Create and add some test messages
    test_messages = [
        ("user", "I really like lions and other big cats"),
        ("assistant", "Lions are magnificent animals! They're the second-largest big cat after tigers."),
        ("user", "Tell me more about bananas"),
        ("assistant", "Bananas are nutritious fruits rich in potassium. They're technically berries!"),
        ("user", "I prefer dogs over cats because they're more loyal"),
        ("assistant", "Dogs are known for their loyalty and companionship. They've been human companions for thousands of years.")
    ]
    
    logger.info(f"Adding {len(test_messages)} test messages to conversation {conversation_id}")
    
    for i, (role, content) in enumerate(test_messages):
        # Create message
        message = ConversationMessage(
            role=MessageRole(role),
            content=content,
            metadata={
                "user_id": "12345",
                "platform": "test_rag",
                "conversation_id": conversation_id,
                "test_message": True
            }
        )
        
        # Add message to memory manager
        message_id = await memory_manager.add_message(message)
        logger.info(f"Added message {i+1}: {role} - '{content[:30]}...' (ID: {message_id})")
    
    logger.info(f"✓ Successfully added {len(test_messages)} test messages")
    return True

async def test_retrieve_messages():
    """Test retrieving messages from the vector store."""
    # Get the memory manager
    memory_manager = get_memory_manager()
    
    # Test queries
    test_queries = [
        ("lion", "test_rag:12345"),
        ("banana", "test_rag:12345"),
        ("dog", "test_rag:12345")
    ]
    
    for query, conversation_id in test_queries:
        logger.info(f"\nTesting query: '{query}' in conversation {conversation_id}")
        
        # Search for similar messages
        similar_messages = await memory_manager.search_similar_messages(
            query_text=query,
            conversation_id=conversation_id,
            limit=2
        )
        
        if similar_messages:
            logger.info(f"✓ Found {len(similar_messages)} similar messages")
            
            for i, msg in enumerate(similar_messages):
                logger.info(f"  Result {i+1}: {msg.role} - '{msg.content[:50]}...'")
        else:
            logger.warning(f"✗ No similar messages found for query '{query}'")
    
    return True

async def main():
    """Run the RAG test suite."""
    logger.info("=" * 50)
    logger.info("Testing RAG Functionality")
    logger.info("=" * 50)
    
    # Test 1: Check vector store path
    logger.info("\n[TEST 1] Checking Vector Database Path")
    if not await test_vector_store_path():
        logger.error("Vector database directory not found or not accessible. Tests cannot continue.")
        return
    
    # Test 2: Add test messages
    logger.info("\n[TEST 2] Adding Test Messages to Vector Store")
    await test_add_messages()
    
    # Test 3: Retrieve messages
    logger.info("\n[TEST 3] Retrieving Messages from Vector Store")
    await test_retrieve_messages()
    
    logger.info("\n" + "=" * 50)
    logger.info("RAG Tests Completed")
    logger.info("=" * 50)

if __name__ == "__main__":
    asyncio.run(main()) 