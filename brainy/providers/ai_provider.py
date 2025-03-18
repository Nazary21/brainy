"""
AI provider base class for Brainy.

This module defines the base interface for AI providers.
"""
from abc import ABC, abstractmethod
from typing import List, Dict, Any, Optional


class Message:
    """
    Represents a message in a conversation with an AI provider.
    """
    
    def __init__(self, role: str, content: str):
        """
        Initialize a message.
        
        Args:
            role: Role of the message sender (system, user, assistant)
            content: Content of the message
        """
        self.role = role
        self.content = content
    
    def to_dict(self) -> Dict[str, str]:
        """
        Convert the message to a dictionary.
        
        Returns:
            Dictionary representation of the message
        """
        return {
            "role": self.role,
            "content": self.content
        }


class AIProvider(ABC):
    """
    Base class for AI providers.
    
    This class defines the interface that all AI providers must implement.
    """
    
    @abstractmethod
    async def generate_completion(self, messages: List[Message]) -> str:
        """
        Generate a completion from a list of messages.
        
        Args:
            messages: List of messages in the conversation
            
        Returns:
            The generated completion text
        """
        pass


def get_ai_provider() -> AIProvider:
    """
    Get the default AI provider.
    
    Returns:
        An instance of the default AI provider
    """
    from brainy.providers.openai_provider import OpenAIProvider
    
    return OpenAIProvider() 