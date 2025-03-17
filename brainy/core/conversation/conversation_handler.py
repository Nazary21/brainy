"""
Conversation handler for Brainy.

This module handles the flow of conversations between users and the bot.
"""
from typing import Dict, Optional, Any, List
import asyncio

from brainy.utils.logging import get_logger
from brainy.core.memory_manager.memory_manager import ConversationMessage, MemoryManager, get_memory_manager
from brainy.core.character.character import Character, CharacterManager, get_character_manager
from brainy.adapters.ai_providers import get_default_provider, Message
from brainy.core.modules import get_module_manager
from brainy.config import settings
from brainy.core.ai_provider.manager import AiProviderManager

# Initialize logger
logger = get_logger(__name__)


class ConversationHandler:
    """
    Handler for managing conversations between users and the bot.
    
    This class coordinates the different components of the bot, including:
    - Character management
    - Memory management
    - AI provider interaction
    - Message processing
    - Module system
    
    It serves as the central coordinator for the chat flow.
    """
    
    def __init__(
        self,
        memory_manager: MemoryManager,
        character_manager: CharacterManager,
        ai_provider_manager: AiProviderManager,
        use_context_search: Optional[bool] = None
    ):
        """
        Initialize a conversation handler.
        
        Args:
            memory_manager: The memory manager to use
            character_manager: The character manager to use
            ai_provider_manager: The AI provider manager to use  
            use_context_search: Whether to use context search. Defaults to settings.USE_CONTEXT_SEARCH
        """
        # Initialize components
        self._memory_manager = memory_manager
        self._character_manager = character_manager
        self._ai_provider_manager = ai_provider_manager
        self._module_manager = get_module_manager()
        
        # Active conversation sessions by user ID
        self._active_sessions: Dict[str, Dict[str, Any]] = {}
        
        # Initialize settings
        self._max_context_length = settings.MAX_CONTEXT_LENGTH
        self._max_similar_messages = settings.MAX_SIMILAR_MESSAGES
        
        # Use context search
        self._use_context_search = use_context_search if use_context_search is not None else settings.USE_CONTEXT_SEARCH
        
        logger.info("Initialized conversation handler")
    
    async def _get_or_create_user_session(
        self,
        user_id: str,
        platform: str
    ) -> Dict[str, Any]:
        """
        Get or create a session for a user.
        
        Args:
            user_id: ID of the user
            platform: Platform the user is interacting on
            
        Returns:
            The user session
        """
        # Check if the user already has an active session
        if user_id in self._active_sessions:
            return self._active_sessions[user_id]
        
        # Get or create a conversation for the user
        conversation_id = await self._memory_manager.get_or_create_conversation(user_id, platform)
        
        # Get the default character for new conversations
        character = self._character_manager.get_default_character()
        
        # Create a new session
        session = {
            "user_id": user_id,
            "platform": platform,
            "conversation_id": conversation_id,
            "character_id": character.character_id,
            "character": character,
            "last_activity": asyncio.get_event_loop().time()
        }
        
        # Store the session
        self._active_sessions[user_id] = session
        
        logger.debug(f"Created new session for user {user_id} on {platform}")
        
        return session
    
    async def _update_session_activity(self, user_id: str) -> None:
        """
        Update the last activity timestamp for a user session.
        
        Args:
            user_id: ID of the user
        """
        if user_id in self._active_sessions:
            self._active_sessions[user_id]["last_activity"] = asyncio.get_event_loop().time()
    
    async def _add_system_message(
        self,
        conversation_id: str,
        user_id: str,
        platform: str,
        character: Character
    ) -> None:
        """
        Add the system message for a character to a conversation.
        
        Args:
            conversation_id: ID of the conversation
            user_id: ID of the user
            platform: Platform of the conversation
            character: Character to use for the system message
        """
        # Create the system message
        system_message = ConversationMessage(
            user_id=user_id,
            role="system",
            content=character.system_prompt,
            conversation_id=conversation_id,
            platform=platform
        )
        
        # Add the message to the conversation
        await self._memory_manager.add_message(system_message)
    
    async def _retrieve_relevant_context(
        self,
        query_text: str,
        conversation_id: str
    ) -> List[ConversationMessage]:
        """
        Retrieve relevant messages from the conversation history.
        
        Args:
            query_text: The text to find relevant messages for
            conversation_id: The ID of the conversation to search in
            
        Returns:
            List of relevant messages
        """
        # Skip if context search is disabled
        if not self._use_context_search:
            logger.debug("Context search is disabled, skipping retrieval")
            return []
        
        try:
            # Search for similar messages in the conversation
            similar_messages = await self._memory_manager.search_similar_messages(
                query_text=query_text,
                conversation_id=conversation_id,
                limit=settings.MAX_SIMILAR_MESSAGES
            )
            
            # Log the results
            logger.debug(
                f"Retrieved {len(similar_messages)} similar messages",
                conversation_id=conversation_id
            )
            
            return similar_messages
        except Exception as e:
            logger.error(f"Error retrieving relevant context: {e}")
            return []
    
    async def process_user_message(
        self,
        user_id: str,
        platform: str,
        message_text: str,
        metadata: Optional[Dict[str, Any]] = None,
        use_context_search: Optional[bool] = None
    ) -> str:
        """
        Process a message from a user and generate a response.
        
        Args:
            user_id: ID of the user
            platform: Platform the user is interacting on
            message_text: Text of the user's message
            metadata: Optional additional metadata for the message
            use_context_search: Whether to use vector search for context retrieval.
                If None, will use the value from settings.
            
        Returns:
            The bot's response text
        """
        # Get or create a session for the user
        session = await self._get_or_create_user_session(user_id, platform)
        
        # Update the last activity timestamp
        await self._update_session_activity(user_id)
        
        conversation_id = session["conversation_id"]
        character = session["character"]
        
        # Determine whether to use context search
        if use_context_search is None:
            use_context_search = settings.USE_CONTEXT_SEARCH
        
        # Create the user message
        user_message = ConversationMessage(
            user_id=user_id,
            role="user",
            content=message_text,
            conversation_id=conversation_id,
            platform=platform
        )
        
        # Add the user message to the conversation
        await self._memory_manager.add_message(user_message)
        
        # Check if this is a command or matches a module
        # First, check if the message is a command
        if self._module_manager.is_command(message_text):
            # Process the command with the module system
            module_response = await self._module_manager.process_command(user_message)
            
            if module_response is not None:
                # Create an assistant message with the module response
                assistant_message = ConversationMessage(
                    user_id=user_id,
                    role="assistant",
                    content=module_response,
                    conversation_id=conversation_id,
                    platform=platform
                )
                
                # Add the assistant message to the conversation
                await self._memory_manager.add_message(assistant_message)
                
                return module_response
        else:
            # Check if the message matches any module patterns
            module = await self._module_manager.find_matching_module(user_message)
            if module:
                # Process the message with the module
                context = {
                    "user_id": user_id,
                    "platform": platform,
                    "conversation_id": conversation_id,
                    "character": character
                }
                
                module_response = await module.process_message(user_message, context)
                
                if module_response is not None:
                    # Create an assistant message with the module response
                    assistant_message = ConversationMessage(
                        user_id=user_id,
                        role="assistant",
                        content=module_response,
                        conversation_id=conversation_id,
                        platform=platform
                    )
                    
                    # Add the assistant message to the conversation
                    await self._memory_manager.add_message(assistant_message)
                    
                    return module_response
        
        # If no module handled the message, process it with the AI provider
        # Get the conversation history, including the new message
        messages = await self._memory_manager.get_conversation_history(
            conversation_id, 
            limit=self._max_context_length
        )
        
        # Check if we need to add a system message
        if not any(msg.role == "system" for msg in messages):
            await self._add_system_message(conversation_id, user_id, platform, character)
            # Get the updated messages
            messages = await self._memory_manager.get_conversation_history(
                conversation_id, 
                limit=self._max_context_length
            )
        
        # Convert messages to AI messages
        ai_messages = [msg.to_ai_message() for msg in messages]
        
        # Retrieve relevant context if enabled
        if use_context_search:
            try:
                # Get relevant context messages
                context_messages = await self._retrieve_relevant_context(message_text, conversation_id)
                
                # If we have context messages, add a system message explaining the context
                if context_messages:
                    # Format the context messages
                    context_text = "Here are some relevant previous interactions that may help with your response:\n\n"
                    
                    for i, msg in enumerate(context_messages):
                        # Format the message with role and content
                        context_text += f"{i+1}. {msg.role.capitalize()}: {msg.content}\n\n"
                    
                    # Add a context message at the beginning, after the system message
                    context_message = Message(
                        role="system",
                        content=context_text
                    )
                    
                    # Insert the context message after the system message
                    system_index = next((i for i, msg in enumerate(ai_messages) if msg.role == "system"), 0)
                    ai_messages.insert(system_index + 1, context_message)
                    
                    logger.debug(f"Added context from {len(context_messages)} previous messages")
            except Exception as e:
                logger.error(f"Error adding context from previous messages: {e}")
        
        # Generate a response using the AI provider
        try:
            response_content = await self._ai_provider_manager.generate_response(ai_messages)
            logger.debug(f"Generated response", user_id=user_id, platform=platform)
        except Exception as e:
            logger.error(f"Error generating response: {e}", user_id=user_id, platform=platform)
            response_content = "I'm sorry, I'm having trouble responding right now. Please try again later."
        
        # Create the assistant message
        assistant_message = ConversationMessage(
            user_id=user_id,
            role="assistant",
            content=response_content,
            conversation_id=conversation_id,
            platform=platform
        )
        
        # Add the assistant message to the conversation
        await self._memory_manager.add_message(assistant_message)
        
        return response_content
    
    async def change_character(
        self,
        user_id: str,
        platform: str,
        character_id: str
    ) -> Optional[Character]:
        """
        Change the character for a user's conversation.
        
        Args:
            user_id: ID of the user
            platform: Platform the user is interacting on
            character_id: ID of the character to change to
            
        Returns:
            The new character, or None if not found
        """
        # Get the character
        character = self._character_manager.get_character(character_id)
        
        if character is None:
            logger.warning(f"Character '{character_id}' not found", user_id=user_id, platform=platform)
            return None
        
        # Get or create a session for the user
        session = await self._get_or_create_user_session(user_id, platform)
        
        # Update the character in the session
        session["character_id"] = character.character_id
        session["character"] = character
        
        # Update the last activity timestamp
        await self._update_session_activity(user_id)
        
        logger.info(f"Changed character to '{character.name}' for user {user_id}", user_id=user_id, platform=platform)
        
        return character
    
    async def clear_conversation(
        self,
        user_id: str,
        platform: str
    ) -> bool:
        """
        Clear the conversation history for a user.
        
        Args:
            user_id: ID of the user
            platform: Platform the user is interacting on
            
        Returns:
            True if successful
        """
        # Get or create a session for the user
        session = await self._get_or_create_user_session(user_id, platform)
        
        conversation_id = session["conversation_id"]
        character = session["character"]
        
        # Clear the conversation
        await self._memory_manager.clear_conversation(conversation_id)
        
        # Add the system message for the current character
        await self._add_system_message(conversation_id, user_id, platform, character)
        
        # Update the last activity timestamp
        await self._update_session_activity(user_id)
        
        logger.info(f"Cleared conversation for user {user_id}", user_id=user_id, platform=platform)
        
        return True


# Singleton instance
_conversation_handler: Optional[ConversationHandler] = None


def get_conversation_handler() -> ConversationHandler:
    """
    Get the conversation handler instance.
    
    Returns:
        The conversation handler instance
    """
    global _conversation_handler
    if _conversation_handler is None:
        # Get the dependencies
        memory_manager = get_memory_manager()
        character_manager = get_character_manager()
        from brainy.core.ai_provider import get_ai_provider_manager
        ai_provider_manager = get_ai_provider_manager()
        
        # Create the conversation handler
        _conversation_handler = ConversationHandler(
            memory_manager=memory_manager,
            character_manager=character_manager,
            ai_provider_manager=ai_provider_manager
        )
    
    return _conversation_handler 