"""
Conversation handler for Brainy.

This module handles the flow of conversations between users and the bot.
"""
from typing import Dict, Optional, Any, List
import asyncio
import sys

from brainy.utils.logging import get_logger
from brainy.core.memory_manager.memory_manager import ConversationMessage, MemoryManager, get_memory_manager
from brainy.core.character.character import Character, CharacterManager, get_character_manager
from brainy.adapters.ai_providers import get_default_provider, Message
from brainy.core.modules import get_module_manager
from brainy.config import settings
from brainy.core.ai_provider.manager import AiProviderManager
from brainy.core.conversation.message_formatter import MessageFormatter
from brainy.core.conversation.conversation_history import ConversationHistory
from brainy.core.character import get_character_manager
from brainy.core.memory_manager import MessageRole
from brainy.providers.ai_provider import AIProvider, get_ai_provider

# Add custom debug logging if available
try:
    sys.path.append(".")  # Add project root to path
    import debug_logging
    debug_log = True
except ImportError:
    debug_log = False

# Initialize logger
logger = get_logger(__name__)

# Debug logging function
def debug(message):
    if debug_log:
        debug_logging.log_conversation(message)
    # Also log at debug level in standard logger
    logger.debug(message)

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
        use_context_search: Optional[bool] = None,
        history_provider: Optional[ConversationHistory] = None,
        ai_provider: Optional[AIProvider] = None,
        message_formatter: Optional[MessageFormatter] = None
    ):
        """
        Initialize a conversation handler.
        
        Args:
            memory_manager: The memory manager to use
            character_manager: The character manager to use
            ai_provider_manager: The AI provider manager to use  
            use_context_search: Whether to use context search. Defaults to settings.USE_CONTEXT_SEARCH
            history_provider: Optional conversation history provider
                If not provided, will use the default conversation history provider
            ai_provider: Optional AI provider
                If not provided, will use the default AI provider
            message_formatter: Optional message formatter
                If not provided, will use the default message formatter
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
        
        # Set up conversation history
        self.history_provider = history_provider or ConversationHistory()
        
        # Set up AI provider
        self.ai_provider = ai_provider or get_ai_provider()
        
        # Set up message formatter
        self.message_formatter = message_formatter or MessageFormatter()
        
        logger.info("Initialized conversation handler")
        if debug_log:
            debug("Conversation handler initialized")
    
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
            logger.debug(f"RAG: Starting semantic search for: '{query_text[:50]}...' in conversation {conversation_id}")
            
            # Search for similar messages in the conversation
            similar_messages = await self._memory_manager.search_similar_messages(
                query_text=query_text,
                conversation_id=conversation_id,
                limit=settings.MAX_SIMILAR_MESSAGES
            )
            
            # Log the results
            logger.debug(
                f"RAG: Retrieved {len(similar_messages)} similar messages",
                conversation_id=conversation_id
            )
            
            # Log each retrieved message
            for i, msg in enumerate(similar_messages):
                content_preview = msg.content[:50] + "..." if len(msg.content) > 50 else msg.content
                logger.debug(f"RAG: Retrieved message {i+1}: {content_preview}")
            
            return similar_messages
        except Exception as e:
            logger.error(f"Error retrieving relevant context: {e}")
            return []
    
    async def process_user_message(
        self,
        user_id: str,
        platform: str,
        message_text: str,
        conversation_id: Optional[str] = None,
        context: Optional[Dict[str, Any]] = None
    ) -> str:
        """
        Process a user message and return an assistant response.
        
        Args:
            user_id: User ID
            platform: Platform ID (e.g., 'telegram', 'slack')
            message_text: Text of the user message
            conversation_id: Optional conversation ID
                If not provided, will be generated/retrieved automatically
            context: Optional context for the message
                Can include any data relevant to the conversation
        
        Returns:
            Assistant response text
        """
        debug(f"Processing user message from user {user_id} on platform {platform}")
        debug(f"User message: '{message_text}'")
        
        try:
            # Get the conversation ID if not provided
            if not conversation_id:
                conversation_id = f"{platform}:{user_id}"
            
            debug(f"Using conversation ID: {conversation_id}")
            
            # Get character for this conversation
            character = self._character_manager.get_character_for_conversation(conversation_id)
            debug(f"Using character: {character.name}")
            
            # Create conversation message object
            user_message = ConversationMessage(
                role=MessageRole.USER,
                content=message_text,
                metadata={
                    "user_id": user_id,
                    "platform": platform,
                    "conversation_id": conversation_id,  # Add conversation_id explicitly to metadata
                    **(context or {})
                }
            )
            
            # Add user message to history
            await self.history_provider.add_message(conversation_id, user_message)
            debug(f"Added user message to history for conversation {conversation_id}")
            
            # IMPORTANT: Also add the message to the memory manager for vector storage
            try:
                debug(f"Adding user message to memory manager for vector storage")
                await self._memory_manager.add_message(user_message)
                debug(f"Successfully added user message to memory manager")
            except Exception as e:
                debug(f"Error adding user message to memory manager: {str(e)}")
                logger.error(f"Error adding user message to memory manager: {str(e)}", exc_info=True)
            
            # Get conversation history
            conversation_messages = await self.history_provider.get_messages(conversation_id)
            debug(f"Retrieved {len(conversation_messages)} messages from history")
            
            # Format messages for AI provider
            formatted_messages = self.message_formatter.format_messages(
                messages=conversation_messages,
                character=character
            )
            debug(f"Formatted messages for AI provider, message count: {len(formatted_messages)}")
            
            # Check for provider preferences for this conversation
            provider_type = None
            try:
                # Try to get provider manager module
                from brainy.core.modules.provider_manager import create_provider_manager_module
                provider_manager = create_provider_manager_module()
                # Get preferred provider for this conversation
                provider_type = provider_manager.get_provider_for_conversation(conversation_id)
                debug(f"Using provider '{provider_type}' for conversation {conversation_id}")
            except Exception as e:
                debug(f"Error getting provider preference, using default: {str(e)}")
                logger.warning(f"Error getting provider preference: {str(e)}")
            
            # Get response from AI provider
            debug(f"Sending messages to AI provider")
            try:
                # Use the specified provider type if available
                ai_response = await self._ai_provider_manager.generate_response(
                    formatted_messages,
                    provider_type=provider_type
                )
                debug(f"Received response from AI provider: '{ai_response[:50]}...'")
            except Exception as e:
                logger.error(f"Error generating AI response: {str(e)}", exc_info=True)
                if debug_log:
                    debug_logging.log_error("CONVERSATION", f"Error generating AI response: {str(e)}", exc_info=True)
                ai_response = "I'm sorry, I encountered an error processing your message. Please try again."
            
            # Create assistant message
            assistant_message = ConversationMessage(
                role=MessageRole.ASSISTANT,
                content=ai_response,
                metadata={
                    "user_id": user_id,
                    "platform": platform,
                    "conversation_id": conversation_id,  # Add conversation_id explicitly to metadata
                    "character_name": character.name,
                    "character_id": character.character_id
                }
            )
            
            # Add assistant message to history
            await self.history_provider.add_message(conversation_id, assistant_message)
            debug(f"Added assistant response to history for conversation {conversation_id}")
            
            # IMPORTANT: Also add the assistant message to the memory manager for vector storage
            try:
                debug(f"Adding assistant message to memory manager for vector storage")
                await self._memory_manager.add_message(assistant_message)
                debug(f"Successfully added assistant message to memory manager")
            except Exception as e:
                debug(f"Error adding assistant message to memory manager: {str(e)}")
                logger.error(f"Error adding assistant message to memory manager: {str(e)}", exc_info=True)
            
            return ai_response
        except Exception as e:
            error_msg = f"Error processing user message: {str(e)}"
            logger.error(error_msg, exc_info=True)
            if debug_log:
                debug_logging.log_error("CONVERSATION", error_msg, exc_info=True)
            return f"I'm sorry, I encountered an error: {str(e)}"
    
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
            platform: The platform identifier
            character_id: ID of the character to switch to
            
        Returns:
            The new character if successful, None if character not found
        """
        # Get the conversation ID
        conversation_id = f"{platform}:{user_id}"
        
        # Get the character
        character = self._character_manager.get_character(character_id)
        if not character:
            return None
        
        # Get the session
        session = await self._get_or_create_user_session(user_id, platform)
        
        # Update the session with the new character
        session["character_id"] = character.character_id
        session["character"] = character
        
        # Save the character preference for this conversation
        self._character_manager._conversation_preferences[conversation_id] = character.character_id
        self._character_manager._save_conversation_preferences()
        
        # Add system message for the new character
        await self._add_system_message(conversation_id, user_id, platform, character)
        
        logger.info(f"Changed character for user {user_id} to '{character.name}'")
        
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