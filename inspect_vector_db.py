"""
Script to inspect the contents of the vector database.
This will show all messages currently stored and search for specific content.
"""
import asyncio
from dotenv import load_dotenv
from brainy.core.memory_manager.vector_store import get_vector_store
from brainy.utils.logging import get_logger
from brainy.config import settings

# Load environment variables
load_dotenv()

# Initialize logger
logger = get_logger(__name__)

async def main():
    # Get vector store instance
    print(f"\n=== Inspecting Vector Database Contents ===")
    print(f"Vector DB path: {settings.VECTOR_DB_PATH}")
    
    vector_store = get_vector_store(collection_name="messages")
    
    # 1. Search for messages containing "Nazar"
    print(f"\n1. Searching for messages containing 'Nazar'...")
    results = vector_store.query(
        query_text="Nazar",
        limit=10
    )
    
    if results:
        print(f"   → Found {len(results)} messages containing 'Nazar'")
        for i, result in enumerate(results):
            print(f"\n   ===== Result {i+1} =====")
            print(f"   Text: {result['text']}")
            print(f"   Distance: {result['distance']:.4f}")
            print(f"   Metadata:")
            for key, value in result['metadata'].items():
                print(f"      - {key}: {value}")
    else:
        print(f"   → No messages found containing 'Nazar'")
    
    # 2. Search for messages containing "name"
    print(f"\n2. Searching for messages containing 'name'...")
    results = vector_store.query(
        query_text="name",
        limit=10
    )
    
    if results:
        print(f"   → Found {len(results)} messages containing 'name'")
        for i, result in enumerate(results):
            print(f"\n   ===== Result {i+1} =====")
            print(f"   Text: {result['text']}")
            print(f"   Distance: {result['distance']:.4f}")
            print(f"   Metadata:")
            for key, value in result['metadata'].items():
                print(f"      - {key}: {value}")
    else:
        print(f"   → No messages found containing 'name'")
    
    # 3. Check for most recent messages
    print(f"\n3. Retrieving most recent messages...")
    results = vector_store.query(
        query_text="",  # Empty query to get most relevant messages
        limit=5
    )
    
    if results:
        print(f"   → Found {len(results)} recent messages")
        for i, result in enumerate(results):
            print(f"\n   ===== Result {i+1} =====")
            print(f"   Text: {result['text']}")
            print(f"   Distance: {result['distance']:.4f}")
            print(f"   Metadata:")
            for key, value in result['metadata'].items():
                print(f"      - {key}: {value}")
    else:
        print(f"   → No messages found")
    
    print(f"\n=== Inspection Completed ===\n")

if __name__ == "__main__":
    asyncio.run(main()) 