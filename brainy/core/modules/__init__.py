"""
Module system for Brainy.

This package contains the module system and individual modules
that extend the bot's functionality.
"""
from brainy.core.modules.base import Module, ModuleManager, get_module_manager
from brainy.core.modules.registry import register_builtin_modules, get_available_modules

__all__ = [
    "Module",
    "ModuleManager",
    "get_module_manager",
    "register_builtin_modules",
    "get_available_modules"
] 