"""
Simple script to test if messages are being added to the vector database and can be retrieved.
"""
import asyncio
from dotenv import load_dotenv
from brainy.core.memory_manager.vector_store import get_vector_store
from brainy.utils.logging import get_logger

# Load environment variables
load_dotenv()

# Initialize logger
logger = get_logger(__name__)

async def main():
    # Get vector store instance
    print(f"\n=== Testing Vector Database Write and Read ===")
    vector_store = get_vector_store(collection_name="messages")
    
    # Test message data
    test_text = "My name is Nazar and I like elephants"
    test_metadata = {
        "message_id": "test123",
        "user_id": "test_user",
        "role": "user",
        "conversation_id": "telegram:test_user",
        "platform": "telegram",
        "timestamp": "2025-03-19T01:30:00"
    }
    
    # 1. Add the test message
    print(f"\n1. Adding test message to vector database...")
    doc_id = await vector_store.add_document(
        text=test_text,
        metadata=test_metadata,
        document_id="test123"
    )
    print(f"   → Added document with ID: {doc_id}")
    
    # 2. Query for the message with exact match
    print(f"\n2. Querying for exact match...")
    results = vector_store.query(
        query_text="My name is Nazar",
        limit=5
    )
    print(f"   → Found {len(results)} results for exact query")
    for i, result in enumerate(results):
        print(f"     Result {i+1}: {result['text']}")
        print(f"     Distance: {result['distance']:.4f}")
    
    # 3. Query with a semantic match
    print(f"\n3. Querying for semantic match...")
    results = vector_store.query(
        query_text="Who is Nazar?",
        limit=5
    )
    print(f"   → Found {len(results)} results for semantic query")
    for i, result in enumerate(results):
        print(f"     Result {i+1}: {result['text']}")
        print(f"     Distance: {result['distance']:.4f}")
    
    # 4. Query with conversation filter
    print(f"\n4. Querying with conversation filter...")
    results = vector_store.query(
        query_text="Who is Nazar?",
        filter_metadata={"conversation_id": "telegram:test_user"},
        limit=5
    )
    print(f"   → Found {len(results)} results with conversation filter")
    
    # 5. Clean up test data
    print(f"\n5. Cleaning up test data...")
    success = vector_store.delete_document("test123")
    print(f"   → {'Successfully deleted' if success else 'Failed to delete'} test document")
    
    print(f"\n=== Test Completed ===\n")

if __name__ == "__main__":
    asyncio.run(main()) 