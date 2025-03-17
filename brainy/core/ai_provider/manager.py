"""
AI provider manager for Brainy.

This module manages AI providers and provides a unified interface for generating
responses and embeddings.
"""
from typing import Dict, List, Any, Optional

from brainy.utils.logging import get_logger
from brainy.adapters.ai_providers import AIProvider, Message, get_default_provider

# Initialize logger
logger = get_logger(__name__)


class AiProviderManager:
    """
    Manager for AI providers.
    
    This class provides a unified interface for generating responses and
    embeddings from various AI providers.
    """
    
    def __init__(self):
        """Initialize the AI provider manager."""
        # Get the default AI provider
        self._default_provider = get_default_provider()
        
        # Dictionary of active providers by type
        self._providers: Dict[str, AIProvider] = {
            self._default_provider.name: self._default_provider
        }
        
        logger.info(f"Initialized AI provider manager with default provider: {self._default_provider.name}")
    
    async def generate_response(
        self,
        messages: List[Message],
        provider_type: Optional[str] = None,
        **kwargs
    ) -> str:
        """
        Generate a response using an AI provider.
        
        Args:
            messages: List of messages in the conversation
            provider_type: Type of provider to use. If not provided, the default provider will be used.
            **kwargs: Additional provider-specific parameters
            
        Returns:
            The generated response text
        """
        try:
            # Get the provider to use
            provider = self._get_provider(provider_type)
            
            logger.info(f"Generating response using provider: {provider.name}")
            logger.debug(f"Messages count: {len(messages)}")
            
            # Log the first few characters of each message for debugging
            for i, msg in enumerate(messages):
                content_preview = msg.content[:30] + "..." if len(msg.content) > 30 else msg.content
                logger.debug(f"Message {i+1} - Role: {msg.role}, Content: {content_preview}")
            
            # Generate the response
            response = await provider.generate_response(messages, **kwargs)
            
            response_preview = response[:50] + "..." if len(response) > 50 else response
            logger.info(f"Generated response: {response_preview}")
            
            return response
        except Exception as e:
            logger.error(f"Error generating response: {str(e)}", exc_info=True)
            # Return a fallback response
            return "I'm sorry, I encountered an error while generating a response. Please try again later."
    
    async def generate_embedding(
        self,
        text: str,
        provider_type: Optional[str] = None
    ) -> List[float]:
        """
        Generate an embedding for a text.
        
        Args:
            text: Text to generate an embedding for
            provider_type: Type of provider to use. If not provided, the default provider will be used.
            
        Returns:
            The generated embedding
        """
        # Get the provider to use
        provider = self._get_provider(provider_type)
        
        # Generate the embedding
        embedding = await provider.generate_embedding(text)
        
        return embedding
    
    def _get_provider(self, provider_type: Optional[str] = None) -> AIProvider:
        """
        Get an AI provider by type.
        
        Args:
            provider_type: Type of provider to get. If not provided, the default provider will be used.
            
        Returns:
            The AI provider
        """
        if provider_type is None:
            return self._default_provider
        
        # Check if we already have an instance of this provider type
        if provider_type in self._providers:
            return self._providers[provider_type]
        
        # We don't have an instance of this provider type,
        # so return the default provider
        logger.warning(f"Provider type '{provider_type}' not found, using default provider")
        return self._default_provider


# Singleton instance
_ai_provider_manager: Optional[AiProviderManager] = None


def get_ai_provider_manager() -> AiProviderManager:
    """
    Get the AI provider manager instance.
    
    Returns:
        The AI provider manager instance
    """
    global _ai_provider_manager
    if _ai_provider_manager is None:
        _ai_provider_manager = AiProviderManager()
    
    return _ai_provider_manager 