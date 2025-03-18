"""
OpenAI provider for Brainy.

This module provides integration with the OpenAI API.
"""
import sys
import asyncio
import json
from typing import Dict, List, Any, Optional

from openai import AsyncOpenAI, BadRequestError
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type

from brainy.utils.logging import get_logger
from brainy.config import settings
from brainy.providers.ai_provider import AIProvider, Message

# Add custom debug logging if available
try:
    sys.path.append(".")  # Add project root to path
    import debug_logging
    debug_log = True
except ImportError:
    debug_log = False

# Initialize logger
logger = get_logger(__name__)

# Debug logging function
def debug(message):
    if debug_log:
        debug_logging.log_ai_provider(message)
    # Also log at debug level in standard logger
    logger.debug(message)

class OpenAIProvider(AIProvider):
    """
    OpenAI provider for Brainy.
    
    This provider interfaces with the OpenAI API to generate responses.
    """
    
    def __init__(
        self,
        api_key: Optional[str] = None,
        model: Optional[str] = None,
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None
    ):
        """
        Initialize the OpenAI provider.
        
        Args:
            api_key: OpenAI API key. If not provided, will attempt to use OPENAI_API_KEY env var
            model: Model to use for completions. If not provided, defaults to gpt-3.5-turbo
            temperature: Temperature for completions. If not provided, defaults to 0.7
            max_tokens: Maximum tokens for completions. If not provided, defaults to None (API default)
        """
        # Set API key, using settings.OPENAI_API_KEY as fallback
        self.api_key = api_key or settings.OPENAI_API_KEY
        if not self.api_key:
            raise ValueError("OpenAI API key not provided and not found in environment")
        
        # Set model, using settings.OPENAI_MODEL as fallback
        self.model = model or settings.OPENAI_MODEL or "gpt-3.5-turbo"
        
        # Set temperature, using settings.OPENAI_TEMPERATURE as fallback
        self.temperature = temperature if temperature is not None else (
            settings.OPENAI_TEMPERATURE if settings.OPENAI_TEMPERATURE is not None else 0.7
        )
        
        # Set max tokens, using settings.OPENAI_MAX_TOKENS as fallback
        self.max_tokens = max_tokens or settings.OPENAI_MAX_TOKENS
        
        # Initialize OpenAI client
        self.client = AsyncOpenAI(api_key=self.api_key)
        
        logger.info(f"Initialized OpenAI provider with model: {self.model}")
        if debug_log:
            debug(f"Initialized OpenAI provider with model: {self.model}, temperature: {self.temperature}")
        
    @retry(
        retry=retry_if_exception_type((BadRequestError, ValueError, ConnectionError)),
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10)
    )
    async def generate_completion(self, messages: List[Message]) -> str:
        """
        Generate a completion from a list of messages.
        
        Args:
            messages: List of message dictionaries with 'role' and 'content'
        
        Returns:
            Generated text response
        """
        # Log the request we're about to make
        debug(f"Generating completion with model {self.model}")
        debug(f"Using temperature: {self.temperature}")
        debug(f"Message count: {len(messages)}")
        if len(messages) > 0:
            debug(f"First message role: {messages[0].role}, content start: '{messages[0].content[:50]}...'")
            debug(f"Last message role: {messages[-1].role}, content start: '{messages[-1].content[:50]}...'")
        
        try:
            # Prepare messages in the format expected by OpenAI
            formatted_messages = [
                {"role": msg.role, "content": msg.content}
                for msg in messages
            ]
            
            # Call the OpenAI API
            debug("Calling OpenAI API...")
            response = await self.client.chat.completions.create(
                model=self.model,
                messages=formatted_messages,
                temperature=self.temperature,
                max_tokens=self.max_tokens
            )
            
            # Extract the response content
            result = response.choices[0].message.content
            debug(f"Received response from OpenAI API, length: {len(result)}")
            debug(f"Response start: '{result[:50]}...'")
            
            return result
        except BadRequestError as e:
            error_msg = f"BadRequestError from OpenAI API: {str(e)}"
            logger.error(error_msg)
            if debug_log:
                debug_logging.log_error("AI_PROVIDER", error_msg, exc_info=True)
            raise
        except ValueError as e:
            error_msg = f"ValueError when calling OpenAI API: {str(e)}"
            logger.error(error_msg)
            if debug_log:
                debug_logging.log_error("AI_PROVIDER", error_msg, exc_info=True)
            raise
        except Exception as e:
            error_msg = f"Error calling OpenAI API: {str(e)}"
            logger.error(error_msg, exc_info=True)
            if debug_log:
                debug_logging.log_error("AI_PROVIDER", error_msg, exc_info=True)
            return f"Error generating response: {str(e)}" 