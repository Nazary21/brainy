"""
Module manager for Brainy.

This module provides functionality for loading, managing, and using modules.
"""
import sys
import pkgutil
import importlib
import inspect
from typing import Dict, List, Any, Callable, Optional, Tuple

from brainy.utils.logging import get_logger
from brainy.config import settings

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
        debug_logging.log_module(message)
    # Also log at debug level in standard logger
    logger.debug(message)

class ModuleManager:
    """
    Manager for Brainy modules.
    
    This class:
    - Loads modules
    - Manages enabled/disabled modules
    - Routes messages to the appropriate modules
    - Provides APIs for interacting with modules
    """
    
    def __init__(self, module_dir: str = "brainy.modules"):
        """
        Initialize the module manager.
        
        Args:
            module_dir: Directory containing modules
        """
        self.module_dir = module_dir
        self.modules = {}
        self.loaded = False
        
        logger.info("Initialized module manager")
        if debug_log:
            debug("Module manager initialized")
    
    def load_modules(self, reload: bool = False) -> None:
        """
        Load all modules from the module directory.
        
        Args:
            reload: Whether to reload modules that are already loaded
        """
        if self.loaded and not reload:
            debug("Modules already loaded, skipping (use reload=True to force)")
            return
        
        debug(f"Loading modules from {self.module_dir}")
        
        # Get all modules in the module directory
        module_package = importlib.import_module(self.module_dir)
        modules_path = module_package.__path__
        
        for _, module_name, is_pkg in pkgutil.iter_modules(modules_path):
            if not is_pkg:
                # We're only interested in packages
                continue
            
            try:
                # Import the module
                module_path = f"{self.module_dir}.{module_name}"
                debug(f"Importing module from {module_path}")
                
                module = importlib.import_module(module_path)
                
                # Find module classes in the module
                for _, obj in inspect.getmembers(module, inspect.isclass):
                    if (
                        hasattr(obj, "__module__") and 
                        obj.__module__.startswith(module_path) and
                        hasattr(obj, "name") and
                        hasattr(obj, "description") and
                        hasattr(obj, "get_commands") and
                        hasattr(obj, "matches_message") and
                        hasattr(obj, "process_message")
                    ):
                        # This looks like a valid module
                        instance = obj()
                        self.modules[instance.name] = instance
                        debug(f"Loaded module: {instance.name}")
            except Exception as e:
                logger.error(f"Error loading module {module_name}: {str(e)}", exc_info=True)
                if debug_log:
                    debug_logging.log_error("MODULE", f"Error loading module {module_name}: {str(e)}", exc_info=True)
        
        self.loaded = True
        logger.info(f"Loaded {len(self.modules)} modules")
        debug(f"Loaded {len(self.modules)} modules: {', '.join(self.modules.keys())}")
    
    def get_all_modules(self) -> Dict[str, Any]:
        """
        Get all modules.
        
        Returns:
            Dictionary of module name to module object
        """
        if not self.loaded:
            self.load_modules()
        
        return self.modules
    
    def get_module(self, name: str) -> Optional[Any]:
        """
        Get a module by name.
        
        Args:
            name: Name of the module to get
        
        Returns:
            Module object if found, None otherwise
        """
        if not self.loaded:
            self.load_modules()
        
        return self.modules.get(name)
    
    def get_enabled_modules(self) -> List[Any]:
        """
        Get all enabled modules.
        
        Returns:
            List of enabled module objects
        """
        if not self.loaded:
            self.load_modules()
        
        # Get the disabled modules from settings
        disabled_modules = settings.DISABLED_MODULES or []
        debug(f"Disabled modules: {disabled_modules}")
        
        # Return all modules that aren't disabled
        enabled_modules = [
            module for name, module in self.modules.items()
            if name not in disabled_modules
        ]
        
        debug(f"Enabled modules: {[m.name for m in enabled_modules]}")
        return enabled_modules
    
    def find_matching_module(
        self,
        message_text: str,
        user_id: str,
        platform: str
    ) -> Tuple[Optional[Any], bool]:
        """
        Find a module that matches the given message.
        
        Args:
            message_text: Text of the message
            user_id: ID of the user who sent the message
            platform: Platform the message was sent on
        
        Returns:
            Tuple of (matching module, is exact match)
            If no module matches, returns (None, False)
        """
        if not self.loaded:
            self.load_modules()
        
        debug(f"Finding matching module for message: '{message_text[:50]}...'")
        
        # Get enabled modules
        enabled_modules = self.get_enabled_modules()
        
        # Try to find an exact match first
        for module in enabled_modules:
            if module.matches_message(message_text, user_id, platform, exact=True):
                debug(f"Found exact match with module: {module.name}")
                return module, True
        
        # If no exact match, try a fuzzy match
        for module in enabled_modules:
            if module.matches_message(message_text, user_id, platform, exact=False):
                debug(f"Found fuzzy match with module: {module.name}")
                return module, False
        
        debug("No matching module found")
        return None, False
    
    async def process_message(
        self,
        message_text: str,
        user_id: str,
        platform: str
    ) -> Optional[str]:
        """
        Process a message with the appropriate module.
        
        Args:
            message_text: Text of the message
            user_id: ID of the user who sent the message
            platform: Platform the message was sent on
        
        Returns:
            Response from the module, or None if no module processes the message
        """
        debug(f"Processing message with module manager: '{message_text[:50]}...'")
        
        # Find a matching module
        module, is_exact = self.find_matching_module(message_text, user_id, platform)
        
        if module:
            try:
                debug(f"Processing message with module {module.name}")
                response = await module.process_message(message_text, user_id, platform)
                if response:
                    debug(f"Got response from module {module.name}")
                    return response
            except Exception as e:
                logger.error(f"Error processing message with module {module.name}: {str(e)}", exc_info=True)
                if debug_log:
                    debug_logging.log_error("MODULE", f"Error processing message with module {module.name}: {str(e)}", exc_info=True)
        
        debug("No module response generated")
        return None
    
    async def process_command(
        self,
        command: str,
        args: str,
        user_id: str,
        platform: str
    ) -> Optional[str]:
        """
        Process a command with the appropriate module.
        
        Args:
            command: Command to process (without the leading slash)
            args: Arguments for the command
            user_id: ID of the user who sent the command
            platform: Platform the command was sent on
        
        Returns:
            Response from the module, or None if no module processes the command
        """
        if not self.loaded:
            self.load_modules()
        
        debug(f"Processing command: /{command} with args: '{args}'")
        
        # Get enabled modules
        enabled_modules = self.get_enabled_modules()
        
        # Find a module that can handle this command
        for module in enabled_modules:
            commands = module.get_commands()
            if command in commands:
                try:
                    debug(f"Processing command /{command} with module {module.name}")
                    
                    # Get the command handler
                    cmd_info = commands[command]
                    handler = cmd_info if callable(cmd_info) else cmd_info.get("handler")
                    
                    if callable(handler):
                        response = await handler(args, user_id, platform)
                        debug(f"Got response from module {module.name} for command /{command}")
                        return response
                except Exception as e:
                    logger.error(f"Error processing command {command} with module {module.name}: {str(e)}", exc_info=True)
                    if debug_log:
                        debug_logging.log_error("MODULE", f"Error processing command {command} with module {module.name}: {str(e)}", exc_info=True)
                    return f"Error processing command: {str(e)}"
        
        debug(f"No module found to handle command /{command}")
        return None