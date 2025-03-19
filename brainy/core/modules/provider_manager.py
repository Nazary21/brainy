"""
Provider management module for Brainy.

This module provides commands for managing and switching between AI providers.
"""
from typing import Dict, List, Any, Optional
import os
import json
from pathlib import Path

from brainy.utils.logging import get_logger
from brainy.core.modules.base import Module
from brainy.core.memory_manager import ConversationMessage
from brainy.adapters.ai_providers import create_provider
from brainy.config import settings

# Initialize logger
logger = get_logger(__name__)


class ProviderManagerModule(Module):
    """
    Module for managing AI providers.
    
    This module allows users to switch between different AI providers
    such as OpenAI, Grok, etc.
    """
    
    def __init__(self):
        """Initialize the provider manager module."""
        super().__init__(
            module_id="provider_manager",
            name="Provider Manager",
            description="Manage and switch between AI providers"
        )
        
        # Register commands
        self.register_command(
            "provider",
            self.provider_command,
            "Switch or view current AI provider",
            usage="/provider [provider_id]",
            examples=[
                "/provider - Show current provider",
                "/provider openai - Switch to OpenAI",
                "/provider grok - Switch to Grok"
            ]
        )
        
        # Dictionary to store user provider preferences
        self._preferences_file = os.path.join(
            settings.VECTOR_DB_PATH, "provider_preferences.json"
        )
        self._preferences: Dict[str, str] = self._load_preferences()
    
    def _load_preferences(self) -> Dict[str, str]:
        """Load provider preferences from file."""
        preferences = {}
        try:
            if os.path.exists(self._preferences_file):
                with open(self._preferences_file, "r") as f:
                    preferences = json.load(f)
        except Exception as e:
            logger.error(f"Error loading provider preferences: {e}")
        
        return preferences
    
    def _save_preferences(self) -> None:
        """Save provider preferences to file."""
        try:
            # Create directory if it doesn't exist
            os.makedirs(os.path.dirname(self._preferences_file), exist_ok=True)
            
            with open(self._preferences_file, "w") as f:
                json.dump(self._preferences, f)
        except Exception as e:
            logger.error(f"Error saving provider preferences: {e}")
    
    def get_provider_for_conversation(self, conversation_id: str) -> str:
        """
        Get the provider for a conversation.
        
        Args:
            conversation_id: ID of the conversation
            
        Returns:
            Provider ID for the conversation, or the default provider if none is set
        """
        return self._preferences.get(conversation_id, settings.DEFAULT_AI_PROVIDER)
    
    def set_provider_for_conversation(self, conversation_id: str, provider_id: str) -> None:
        """
        Set the provider for a conversation.
        
        Args:
            conversation_id: ID of the conversation
            provider_id: ID of the provider to use
        """
        self._preferences[conversation_id] = provider_id
        self._save_preferences()
    
    async def process_message(
        self,
        message: ConversationMessage,
        context: Dict[str, Any]
    ) -> Optional[str]:
        """
        Process a message that has triggered this module.
        
        Args:
            message: The message to process
            context: Additional context for processing
            
        Returns:
            Optional response from the module. If None, the message
            will be processed by the AI provider.
        """
        # This module doesn't process regular messages
        return None
    
    async def provider_command(
        self,
        message: ConversationMessage,
        args: List[str]
    ) -> str:
        """
        Handle the /provider command.
        
        Args:
            message: The message containing the command
            args: Command arguments
            
        Returns:
            Response message
        """
        try:
            # Get conversation ID
            conversation_id = message.metadata.get("conversation_id")
            if not conversation_id:
                return "Error: Conversation ID not found in message metadata."
            
            # Get current provider
            current_provider = self.get_provider_for_conversation(conversation_id)
            
            # If no provider specified, show current provider
            if not args:
                available_providers = ["openai", "grok"]
                provider_list = "\n".join([f"• {p}" for p in available_providers])
                
                return (
                    f"📌 **Current AI Provider:** {current_provider}\n\n"
                    f"To switch providers, use:\n"
                    f"`/provider <provider_id>`\n\n"
                    f"Available providers:\n{provider_list}"
                )
            
            # Get the provider ID from args
            provider_id = args[0].lower()
            
            # Check if provider is valid
            valid_providers = ["openai", "grok"]
            if provider_id not in valid_providers:
                return (
                    f"❌ Unknown provider: '{provider_id}'\n\n"
                    f"Available providers:\n" + 
                    "\n".join([f"• {p}" for p in valid_providers])
                )
            
            # Check if trying to switch to the same provider
            if provider_id == current_provider:
                return f"You're already using the '{provider_id}' provider."
            
            # Check if the provider is properly configured
            try:
                # Try to create the provider to ensure it's properly configured
                provider = create_provider(provider_id)
                logger.info(f"Successfully tested provider '{provider_id}'")
            except Exception as e:
                logger.error(f"Error creating provider '{provider_id}': {e}")
                return f"❌ Error: Provider '{provider_id}' is not properly configured. Please check your API keys."
            
            # Update provider for conversation
            self.set_provider_for_conversation(conversation_id, provider_id)
            
            return f"✅ AI provider changed to: {provider_id}"
            
        except Exception as e:
            logger.error(f"Error handling provider command: {e}")
            return f"Error handling command: {str(e)}"


def create_provider_manager_module() -> ProviderManagerModule:
    """Create an instance of the provider manager module."""
    return ProviderManagerModule() 