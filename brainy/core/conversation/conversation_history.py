"""
Conversation history for Brainy.

This module provides storage and retrieval of conversation history.
"""
import sys
from typing import List, Dict, Any, Optional
import uuid

from brainy.core.memory_manager import ConversationMessage, MessageRole

# Add custom debug logging if available
try:
    sys.path.append(".")  # Add project root to path
    import debug_logging
    debug_log = True
except ImportError:
    debug_log = False


class ConversationHistory:
    """
    Manages conversation history.
    
    This class:
    - Stores messages in memory (for now)
    - Retrieves conversation history
    - Will eventually support persistent storage
    """
    
    def __init__(self):
        """Initialize the conversation history manager."""
        # In-memory storage of conversations
        self._conversations: Dict[str, List[ConversationMessage]] = {}
        
        if debug_log:
            debug_logging.log_conversation("Conversation history initialized")
    
    async def add_message(self, conversation_id: str, message: ConversationMessage) -> None:
        """
        Add a message to the conversation history.
        
        Args:
            conversation_id: ID of the conversation
            message: Message to add
        """
        if conversation_id not in self._conversations:
            self._conversations[conversation_id] = []
            
        self._conversations[conversation_id].append(message)
        
        if debug_log:
            debug_logging.log_conversation(f"Added message to conversation {conversation_id}")
    
    async def get_messages(self, conversation_id: str, limit: Optional[int] = None) -> List[ConversationMessage]:
        """
        Get messages for a conversation.
        
        Args:
            conversation_id: ID of the conversation
            limit: Optional maximum number of messages to retrieve
            
        Returns:
            List of messages in the conversation
        """
        if conversation_id not in self._conversations:
            if debug_log:
                debug_logging.log_conversation(f"No messages found for conversation {conversation_id}")
            return []
        
        messages = self._conversations[conversation_id]
        
        if limit is not None:
            messages = messages[-limit:]
            
        if debug_log:
            debug_logging.log_conversation(f"Retrieved {len(messages)} messages from conversation {conversation_id}")
            
        return messages
    
    async def clear_conversation(self, conversation_id: str) -> None:
        """
        Clear the history for a conversation.
        
        Args:
            conversation_id: ID of the conversation
        """
        if conversation_id in self._conversations:
            self._conversations[conversation_id] = []
            
            if debug_log:
                debug_logging.log_conversation(f"Cleared history for conversation {conversation_id}")
    
    async def delete_conversation(self, conversation_id: str) -> None:
        """
        Delete a conversation completely.
        
        Args:
            conversation_id: ID of the conversation
        """
        if conversation_id in self._conversations:
            del self._conversations[conversation_id]
            
            if debug_log:
                debug_logging.log_conversation(f"Deleted conversation {conversation_id}")
                
    async def get_conversation_ids(self) -> List[str]:
        """
        Get all conversation IDs.
        
        Returns:
            List of conversation IDs
        """
        return list(self._conversations.keys()) 