"""
Base interfaces for AI provider adapters.
"""
from abc import ABC, abstractmethod
from typing import Dict, List, Any, Optional


class Message:
    """Message representation for AI providers."""
    
    def __init__(self, role: str, content: str):
        """
        Initialize a message.
        
        Args:
            role: The role of the message sender (system, user, assistant)
            content: The content of the message
        """
        self.role = role
        self.content = content
    
    def to_dict(self) -> Dict[str, str]:
        """Convert message to dictionary representation."""
        return {
            "role": self.role,
            "content": self.content
        }


class AIProvider(ABC):
    """Base interface for AI provider adapters."""
    
    @abstractmethod
    async def generate_response(self, messages: List[Message], **kwargs) -> str:
        """
        Generate a response from the AI provider.
        
        Args:
            messages: List of messages in the conversation
            **kwargs: Additional provider-specific parameters
            
        Returns:
            The generated response text
        """
        pass
    
    @abstractmethod
    async def generate_embedding(self, text: str) -> List[float]:
        """
        Generate embeddings for a text.
        
        Args:
            text: The text to generate embeddings for
            
        Returns:
            List of embedding values
        """
        pass
    
    @property
    @abstractmethod
    def name(self) -> str:
        """Name of the provider."""
        pass
    
    @property
    @abstractmethod
    def available_models(self) -> List[str]:
        """List of available models from this provider."""
        pass


class AIProviderConfig:
    """Configuration for AI providers."""
    
    def __init__(
        self,
        api_key: str,
        model: str,
        temperature: float = 0.7,
        max_tokens: Optional[int] = None,
        **kwargs
    ):
        """
        Initialize provider configuration.
        
        Args:
            api_key: The API key for the provider
            model: The model to use
            temperature: The temperature for generation
            max_tokens: Maximum tokens to generate
            **kwargs: Additional provider-specific parameters
        """
        self.api_key = api_key
        self.model = model
        self.temperature = temperature
        self.max_tokens = max_tokens
        self.extra_params = kwargs 