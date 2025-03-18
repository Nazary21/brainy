"""
Memory manager for Brainy.

This module handles conversation memory management including storing, retrieving,
and searching conversation history.
"""
import sys
import uuid
from typing import Dict, List, Any, Optional
from datetime import datetime
from enum import Enum

from brainy.utils.logging import get_logger
from brainy.adapters.ai_providers.base import Message
from brainy.core.memory_manager.vector_store import get_vector_store

# Add custom debug logging if available
try:
    sys.path.append(".")  # Add project root to path
    import debug_logging
    debug_log = True
except ImportError:
    debug_log = False

# Initialize logger
logger = get_logger(__name__)


class MessageRole(str, Enum):
    """Enumeration of message roles."""
    USER = "user"
    ASSISTANT = "assistant"
    SYSTEM = "system"


class ConversationMessage:
    """
    Represents a message in a conversation.
    """
    
    def __init__(
        self,
        role: MessageRole,
        content: str,
        metadata: Optional[Dict[str, Any]] = None,
        message_id: Optional[str] = None,
        timestamp: Optional[datetime] = None
    ):
        """
        Initialize a conversation message.
        
        Args:
            role: Role of the message sender (USER, ASSISTANT, SYSTEM)
            content: Content of the message
            metadata: Optional metadata about the message
            message_id: Optional ID for the message, will be generated if not provided
            timestamp: Optional timestamp for the message, will use current time if not provided
        """
        self.role = role
        self.content = content
        self.metadata = metadata or {}
        self.message_id = message_id or str(uuid.uuid4())
        self.timestamp = timestamp or datetime.now()
        
    def to_dict(self) -> Dict[str, Any]:
        """
        Convert the message to a dictionary.
        
        Returns:
            Dictionary representation of the message
        """
        return {
            "role": self.role,
            "content": self.content,
            "metadata": self.metadata,
            "message_id": self.message_id,
            "timestamp": self.timestamp.isoformat()
        }
    
    def to_ai_message(self) -> Message:
        """Convert to AI provider message format."""
        return Message(role=self.role, content=self.content)
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'ConversationMessage':
        """
        Create a message from a dictionary.
        
        Args:
            data: Dictionary representation of the message
            
        Returns:
            ConversationMessage instance
        """
        timestamp = None
        if "timestamp" in data:
            if isinstance(data["timestamp"], str):
                timestamp = datetime.fromisoformat(data["timestamp"])
            elif isinstance(data["timestamp"], datetime):
                timestamp = data["timestamp"]
        
        return cls(
            role=data["role"],
            content=data["content"],
            metadata=data.get("metadata", {}),
            message_id=data.get("message_id"),
            timestamp=timestamp
        )


class MemoryManager:
    """
    Manages conversation memory.
    
    This class is responsible for:
    - Storing conversation messages in memory
    - Retrieving conversation history
    - Searching for similar messages
    """
    
    def __init__(self):
        """Initialize the memory manager."""
        # In-memory storage for now
        self._messages: Dict[str, ConversationMessage] = {}
        self._conversation_messages: Dict[str, List[str]] = {}
        
        # Get the vector store
        self._vector_store = get_vector_store("messages")
        
        if debug_log:
            debug_logging.log_conversation("Memory manager initialized")
        
    async def add_message(self, message: ConversationMessage) -> str:
        """
        Add a message to memory.
        
        Args:
            message: Message to add
            
        Returns:
            ID of the added message
        """
        # Get conversation ID from metadata
        conversation_id = message.metadata.get("conversation_id")
        if not conversation_id:
            # If no conversation ID, use user ID and platform as fallback
            user_id = message.metadata.get("user_id")
            platform = message.metadata.get("platform")
            if user_id and platform:
                conversation_id = f"{platform}:{user_id}"
            else:
                raise ValueError("Message must have either conversation_id or both user_id and platform in metadata")
        
        # Store message
        message_id = message.message_id
        self._messages[message_id] = message
        
        # Add to conversation index
        if conversation_id not in self._conversation_messages:
            self._conversation_messages[conversation_id] = []
        self._conversation_messages[conversation_id].append(message_id)
        
        if debug_log:
            user_id = message.metadata.get("user_id", "unknown")
            debug_logging.log_conversation(f"Added message from user {user_id} to conversation {conversation_id}")
        
        # Add the message to the vector store if it's a user or assistant message
        # We don't store system messages in the vector store
        if message.role in ["user", "assistant"]:
            try:
                # Prepare metadata for the vector store
                metadata = {
                    "message_id": message.message_id,
                    "user_id": message.metadata.get("user_id"),
                    "role": message.role,
                    "conversation_id": conversation_id,
                    "platform": message.metadata.get("platform"),
                    "timestamp": message.timestamp.isoformat()
                }
                
                # Add the message to the vector store
                vector_id = await self._vector_store.add_document(
                    text=message.content,
                    metadata=metadata,
                    document_id=message.message_id
                )
                
                # Update the message with the vector ID
                message.metadata["vector_id"] = vector_id
                
                logger.debug(
                    f"Added message to vector store",
                    message_id=message.message_id,
                    vector_id=vector_id
                )
            except Exception as e:
                logger.error(f"Error adding message to vector store: {e}")
        
        return message_id
    
    async def get_conversation_history(
        self,
        conversation_id: str,
        limit: Optional[int] = None
    ) -> List[ConversationMessage]:
        """
        Get the conversation history for a conversation.
        
        Args:
            conversation_id: ID of the conversation to get history for
            limit: Optional maximum number of messages to retrieve
            
        Returns:
            List of messages in the conversation, ordered by timestamp
        """
        if conversation_id not in self._conversation_messages:
            if debug_log:
                debug_logging.log_conversation(f"No messages found for conversation {conversation_id}")
            return []
        
        message_ids = self._conversation_messages[conversation_id]
        messages = [self._messages[msg_id] for msg_id in message_ids if msg_id in self._messages]
        
        # Sort by timestamp
        messages.sort(key=lambda msg: msg.timestamp)
        
        # Apply limit if specified
        if limit is not None:
            messages = messages[-limit:]
        
        if debug_log:
            debug_logging.log_conversation(f"Retrieved {len(messages)} messages for conversation {conversation_id}")
        
        return messages
    
    async def get_user_conversation_ids(self, user_id: str) -> List[str]:
        """
        Get the conversation IDs for a user.
        
        Args:
            user_id: ID of the user
            
        Returns:
            List of conversation IDs for the user
        """
        return [conv_id for conv_id, user_conversations in self._conversation_messages.items() if user_id in user_conversations]
    
    async def clear_conversation(self, conversation_id: str) -> None:
        """
        Clear the conversation history for a conversation.
        
        Args:
            conversation_id: ID of the conversation to clear
        """
        if conversation_id in self._conversation_messages:
            # Get the messages to remove from the vector store
            messages = self.get_conversation_history(conversation_id)
            
            # Remove messages from the vector store
            try:
                # Delete messages from the vector store
                self._vector_store.delete_by_metadata({"conversation_id": conversation_id})
                logger.debug(f"Deleted messages from vector store for conversation {conversation_id}")
            except Exception as e:
                logger.error(f"Error deleting messages from vector store: {e}")
            
            # Clear the in-memory messages
            self._messages = {}
            self._conversation_messages[conversation_id] = []
            
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
        conversation_id = f"{platform}:{user_id}"
        
        # Initialize the conversation
        self._messages = {}
        self._conversation_messages[conversation_id] = []
        
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
        Search for messages that are semantically similar to the query.
        
        Args:
            query_text: The text to find similar messages for
            conversation_id: Optional ID of conversation to filter by
            limit: Maximum number of results to return
            
        Returns:
            List of similar messages
        """
        try:
            logger.info(f"Vector search: Starting search for '{query_text[:30]}...'")
            
            # Prepare metadata filter if conversation_id is provided
            filter_metadata = None
            if conversation_id:
                filter_metadata = {"conversation_id": conversation_id}
                logger.info(f"Vector search: Filtering by conversation_id: {conversation_id}")
            
            # Check if vector store is initialized
            if not self._vector_store:
                logger.error("Vector search: Vector store not initialized")
                return []
                
            # Log the vector store path
            logger.info(f"Vector search: Using vector store at path: {self._vector_store.db_path}")
            
            # Query the vector store for similar messages
            logger.info(f"Vector search: Querying vector store with limit: {limit}")
            similar_docs = self._vector_store.query(
                query_text=query_text,
                filter_metadata=filter_metadata,
                limit=limit
            )
            
            logger.info(f"Vector search: Found {len(similar_docs)} document(s) in vector store")
            
            # Convert to ConversationMessages
            messages = []
            for doc in similar_docs:
                try:
                    # Extract message details from document
                    message_id = doc.get("metadata", {}).get("message_id")
                    
                    # If we have the message in memory, use that
                    if message_id in self._messages:
                        messages.append(self._messages[message_id])
                        logger.info(f"Vector search: Retrieved message {message_id} from memory")
                    else:
                        # Otherwise, construct a new message from the document
                        metadata = doc.get("metadata", {})
                        
                        # Parse timestamp if available
                        timestamp_str = metadata.get("timestamp")
                        timestamp = None
                        if timestamp_str:
                            try:
                                timestamp = datetime.fromisoformat(timestamp_str)
                            except ValueError:
                                timestamp = datetime.now()
                        
                        message = ConversationMessage(
                            role=MessageRole(metadata.get("role", "user")),
                            content=doc.get("text", ""),
                            metadata=metadata,
                            message_id=message_id,
                            timestamp=timestamp
                        )
                        messages.append(message)
                        logger.info(f"Vector search: Constructed message from document {message_id}")
                except Exception as e:
                    logger.error(f"Vector search: Error converting document to message: {str(e)}")
            
            logger.info(f"Vector search: Returning {len(messages)} message(s)")
            return messages
        except Exception as e:
            logger.error(f"Vector search: Error searching similar messages: {str(e)}", exc_info=True)
            return []


# Singleton instance
_memory_manager: Optional[MemoryManager] = None


def get_memory_manager() -> MemoryManager:
    """
    Get the memory manager instance.
    
    Returns:
        MemoryManager instance
    """
    global _memory_manager
    
    if _memory_manager is None:
        _memory_manager = MemoryManager()
        
    return _memory_manager 