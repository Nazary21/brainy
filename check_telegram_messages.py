"""
Script to check if Telegram conversation messages are properly stored in the vector database.
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
    # Your Telegram user ID
    telegram_user_id = "308526396"  # This is the ID from the logs
    conversation_id = f"telegram:{telegram_user_id}"
    
    print(f"\n=== Checking Telegram Messages in Vector Database ===")
    print(f"Vector DB path: {settings.VECTOR_DB_PATH}")
    print(f"Looking for conversation_id: {conversation_id}")
    
    vector_store = get_vector_store(collection_name="messages")
    
    # Search for your messages by conversation ID
    print(f"\n1. Searching for messages with conversation_id={conversation_id}...")
    results = vector_store.query(
        query_text="",  # Empty query to get all messages
        filter_metadata={"conversation_id": conversation_id},
        limit=10
    )
    
    if results:
        print(f"   → Found {len(results)} messages from your Telegram conversation")
        for i, result in enumerate(results):
            print(f"\n   ===== Result {i+1} =====")
            print(f"   Text: {result['text']}")
            print(f"   Distance: {result['distance']:.4f}")
            print(f"   Metadata:")
            for key, value in result['metadata'].items():
                print(f"      - {key}: {value}")
    else:
        print(f"   → No messages found with conversation_id={conversation_id}")
        
        # If no messages found, let's see what conversation IDs exist
        print(f"\n2. Checking all unique conversation IDs in the database...")
        all_results = vector_store.query(
            query_text="",
            limit=100  # Get a large sample
        )
        
        conversation_ids = set()
        for result in all_results:
            conv_id = result['metadata'].get('conversation_id')
            if conv_id:
                conversation_ids.add(conv_id)
        
        if conversation_ids:
            print(f"   → Found {len(conversation_ids)} unique conversation IDs:")
            for i, conv_id in enumerate(conversation_ids):
                print(f"      {i+1}. {conv_id}")
        else:
            print(f"   → No conversation IDs found in the database")
    
    # Search for messages containing "Nazar" 
    print(f"\n3. Searching for messages containing 'Nazar'...")
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
    
    print(f"\n=== Check Completed ===\n")

if __name__ == "__main__":
    asyncio.run(main()) 