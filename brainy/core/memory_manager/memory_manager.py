"""
Memory manager for Brainy.
"""
from typing import Dict, List, Optional, Any
from datetime import datetime
import uuid
import json

from brainy.utils.logging import get_logger
from brainy.adapters.ai_providers.base import Message
from brainy.core.memory_manager.vector_store import get_vector_store

# Initialize logger
logger = get_logger(__name__)


class ConversationMessage:
    """Representation of a message in a conversation."""
    
    def __init__(
        self,
        user_id: str,
        role: str,
        content: str,
        conversation_id: str,
        platform: str,
        message_id: Optional[str] = None,
        timestamp: Optional[datetime] = None,
        vector_id: Optional[str] = None
    ):
        """
        Initialize a conversation message.
        
        Args:
            user_id: ID of the user who sent or received the message
            role: Role of the message sender (user, assistant, system)
            content: Content of the message
            conversation_id: ID of the conversation
            platform: Platform where the message was sent
            message_id: Optional ID for the message. Will be generated if not provided.
            timestamp: Optional timestamp for the message. Current time will be used if not provided.
            vector_id: Optional ID for the message in the vector store.
        """
        self.user_id = user_id
        self.role = role
        self.content = content
        self.conversation_id = conversation_id
        self.platform = platform
        self.message_id = message_id or str(uuid.uuid4())
        self.timestamp = timestamp or datetime.now()
        self.vector_id = vector_id
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert message to dictionary representation."""
        return {
            "message_id": self.message_id,
            "user_id": self.user_id,
            "role": self.role,
            "content": self.content,
            "conversation_id": self.conversation_id,
            "platform": self.platform,
            "timestamp": self.timestamp.isoformat(),
            "vector_id": self.vector_id
        }
    
    def to_ai_message(self) -> Message:
        """Convert to AI provider message format."""
        return Message(role=self.role, content=self.content)
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'ConversationMessage':
        """Create a message from dictionary data."""
        timestamp = data.get("timestamp")
        if timestamp and isinstance(timestamp, str):
            timestamp = datetime.fromisoformat(timestamp)
        
        return cls(
            user_id=data["user_id"],
            role=data["role"],
            content=data["content"],
            conversation_id=data["conversation_id"],
            platform=data["platform"],
            message_id=data["message_id"],
            timestamp=timestamp,
            vector_id=data.get("vector_id")
        )


class MemoryManager:
    """
    Memory manager for storing and retrieving conversation history.
    
    This implementation uses an in-memory store for recent messages and
    ChromaDB for vector search capabilities.
    """
    
    def __init__(self):
        """Initialize the memory manager."""
        # In-memory storage of messages by conversation ID
        self._messages: Dict[str, List[ConversationMessage]] = {}
        
        # Mapping of user IDs to conversation IDs
        self._user_conversations: Dict[str, List[str]] = {}
        
        # Get the vector store
        self._vector_store = get_vector_store("messages")
        
        logger.info("Initialized memory manager with vector store")
    
    async def add_message(self, message: ConversationMessage) -> str:
        """
        Add a message to the conversation history.
        
        Args:
            message: The message to add
            
        Returns:
            The ID of the added message
        """
        # Initialize conversation list if it doesn't exist
        if message.conversation_id not in self._messages:
            self._messages[message.conversation_id] = []
        
        # Add the message to the in-memory store
        self._messages[message.conversation_id].append(message)
        
        # Update user conversations mapping
        if message.user_id not in self._user_conversations:
            self._user_conversations[message.user_id] = []
        
        if message.conversation_id not in self._user_conversations[message.user_id]:
            self._user_conversations[message.user_id].append(message.conversation_id)
        
        # Add the message to the vector store if it's a user or assistant message
        # We don't store system messages in the vector store
        if message.role in ["user", "assistant"]:
            try:
                # Prepare metadata for the vector store
                metadata = {
                    "message_id": message.message_id,
                    "user_id": message.user_id,
                    "role": message.role,
                    "conversation_id": message.conversation_id,
                    "platform": message.platform,
                    "timestamp": message.timestamp.isoformat()
                }
                
                # Add the message to the vector store
                vector_id = await self._vector_store.add_document(
                    text=message.content,
                    metadata=metadata,
                    document_id=message.message_id
                )
                
                # Update the message with the vector ID
                message.vector_id = vector_id
                
                logger.debug(
                    f"Added message to vector store",
                    message_id=message.message_id,
                    vector_id=vector_id
                )
            except Exception as e:
                logger.error(f"Error adding message to vector store: {e}")
        
        logger.debug(
            f"Added message to conversation",
            user_id=message.user_id,
            conversation_id=message.conversation_id,
            role=message.role,
            message_id=message.message_id
        )
        
        return message.message_id
    
    async def get_conversation_history(
        self,
        conversation_id: str,
        limit: Optional[int] = None
    ) -> List[ConversationMessage]:
        """
        Get the conversation history for a conversation.
        
        Args:
            conversation_id: ID of the conversation
            limit: Optional limit on the number of messages to return (most recent)
            
        Returns:
            List of messages in the conversation
        """
        if conversation_id not in self._messages:
            return []
        
        # Get all messages for the conversation
        messages = self._messages[conversation_id]
        
        # Sort by timestamp (newest last)
        messages = sorted(messages, key=lambda m: m.timestamp)
        
        # Apply limit if specified
        if limit is not None:
            messages = messages[-limit:]
        
        return messages
    
    async def get_user_conversation_ids(self, user_id: str) -> List[str]:
        """
        Get the conversation IDs for a user.
        
        Args:
            user_id: ID of the user
            
        Returns:
            List of conversation IDs for the user
        """
        return self._user_conversations.get(user_id, [])
    
    async def clear_conversation(self, conversation_id: str) -> None:
        """
        Clear the conversation history for a conversation.
        
        Args:
            conversation_id: ID of the conversation to clear
        """
        if conversation_id in self._messages:
            # Get the messages to remove from the vector store
            messages = self._messages[conversation_id]
            
            # Remove messages from the vector store
            try:
                # Delete messages from the vector store
                self._vector_store.delete_by_metadata({"conversation_id": conversation_id})
                logger.debug(f"Deleted messages from vector store for conversation {conversation_id}")
            except Exception as e:
                logger.error(f"Error deleting messages from vector store: {e}")
            
            # Clear the in-memory messages
            self._messages[conversation_id] = []
            
            logger.info(f"Cleared conversation {conversation_id}")
    
    async def get_or_create_conversation(
        self,
        user_id: str,
        platform: str
    ) -> str:
        """
        Get or create a conversation for a user and platform.
        
        Args:
            user_id: ID of the user
            platform: Platform of the conversation
            
        Returns:
            The conversation ID
        """
        # For now, we just create one conversation per user-platform pair
        # In the future, we might want to support multiple conversations
        
        # Check if the user already has a conversation
        user_conversations = await self.get_user_conversation_ids(user_id)
        if user_conversations:
            # For simplicity, just return the first conversation ID
            return user_conversations[0]
        
        # Create a new conversation ID
        conversation_id = f"{user_id}_{platform}_{uuid.uuid4()}"
        
        # Initialize the conversation
        self._messages[conversation_id] = []
        
        # Update user conversations mapping
        if user_id not in self._user_conversations:
            self._user_conversations[user_id] = []
        
        self._user_conversations[user_id].append(conversation_id)
        
        logger.info(f"Created new conversation {conversation_id} for user {user_id}")
        
        return conversation_id
    
    async def get_messages_as_ai_messages(
        self,
        conversation_id: str,
        limit: Optional[int] = None
    ) -> List[Message]:
        """
        Get the conversation history as AI provider messages.
        
        Args:
            conversation_id: ID of the conversation
            limit: Optional limit on the number of messages to return
            
        Returns:
            List of messages in AI provider format
        """
        messages = await self.get_conversation_history(conversation_id, limit)
        return [message.to_ai_message() for message in messages]
    
    async def search_similar_messages(
        self,
        query_text: str,
        conversation_id: Optional[str] = None,
        limit: int = 5
    ) -> List[ConversationMessage]:
        """
        Search for similar messages using vector similarity.
        
        Args:
            query_text: Text to search for
            conversation_id: Optional conversation ID to limit search to
            limit: Maximum number of results to return
            
        Returns:
            List of similar messages
        """
        try:
            # Prepare metadata filter if conversation_id is provided
            filter_metadata = None
            if conversation_id:
                filter_metadata = {"conversation_id": conversation_id}
            
            # Search the vector store
            results = self._vector_store.query(
                query_text=query_text,
                filter_metadata=filter_metadata,
                limit=limit
            )
            
            # Convert results to ConversationMessage objects
            messages = []
            for result in results:
                metadata = result.get("metadata", {})
                
                # Create a message from the metadata
                message = ConversationMessage(
                    user_id=metadata.get("user_id", ""),
                    role=metadata.get("role", ""),
                    content=result.get("text", ""),
                    conversation_id=metadata.get("conversation_id", ""),
                    platform=metadata.get("platform", ""),
                    message_id=metadata.get("message_id", ""),
                    vector_id=result.get("id")
                )
                
                # Parse timestamp if available
                timestamp_str = metadata.get("timestamp")
                if timestamp_str:
                    try:
                        message.timestamp = datetime.fromisoformat(timestamp_str)
                    except ValueError:
                        pass
                
                messages.append(message)
            
            logger.debug(f"Search returned {len(messages)} similar messages")
            
            return messages
        except Exception as e:
            logger.error(f"Error searching for similar messages: {e}")
            return []


# Singleton instance
_memory_manager: Optional[MemoryManager] = None


def get_memory_manager() -> MemoryManager:
    """
    Get the memory manager instance.
    
    Returns:
        The memory manager instance
    """
    global _memory_manager
    if _memory_manager is None:
        _memory_manager = MemoryManager()
    
    return _memory_manager 