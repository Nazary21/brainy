"""
Test script for the Brainy module system.

This script tests the core functionality of the module system without
requiring all external dependencies.
"""
import os
import sys
import re
import asyncio
from typing import Dict, List, Any, Optional

# Add the current directory to the Python path
sys.path.append(os.getcwd())

# Modify the import paths to avoid dependency issues
# We'll patch the logger to use print statements
import brainy.utils.logging.logger as logger_module
logger_module.get_logger = lambda name=None: SimpleLogger(name)

class SimpleLogger:
    def __init__(self, name=None):
        self.name = name or "root"
    
    def info(self, message, **kwargs):
        self._log("INFO", message, kwargs)
    
    def debug(self, message, **kwargs):
        self._log("DEBUG", message, kwargs)
    
    def error(self, message, **kwargs):
        self._log("ERROR", message, kwargs)
    
    def warning(self, message, **kwargs):
        self._log("WARNING", message, kwargs)
    
    def _log(self, level, message, kwargs):
        context = " ".join(f"{k}={v}" for k, v in kwargs.items())
        print(f"[{level}] {self.name}: {message} {context}")

# Create a mock conversation message for testing
class MockConversationMessage:
    def __init__(self, user_id, content, conversation_id="test_conv", platform="test"):
        self.user_id = user_id
        self.content = content
        self.role = "user"
        self.conversation_id = conversation_id
        self.platform = platform
        self.message_id = "test_msg_id"

async def test_module_system():
    """Run tests on the module system."""
    try:
        # Import the module system components
        from brainy.core.modules.base import Module, ModuleManager, get_module_manager
        from brainy.core.modules.reminder import ReminderModule, create_reminder_module
        
        print("\n=== Testing Module Manager ===")
        # Get the module manager
        module_manager = get_module_manager()
        print(f"Module manager initialized: {module_manager is not None}")
        
        print("\n=== Testing Reminder Module ===")
        # Create a reminder module
        reminder_module = create_reminder_module()
        print(f"Reminder module created: {reminder_module is not None}")
        print(f"Module ID: {reminder_module.module_id}")
        print(f"Module Name: {reminder_module.name}")
        print(f"Module Description: {reminder_module.description}")
        
        # Test command registration
        commands = reminder_module.get_commands()
        print(f"Registered commands: {list(commands.keys())}")
        
        # Test pattern matching
        test_messages = [
            "remind me to buy milk in 5 minutes",
            "set a reminder for my meeting in 2 hours",
            "what's the weather like today?",
            "help me with my homework"
        ]
        
        print("\n=== Testing Message Matching ===")
        for msg in test_messages:
            match = reminder_module.matches_message(msg)
            print(f"Message: '{msg}' -> Match: {match}")
        
        # Register module and test command processing
        print("\n=== Testing Module Registration and Command Processing ===")
        module_manager.register_module(reminder_module)
        
        # Test command processing
        test_command = "/remind 10 minutes check the oven"
        msg = MockConversationMessage("test_user", test_command)
        
        is_command = module_manager.is_command(msg.content)
        print(f"Is command: {is_command}")
        
        if is_command:
            cmd, args = module_manager.parse_command(msg.content)
            print(f"Parsed command: '{cmd}', args: {args}")
        
        # Process the command
        response = await module_manager.process_command(msg)
        print(f"Command response: {response}")
        
        # Test natural language processing
        print("\n=== Testing Natural Language Processing ===")
        nl_msg = MockConversationMessage("test_user", "remind me to call mom in 2 hours")
        
        # Find matching module
        matching_module = await module_manager.find_matching_module(nl_msg)
        print(f"Matching module: {matching_module.name if matching_module else 'None'}")
        
        if matching_module:
            # Process the message with the module
            context = {"user_id": nl_msg.user_id, "platform": nl_msg.platform}
            response = await matching_module.process_message(nl_msg, context)
            print(f"Natural language response: {response}")
        
        print("\n=== All Tests Completed Successfully ===")
        return True
    
    except Exception as e:
        print(f"Error during testing: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    print("Starting module system tests...")
    asyncio.run(test_module_system()) 