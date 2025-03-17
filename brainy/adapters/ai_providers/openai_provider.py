"""
OpenAI provider implementation.
"""
from typing import Dict, List, Any, Optional

from openai import AsyncOpenAI
from tenacity import retry, stop_after_attempt, wait_exponential

from brainy.utils.logging import get_logger
from brainy.adapters.ai_providers.base import AIProvider, AIProviderConfig, Message

# Initialize logger
logger = get_logger(__name__)


class OpenAIProvider(AIProvider):
    """OpenAI API provider implementation."""
    
    def __init__(self, config: AIProviderConfig):
        """
        Initialize OpenAI provider with configuration.
        
        Args:
            config: Provider configuration
        """
        self.config = config
        self.client = AsyncOpenAI(api_key=config.api_key)
        logger.info(f"Initialized OpenAI provider with model: {config.model}")
    
    @property
    def name(self) -> str:
        """Name of the provider."""
        return "openai"
    
    @property
    def available_models(self) -> List[str]:
        """List of available models from this provider."""
        return [
            "gpt-4",
            "gpt-4-turbo",
            "gpt-4o",
            "gpt-3.5-turbo",
            "gpt-3.5-turbo-16k",
        ]
    
    @retry(
        stop=stop_after_attempt(3), 
        wait=wait_exponential(multiplier=1, min=1, max=10)
    )
    async def generate_response(self, messages: List[Message], **kwargs) -> str:
        """
        Generate a response from OpenAI.
        
        Args:
            messages: List of messages in the conversation
            **kwargs: Additional provider-specific parameters
            
        Returns:
            The generated response text
        """
        try:
            # Convert messages to the format expected by OpenAI
            formatted_messages = [message.to_dict() for message in messages]
            
            # Prepare parameters for the API call
            params = {
                "model": self.config.model,
                "messages": formatted_messages,
                "temperature": self.config.temperature,
            }
            
            # Add max_tokens if specified
            if self.config.max_tokens:
                params["max_tokens"] = self.config.max_tokens
            
            # Add any additional parameters
            params.update(self.config.extra_params)
            
            # Override with any function-specific parameters
            params.update(kwargs)
            
            # Log the request (excluding message content for privacy)
            logger.debug(
                f"Sending request to OpenAI",
                model=params.get("model"),
                temperature=params.get("temperature"),
                max_tokens=params.get("max_tokens"),
                message_count=len(formatted_messages)
            )
            
            # Make the API request
            response = await self.client.chat.completions.create(**params)
            
            # Extract the response text
            response_text = response.choices[0].message.content
            
            return response_text
            
        except Exception as e:
            logger.error(f"Error generating response from OpenAI: {str(e)}")
            raise
    
    @retry(
        stop=stop_after_attempt(3), 
        wait=wait_exponential(multiplier=1, min=1, max=10)
    )
    async def generate_embedding(self, text: str) -> List[float]:
        """
        Generate embeddings for a text using OpenAI's embedding model.
        
        Args:
            text: The text to generate embeddings for
            
        Returns:
            List of embedding values
        """
        try:
            # The embedding model to use
            model = "text-embedding-ada-002"
            
            # Make the API request
            response = await self.client.embeddings.create(
                input=text,
                model=model
            )
            
            # Extract the embedding
            embedding = response.data[0].embedding
            
            return embedding
            
        except Exception as e:
            logger.error(f"Error generating embedding from OpenAI: {str(e)}")
            raise 