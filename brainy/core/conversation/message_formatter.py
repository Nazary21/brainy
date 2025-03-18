"""
Message formatter for Brainy.

This module provides functionality for formatting messages for AI providers.
"""
import sys
from typing import List, Dict, Any, Optional

from brainy.core.character import Character
from brainy.core.memory_manager import ConversationMessage, MessageRole
from brainy.providers.ai_provider import Message

# Add custom debug logging if available
try:
    sys.path.append(".")  # Add project root to path
    import debug_logging
    debug_log = True
except ImportError:
    debug_log = False


class MessageFormatter:
    """
    Formats messages for AI providers.
    
    This class:
    - Adds system prompts based on character
    - Formats conversation history for the AI provider
    - Handles message role mapping between systems
    """
    
    def __init__(self):
        """Initialize the message formatter."""
        pass
    
    def format_messages(
        self,
        messages: List[ConversationMessage],
        character: Character
    ) -> List[Message]:
        """
        Format messages for the AI provider.
        
        Args:
            messages: List of conversation messages
            character: Character to use for system prompt
            
        Returns:
            List of formatted messages for the AI provider
        """
        if debug_log:
            debug_logging.log_conversation(f"Formatting {len(messages)} messages with character: {character.name}")
        
        # Start with the system prompt
        formatted_messages = [
            Message(
                role="system",
                content=character.system_prompt
            )
        ]
        
        # Add conversation messages
        for msg in messages:
            # Map internal roles to OpenAI roles
            role = self._map_role_to_ai_provider(msg.role)
            
            formatted_messages.append(
                Message(
                    role=role,
                    content=msg.content
                )
            )
        
        if debug_log:
            debug_logging.log_conversation(f"Formatted {len(formatted_messages)} messages (including system prompt)")
        
        return formatted_messages
    
    def _map_role_to_ai_provider(self, role: str) -> str:
        """
        Map internal role to AI provider role.
        
        Args:
            role: Internal role (USER, ASSISTANT, SYSTEM)
            
        Returns:
            Role string for AI provider (user, assistant, system)
        """
        role_mapping = {
            MessageRole.USER: "user",
            MessageRole.ASSISTANT: "assistant",
            MessageRole.SYSTEM: "system"
        }
        
        return role_mapping.get(role, "user")  # Default to user if unknown role 