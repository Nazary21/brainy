"""
Test script to verify vector store functionality with local 384-dimensional embeddings.

This script adds sample documents to the vector store and performs queries 
to ensure that the vector store is working correctly with 384-dimensional embeddings.
"""
import asyncio
import os
from dotenv import load_dotenv

from brainy.core.memory_manager.vector_store import get_vector_store
from brainy.utils.logging import get_logger

# Load environment variables
load_dotenv()

# Initialize logger
logger = get_logger(__name__)

async def test_vector_store():
    """Test vector store functionality"""
    print("\n=== Testing Vector Store with 384-dimensional embeddings ===\n")
    
    # Get vector store instance
    print("Initializing vector store...")
    vector_store = get_vector_store(collection_name="test_collection")
    
    # Add some sample documents
    print("\nAdding sample documents...")
    documents = [
        "Artificial intelligence is transforming the world in many ways.",
        "Machine learning models can recognize patterns in large datasets.",
        "Natural language processing helps computers understand human language.",
        "Neural networks are inspired by the human brain's structure.",
        "Deep learning has revolutionized computer vision tasks."
    ]
    
    doc_ids = []
    for i, text in enumerate(documents):
        metadata = {"topic": "AI", "index": i}
        doc_id = await vector_store.add_document(text=text, metadata=metadata)
        doc_ids.append(doc_id)
        print(f"Added document {i+1}: {text[:40]}... (ID: {doc_id})")
    
    # Test querying
    print("\nTesting queries...")
    queries = [
        "How is AI changing the world?",
        "Tell me about neural networks",
        "What is machine learning good for?"
    ]
    
    for query in queries:
        print(f"\nQuery: '{query}'")
        results = vector_store.query(query_text=query, limit=2)
        
        print(f"Found {len(results)} results:")
        for i, result in enumerate(results):
            print(f"  {i+1}. {result['text'][:60]}...")
            print(f"     Distance: {result['distance']:.4f}")
            print(f"     Metadata: {result['metadata']}")
    
    # Test document retrieval
    print("\nTesting document retrieval...")
    if doc_ids:
        doc = vector_store.get_document(doc_ids[0])
        print(f"Retrieved document: {doc['text']}")
        print(f"Metadata: {doc['metadata']}")
    
    # Test deletion
    print("\nTesting document deletion...")
    if doc_ids:
        vector_store.delete_document(doc_ids[0])
        print(f"Deleted document with ID: {doc_ids[0]}")
        
        # Verify deletion
        doc = vector_store.get_document(doc_ids[0])
        if doc is None:
            print("Document successfully deleted (not found)")
        else:
            print("Document still exists after deletion attempt")
    
    print("\n=== Vector Store Test Completed ===")

if __name__ == "__main__":
    asyncio.run(test_vector_store()) 