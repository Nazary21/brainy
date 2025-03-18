"""
Base module system for Brainy.

This module defines the core interfaces for creating extension modules.
"""
from abc import ABC, abstractmethod
from typing import Dict, List, Any, Optional, Callable, Set, Tuple
import re
import inspect
import datetime

from brainy.utils.logging import get_logger
from brainy.config import settings
from brainy.core.memory_manager import ConversationMessage

# Initialize logger
logger = get_logger(__name__)


class Module(ABC):
    """
    Base class for all Brainy modules.
    
    Modules provide additional functionality to the bot, such as task management,
    information lookup, or integration with external services.
    """
    
    def __init__(self, module_id: str, name: str, description: str = ""):
        """
        Initialize a module.
        
        Args:
            module_id: Unique identifier for the module
            name: Display name of the module
            description: Description of what the module does
        """
        self.module_id = module_id
        self.name = name
        self.description = description
        self.is_enabled = True
        
        # Patterns that trigger this module
        self._trigger_patterns: List[re.Pattern] = []
        
        # Commands supported by this module
        self._commands: Dict[str, Dict[str, Any]] = {}
        
        # Register basic commands
        self.register_command("help", self.help_command, "Show help for this module")
        
        # For debugging/development purposes
        if settings.DEBUG:
            self.register_command(
                "debug_rag",
                self.debug_rag_command,
                "Debug RAG retrieval for a given query",
                usage="/debug_rag <query>",
                examples=["/debug_rag What is machine learning?"]
            )
        
        logger.info(f"Initialized module: {self.name} ({self.module_id})")
    
    def register_trigger_pattern(self, pattern: str) -> None:
        """
        Register a regex pattern that will trigger this module.
        
        Args:
            pattern: Regular expression pattern to match against user messages
        """
        try:
            compiled_pattern = re.compile(pattern, re.IGNORECASE)
            self._trigger_patterns.append(compiled_pattern)
            logger.debug(f"Registered trigger pattern for module {self.module_id}: {pattern}")
        except re.error as e:
            logger.error(f"Invalid trigger pattern for module {self.module_id}: {pattern} - {e}")
    
    def matches_message(self, message_text: str) -> bool:
        """
        Check if a message matches any of this module's trigger patterns.
        
        Args:
            message_text: The text of the message to check
            
        Returns:
            True if the message matches a trigger pattern, False otherwise
        """
        for pattern in self._trigger_patterns:
            if pattern.search(message_text):
                return True
        return False
    
    def register_command(
        self, 
        command: str, 
        handler: Callable,
        description: str,
        **kwargs
    ) -> None:
        """
        Register a command with this module.
        
        Args:
            command: Command name (without leading slash)
            handler: Async function that handles the command
            description: Description of the command
            **kwargs: Additional command metadata
        """
        self._commands[command] = {
            "handler": handler,
            "description": description,
            **kwargs
        }
        logger.debug(f"Registered command '{command}' for module '{self.module_id}'")
    
    def get_commands(self) -> Dict[str, Dict[str, Any]]:
        """
        Get all commands registered with this module.
        
        Returns:
            Dictionary of command names to command info
        """
        return self._commands
    
    async def help_command(self, message: ConversationMessage, args: List[str]) -> str:
        """
        Default help command for modules.
        
        Args:
            message: The message that triggered the command
            args: Arguments passed to the command
            
        Returns:
            Help text for the module
        """
        help_text = f"### {self.name} Module\n\n"
        help_text += f"{self.description}\n\n"
        
        help_text += "**Available Commands:**\n\n"
        
        for cmd_name, cmd_info in self._commands.items():
            help_text += f"/{cmd_name} - {cmd_info['description']}\n"
        
        return help_text
    
    @abstractmethod
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
        pass
    
    async def process_command(
        self,
        command: str,
        message: ConversationMessage,
        args: List[str]
    ) -> Optional[str]:
        """
        Process a command directed at this module.
        
        Args:
            command: The command to process (without prefix)
            message: The message containing the command
            args: Arguments passed to the command
            
        Returns:
            Response from the module, or None if the command is not handled
        """
        if command in self._commands:
            handler = self._commands[command]["handler"]
            try:
                return await handler(message, args)
            except Exception as e:
                logger.error(f"Error processing command {command} in module {self.module_id}: {e}")
                return f"Error processing command: {e}"
        return None
    
    def to_dict(self) -> Dict[str, Any]:
        """
        Convert module to dictionary representation.
        
        Returns:
            Dictionary representation of the module
        """
        return {
            "module_id": self.module_id,
            "name": self.name,
            "description": self.description,
            "is_enabled": self.is_enabled,
            "commands": list(self._commands.keys())
        }
    
    async def debug_rag_command(
        self,
        message: ConversationMessage,
        args: List[str]
    ) -> str:
        """
        Debug command to show what RAG context is being retrieved.
        
        Args:
            message: The message containing the command
            args: Command arguments (the query text)
            
        Returns:
            Debug information about retrieved context
        """
        if not args:
            return "Please provide a query to test RAG retrieval."
        
        query_text = " ".join(args)
        
        try:
            # Get the conversation ID
            user_id = message.metadata.get("user_id")
            platform = message.metadata.get("platform")
            if not user_id or not platform:
                return "Error: User information not available."
            
            conversation_id = f"{platform}:{user_id}"
            
            logger.info(f"RAG DEBUG: Testing query '{query_text}' for conversation {conversation_id}")
            
            # Get the memory manager
            from brainy.core.memory_manager import get_memory_manager
            memory_manager = get_memory_manager()
            
            # Log vector store path
            from brainy.config import settings
            logger.info(f"RAG DEBUG: Vector DB path: {settings.VECTOR_DB_PATH}")
            
            # Search for similar messages
            logger.info(f"RAG DEBUG: Searching for similar messages...")
            similar_messages = await memory_manager.search_similar_messages(
                query_text=query_text,
                conversation_id=conversation_id,
                limit=5
            )
            
            if not similar_messages:
                logger.info(f"RAG DEBUG: No similar messages found for query: '{query_text}'")
                return f"No similar messages found for query: '{query_text}'"
            
            # Format the results
            logger.info(f"RAG DEBUG: Found {len(similar_messages)} similar messages")
            results = f"Found {len(similar_messages)} similar messages for query: '{query_text}'\n\n"
            
            for i, msg in enumerate(similar_messages, 1):
                # Truncate content if too long
                content = msg.content
                if len(content) > 100:
                    content = content[:97] + "..."
                
                results += f"{i}. {msg.role}: {content}\n"
                results += f"   Time: {msg.timestamp.strftime('%Y-%m-%d %H:%M:%S')}\n\n"
                logger.info(f"RAG DEBUG: Result {i}: {msg.role} message from {msg.timestamp}")
            
            return results
        except Exception as e:
            error_msg = f"Error testing RAG retrieval: {str(e)}"
            logger.error(f"RAG DEBUG ERROR: {error_msg}", exc_info=True)
            return error_msg


class ModuleManager:
    """
    Manager for module registration and dispatching.
    
    This class manages all the modules in the system and handles
    routing messages to the appropriate modules.
    """
    
    def __init__(self):
        """Initialize the module manager."""
        # Dictionary of modules by ID
        self._modules: Dict[str, Module] = {}
        
        # Dictionary of command handlers by command name
        self._command_handlers: Dict[str, Tuple[Module, Callable]] = {}
        
        # Command prefix
        self.command_prefix = "/"
        
        logger.info("Initialized module manager")
    
    def register_module(self, module: Module) -> None:
        """
        Register a module with the manager.
        
        Args:
            module: The module to register
        """
        # Check if module is already registered
        if module.module_id in self._modules:
            logger.warning(f"Module {module.module_id} already registered. Overwriting.")
        
        # Register the module
        self._modules[module.module_id] = module
        
        # Register command handlers
        for command, command_info in module.get_commands().items():
            # Skip if command is already registered
            if command in self._command_handlers:
                existing_module, _ = self._command_handlers[command]
                logger.warning(
                    f"Command /{command} already registered by module {existing_module.module_id}. "
                    f"Skipping registration for module {module.module_id}."
                )
                continue
            
            # Register the command
            self._command_handlers[command] = (module, command_info["handler"])
        
        logger.info(f"Registered module: {module.name} ({module.module_id})")
    
    def get_module(self, module_id: str) -> Optional[Module]:
        """
        Get a module by ID.
        
        Args:
            module_id: ID of the module to get
            
        Returns:
            The module if found, None otherwise
        """
        return self._modules.get(module_id)
    
    def get_all_modules(self) -> List[Module]:
        """
        Get all registered modules.
        
        Returns:
            List of all modules
        """
        return list(self._modules.values())
    
    def get_enabled_modules(self) -> List[Module]:
        """
        Get all enabled modules.
        
        Returns:
            List of enabled modules
        """
        return [m for m in self._modules.values() if m.is_enabled]
    
    def is_command(self, message_text: str) -> bool:
        """
        Check if a message is a command.
        
        Args:
            message_text: The text of the message to check
            
        Returns:
            True if the message is a command, False otherwise
        """
        return message_text.startswith(self.command_prefix)
    
    def parse_command(self, message_text: str) -> Tuple[str, List[str]]:
        """
        Parse a command from a message.
        
        Args:
            message_text: The text of the message to parse
            
        Returns:
            Tuple of (command, args)
        """
        # Strip the command prefix
        content = message_text[len(self.command_prefix):]
        
        # Split into command and args
        parts = content.split()
        if not parts:
            return "", []
        
        command = parts[0].lower()
        args = parts[1:]
        
        return command, args
    
    async def process_command(
        self,
        message: ConversationMessage
    ) -> Optional[str]:
        """
        Process a command message.
        
        Args:
            message: The message to process
            
        Returns:
            Response from the module, or None if the command is not handled
        """
        # Parse the command
        command, args = self.parse_command(message.content)
        
        # Check if we have a handler for this command
        if command in self._command_handlers:
            module, handler = self._command_handlers[command]
            
            # Skip disabled modules
            if not module.is_enabled:
                return None
            
            try:
                # Process the command
                return await module.process_command(command, message, args)
            except Exception as e:
                logger.error(f"Error processing command {command}: {e}")
                return f"Error processing command: {e}"
        
        return None
    
    async def find_matching_module(
        self,
        message: ConversationMessage
    ) -> Optional[Module]:
        """
        Find a module that matches a message.
        
        Args:
            message: The message to match
            
        Returns:
            Matching module, or None if no match found
        """
        for module in self.get_enabled_modules():
            if module.matches_message(message.content):
                return module
        return None
    
    async def process_message(
        self,
        message: ConversationMessage,
        context: Dict[str, Any]
    ) -> Optional[str]:
        """
        Process a message with the appropriate module.
        
        Args:
            message: The message to process
            context: Additional context for processing
            
        Returns:
            Response from the module, or None if the message should be
            processed by the AI provider.
        """
        # Check if the message is a command
        if self.is_command(message.content):
            return await self.process_command(message)
        
        # Find a module that matches the message
        module = await self.find_matching_module(message)
        if module:
            try:
                return await module.process_message(message, context)
            except Exception as e:
                logger.error(f"Error processing message with module {module.module_id}: {e}")
                return f"Error processing message: {e}"
        
        # No matching module, so let the AI provider handle it
        return None


# Singleton instance
_module_manager: Optional[ModuleManager] = None


def get_module_manager() -> ModuleManager:
    """
    Get the module manager instance.
    
    Returns:
        The module manager instance
    """
    global _module_manager
    if _module_manager is None:
        _module_manager = ModuleManager()
    
    return _module_manager 