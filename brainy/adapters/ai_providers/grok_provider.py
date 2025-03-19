"""
Grok provider implementation for Anthropic's Grok API.
"""
from typing import Dict, List, Any, Optional
import httpx
import json

from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type

from brainy.utils.logging import get_logger
from brainy.adapters.ai_providers.base import AIProvider, AIProviderConfig, Message

# Initialize logger
logger = get_logger(__name__)


class GrokProvider(AIProvider):
    """Anthropic Grok API provider implementation."""
    
    def __init__(self, config: AIProviderConfig):
        """
        Initialize Grok provider with configuration.
        
        Args:
            config: Provider configuration
        """
        self.config = config
        self.api_key = config.api_key
        self.model = config.model
        self.base_url = "https://api.groq.com/openai/v1"
        logger.info(f"Initialized Grok provider with model: {config.model}")
    
    @property
    def name(self) -> str:
        """Name of the provider."""
        return "grok"
    
    @property
    def available_models(self) -> List[str]:
        """List of available models from this provider."""
        return [
            "grok-1",
            "grok-1.5",
        ]
    
    @retry(
        retry=retry_if_exception_type((httpx.HTTPError, ValueError, ConnectionError)),
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10)
    )
    async def generate_response(self, messages: List[Message], **kwargs) -> str:
        """
        Generate a response from Grok.
        
        Args:
            messages: List of messages in the conversation
            **kwargs: Additional provider-specific parameters
            
        Returns:
            The generated response text
        """
        try:
            # Convert messages to the format expected by Grok (OpenAI compatible format)
            formatted_messages = [message.to_dict() for message in messages]
            
            # Prepare parameters for the API call
            params = {
                "model": self.model,
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
            logger.info(
                f"Sending request to Grok API",
                model=params.get("model"),
                temperature=params.get("temperature"),
                max_tokens=params.get("max_tokens"),
                message_count=len(formatted_messages)
            )
            
            # Log API key status (securely)
            api_key = self.api_key
            logger.debug(f"API key status: {'Set (starts with ' + api_key[:4] + '...)' if api_key else 'Not set'}")
            
            # Make the API request using httpx
            headers = {
                "Content-Type": "application/json",
                "Authorization": f"Bearer {self.api_key}"
            }
            
            # Make the API request
            logger.debug("Starting Grok API call")
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    f"{self.base_url}/chat/completions",
                    headers=headers,
                    json=params,
                    timeout=60.0
                )
                
                # Check for errors
                if response.status_code != 200:
                    error_msg = f"Grok API error: {response.status_code} - {response.text}"
                    logger.error(error_msg)
                    raise ValueError(error_msg)
                
                # Parse the response
                response_data = response.json()
                
            logger.debug("Completed Grok API call")
            
            # Extract the response text
            response_text = response_data["choices"][0]["message"]["content"]
            
            # Log a preview of the response
            response_preview = response_text[:50] + "..." if len(response_text) > 50 else response_text
            logger.info(f"Received response from Grok: {response_preview}")
            
            return response_text
            
        except Exception as e:
            logger.error(f"Error generating response from Grok: {str(e)}", exc_info=True)
            raise
    
    @retry(
        retry=retry_if_exception_type((httpx.HTTPError, ValueError, ConnectionError)),
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10)
    )
    async def generate_embedding(self, text: str) -> List[float]:
        """
        Generate embeddings for a text using Grok's embedding model.
        
        Args:
            text: The text to generate embeddings for
            
        Returns:
            List of embedding values
        """
        try:
            # For Grok, we'll use the OpenAI-compatible embeddings endpoint
            headers = {
                "Content-Type": "application/json",
                "Authorization": f"Bearer {self.api_key}"
            }
            
            body = {
                "input": text,
                "model": "embedding-001"  # Use appropriate embedding model
            }
            
            # Make the API request
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    f"{self.base_url}/embeddings",
                    headers=headers,
                    json=body,
                    timeout=30.0
                )
                
                # Check for errors
                if response.status_code != 200:
                    error_msg = f"Grok Embeddings API error: {response.status_code} - {response.text}"
                    logger.error(error_msg)
                    raise ValueError(error_msg)
                
                # Parse the response
                response_data = response.json()
            
            # Extract the embedding
            embedding = response_data["data"][0]["embedding"]
            
            return embedding
            
        except Exception as e:
            logger.error(f"Error generating embedding from Grok: {str(e)}")
            # Fall back to OpenAI embeddings if configured
            from brainy.adapters.ai_providers import create_provider
            try:
                logger.info("Falling back to OpenAI for embeddings")
                openai_provider = create_provider("openai")
                return await openai_provider.generate_embedding(text)
            except Exception as fallback_error:
                logger.error(f"Fallback to OpenAI embeddings failed: {str(fallback_error)}")
                raise 