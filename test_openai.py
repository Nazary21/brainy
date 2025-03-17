#!/usr/bin/env python
"""
Test script for OpenAI integration without Telegram.

This script tests the full message flow from user input to AI response
using the console instead of Telegram as the interface.
"""
import asyncio
import os
from pathlib import Path
from dotenv import load_dotenv

from brainy.core.character import get_character_manager
from brainy.core.conversation import get_conversation_handler
from brainy.core.memory_manager import ConversationMessage, get_memory_manager
from brainy.adapters.ai_providers import get_default_provider
from brainy.utils.logging import get_logger

# Initialize logger
logger = get_logger(__name__)

# Load environment variables from .env file
load_dotenv()

async def simulate_message(user_id, message_text):
    """Simulate sending a message through the conversation handler."""
    platform = "console"
    
    # Process the message using the conversation handler
    response = await conversation_handler.process_user_message(
        user_id=user_id,
        platform=platform,
        message_text=message_text,
        metadata={"source": "test_script"}
    )
    
    return response

async def display_conversation_history(user_id, conversation_id):
    """Display the conversation history for debugging."""
    print("\n=== Conversation History ===")
    
    # Get the conversation history
    messages = await memory_manager.get_conversation_history(conversation_id)
    
    for msg in messages:
        role_display = f"[{msg.role.upper()}]"
        print(f"{role_display.ljust(10)} {msg.content}")
    
    print("============================\n")

async def main():
    """Run the test script."""
    global conversation_handler, memory_manager
    
    print("=== OpenAI Integration Test ===")
    print("This script tests the AI integration without Telegram.")
    print("Type 'quit', 'exit', or Ctrl+C to exit.")
    print("Type 'history' to view conversation history.")
    print("Type 'clear' to clear conversation history.")
    print("Type 'character <id>' to change character.")
    print("=============================\n")
    
    # Create necessary directories
    data_dir = Path("brainy") / "data"
    data_dir.mkdir(parents=True, exist_ok=True)
    
    # Characters directory
    characters_dir = data_dir / "characters"
    characters_dir.mkdir(parents=True, exist_ok=True)
    
    # Vector DB directory
    vector_db_path = os.getenv("VECTOR_DB_PATH", "./data/vectordb")
    Path(vector_db_path).mkdir(parents=True, exist_ok=True)
    
    # Initialize core components
    memory_manager = get_memory_manager()
    character_manager = get_character_manager()
    conversation_handler = get_conversation_handler()
    
    # Test the OpenAI provider directly
    ai_provider = get_default_provider()
    logger.info(f"Using AI provider: {ai_provider.name} with model: {ai_provider.config.model}")
    
    # Get or create a conversation ID
    user_id = "console_user"
    platform = "console"
    conversation_id = await memory_manager.get_or_create_conversation(user_id, platform)
    
    # Get the default character
    character = character_manager.get_default_character()
    print(f"Using character: {character.name} ({character.character_id})")
    print(f"Description: {character.description}")
    print(f"\n{character.greeting}\n")
    
    # Main interaction loop
    try:
        while True:
            # Get user input
            user_input = input("You: ")
            
            # Check for exit commands
            if user_input.lower() in ["quit", "exit", "q"]:
                print("Exiting...")
                break
            
            # Check for special commands
            if user_input.lower() == "history":
                await display_conversation_history(user_id, conversation_id)
                continue
            
            if user_input.lower() == "clear":
                await conversation_handler.clear_conversation(user_id, platform)
                print("Conversation cleared.")
                continue
            
            if user_input.lower().startswith("character "):
                character_id = user_input.split(" ", 1)[1].strip()
                character = await conversation_handler.change_character(user_id, platform, character_id)
                if character:
                    print(f"Changed character to: {character.name} ({character.character_id})")
                    print(f"Description: {character.description}")
                    if character.greeting:
                        print(f"\n{character.greeting}\n")
                else:
                    print(f"Character '{character_id}' not found.")
                continue
            
            # Process the message
            print("Bot is thinking...")
            try:
                response = await simulate_message(user_id, user_input)
                print(f"Bot: {response}")
            except Exception as e:
                logger.error(f"Error processing message: {e}")
                print(f"Error: {e}")
    
    except KeyboardInterrupt:
        print("\nExiting...")
    
    except Exception as e:
        logger.error(f"Unexpected error: {e}")
        print(f"Unexpected error: {e}")
    
    print("Test completed.")

if __name__ == "__main__":
    asyncio.run(main()) 