"""
Factory for creating AI providers.
"""
from typing import Dict, Optional

from brainy.utils.logging import get_logger
from brainy.adapters.ai_providers.base import AIProvider, AIProviderConfig
from brainy.adapters.ai_providers.openai_provider import OpenAIProvider
from brainy.config import settings

# Initialize logger
logger = get_logger(__name__)

# Cache for provider instances
_provider_instances: Dict[str, AIProvider] = {}


def create_provider(provider_type: str, config: Optional[AIProviderConfig] = None) -> AIProvider:
    """
    Create an AI provider instance.
    
    Args:
        provider_type: Type of provider to create (e.g., "openai")
        config: Optional configuration for the provider.
            If not provided, will use default configuration from settings.
            
    Returns:
        An instance of the AI provider
        
    Raises:
        ValueError: If the provider type is not supported
    """
    # Check if we already have an instance of this provider type
    if provider_type in _provider_instances:
        logger.debug(f"Returning cached instance of {provider_type} provider")
        return _provider_instances[provider_type]
    
    # Create a new provider instance
    logger.info(f"Creating new {provider_type} provider")
    
    # Get configuration from settings if not provided
    if config is None:
        provider_config_dict = settings.get_ai_provider_config(provider_type)
        config = AIProviderConfig(**provider_config_dict)
    
    # Create the provider instance
    if provider_type == "openai":
        provider = OpenAIProvider(config)
    else:
        raise ValueError(f"Unsupported provider type: {provider_type}")
    
    # Cache the instance
    _provider_instances[provider_type] = provider
    
    return provider


def get_default_provider() -> AIProvider:
    """
    Get the default AI provider.
    
    Returns:
        The default AI provider
    """
    default_provider_type = settings.DEFAULT_AI_PROVIDER
    return create_provider(default_provider_type) 