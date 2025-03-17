"""
Module registry for Brainy.

This module contains functions for initializing and registering modules.
"""
from typing import List, Dict, Any

from brainy.utils.logging import get_logger
from brainy.core.modules.base import Module, get_module_manager
from brainy.core.modules.reminder import create_reminder_module

# Initialize logger
logger = get_logger(__name__)


async def register_builtin_modules() -> None:
    """
    Register all built-in modules.
    
    This function should be called once during application startup.
    """
    module_manager = get_module_manager()
    
    # Create and register modules
    modules = [
        create_reminder_module(),
        # Add more built-in modules here as they are created
    ]
    
    # Register each module
    for module in modules:
        module_manager.register_module(module)
    
    logger.info(f"Registered {len(modules)} built-in modules")


def get_available_modules() -> List[Dict[str, Any]]:
    """
    Get a list of all available modules.
    
    Returns:
        List of module information dictionaries
    """
    module_manager = get_module_manager()
    modules = module_manager.get_all_modules()
    
    return [module.to_dict() for module in modules] 