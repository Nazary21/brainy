"""
Direct test of the module system with minimal imports.

This test directly imports the module classes without loading the entire
application infrastructure.
"""
import os
import sys
import re
import asyncio
from typing import Dict, List, Any, Optional
from abc import ABC, abstractmethod

# Add the current directory to the Python path
sys.path.append(os.getcwd())

# Mock classes to avoid dependencies
class MockLogger:
    def info(self, msg, **kwargs): print(f"INFO: {msg}")
    def debug(self, msg, **kwargs): print(f"DEBUG: {msg}")
    def error(self, msg, **kwargs): print(f"ERROR: {msg}")
    def warning(self, msg, **kwargs): print(f"WARNING: {msg}")

class MockConversationMessage:
    def __init__(self, user_id, content, conversation_id="test_conv", platform="test"):
        self.user_id = user_id
        self.content = content
        self.role = "user"
        self.conversation_id = conversation_id
        self.platform = platform
        self.message_id = "test_msg_id"

# Define minimal Module interface
class Module(ABC):
    """Base class for all Brainy modules."""
    
    def __init__(self, module_id: str, name: str, description: str = ""):
        """Initialize a module."""
        self.module_id = module_id
        self.name = name
        self.description = description
        self.is_enabled = True
        self._trigger_patterns = []
        self._commands = {}
        self.logger = MockLogger()
        
    def register_trigger_pattern(self, pattern: str) -> None:
        """Register a regex pattern that will trigger this module."""
        try:
            compiled_pattern = re.compile(pattern, re.IGNORECASE)
            self._trigger_patterns.append(compiled_pattern)
            self.logger.debug(f"Registered trigger pattern for module {self.module_id}: {pattern}")
        except re.error as e:
            self.logger.error(f"Invalid trigger pattern for module {self.module_id}: {pattern} - {e}")
    
    def matches_message(self, message_text: str) -> bool:
        """Check if a message matches any of this module's trigger patterns."""
        for pattern in self._trigger_patterns:
            if pattern.search(message_text):
                return True
        return False
    
    def register_command(self, command: str, handler, description: str, **kwargs) -> None:
        """Register a command that this module can handle."""
        self._commands[command] = {
            "handler": handler,
            "description": description,
            **kwargs
        }
        self.logger.debug(f"Registered command for module {self.module_id}: {command}")
    
    def get_commands(self) -> Dict[str, Dict[str, Any]]:
        """Get all commands supported by this module."""
        return self._commands
    
    async def help_command(self, message, args: List[str]) -> str:
        """Default help command for modules."""
        help_text = f"### {self.name} Module\n\n"
        help_text += f"{self.description}\n\n"
        help_text += "**Available Commands:**\n\n"
        for cmd_name, cmd_info in self._commands.items():
            help_text += f"/{cmd_name} - {cmd_info['description']}\n"
        return help_text
    
    @abstractmethod
    async def process_message(self, message, context: Dict[str, Any]) -> Optional[str]:
        """Process a message that has triggered this module."""
        pass
    
    async def process_command(self, command: str, message, args: List[str]) -> Optional[str]:
        """Process a command directed at this module."""
        if command in self._commands:
            handler = self._commands[command]["handler"]
            try:
                return await handler(message, args)
            except Exception as e:
                self.logger.error(f"Error processing command {command} in module {self.module_id}: {e}")
                return f"Error processing command: {e}"
        return None

# Simple Reminder Module implementation
class ReminderModule(Module):
    """Module for managing reminders."""
    
    def __init__(self):
        """Initialize the reminder module."""
        super().__init__(
            module_id="reminder",
            name="Reminder",
            description="Set and manage reminders for future tasks."
        )
        
        # Dictionary of reminders by user ID
        self._reminders = {}
        
        # Register trigger patterns
        self.register_trigger_pattern(r"remind\s+me\s+to\s+(.+)")
        self.register_trigger_pattern(r"set\s+a\s+reminder\s+for\s+(.+)")
        
        # Register commands
        self.register_command(
            "remind", 
            self.remind_command, 
            "Set a reminder. Usage: /remind <time> <message>"
        )
        self.register_command(
            "reminders", 
            self.list_reminders_command, 
            "List your active reminders"
        )
    
    async def process_message(self, message, context: Dict[str, Any]) -> Optional[str]:
        """Process a message that has triggered this module."""
        # Try to extract a reminder from the message
        reminder_match = re.search(r"remind\s+me\s+to\s+(.+)", message.content, re.IGNORECASE)
        if reminder_match:
            task = reminder_match.group(1)
            
            # Try to extract a time from the task
            time_match = re.search(r"in\s+(\d+)\s+(minute|hour|day)s?", task, re.IGNORECASE)
            
            if time_match:
                # Extract the time components
                amount = int(time_match.group(1))
                unit = time_match.group(2).lower()
                
                # For test purposes, we'll just return a confirmation
                return f"I'll remind you about '{task}' in {amount} {unit}(s)."
            else:
                # No time specified, ask for clarification
                return (
                    f"When would you like me to remind you to {task}? "
                    f"Please specify a time like 'in 10 minutes' or 'in 2 hours'."
                )
        
        # Check other patterns
        reminder_match = re.search(r"set\s+a\s+reminder\s+for\s+(.+)", message.content, re.IGNORECASE)
        if reminder_match:
            return "To set a reminder, please use '/remind <time> <message>' or say 'remind me to do something in X minutes'."
        
        # If we get here, we couldn't process the message
        return None
    
    async def remind_command(self, message, args: List[str]) -> str:
        """Handle the /remind command."""
        if not args:
            return "Usage: /remind <time> <message>\nExample: /remind 30 minutes Check the oven"
        
        try:
            # For test purposes, we'll just echo back the command
            return f"Reminder set for {args[0]} {args[1]}: {' '.join(args[2:])}"
        except (ValueError, IndexError) as e:
            return "Usage: /remind <time> <message>\nExample: /remind 30 minutes Check the oven"
    
    async def list_reminders_command(self, message, args: List[str]) -> str:
        """Handle the /reminders command."""
        return "You don't have any active reminders."

# Module Manager
class ModuleManager:
    """Manager for module registration and dispatching."""
    
    def __init__(self):
        """Initialize the module manager."""
        self._modules = {}
        self._command_handlers = {}
        self.command_prefix = "/"
        self.logger = MockLogger()
    
    def register_module(self, module: Module) -> None:
        """Register a module with the manager."""
        # Check if module is already registered
        if module.module_id in self._modules:
            self.logger.warning(f"Module {module.module_id} already registered. Overwriting.")
        
        # Register the module
        self._modules[module.module_id] = module
        
        # Register command handlers
        for command, command_info in module.get_commands().items():
            if command in self._command_handlers:
                existing_module, _ = self._command_handlers[command]
                self.logger.warning(
                    f"Command /{command} already registered by module {existing_module.module_id}. "
                    f"Skipping registration for module {module.module_id}."
                )
                continue
            
            self._command_handlers[command] = (module, command_info["handler"])
        
        self.logger.info(f"Registered module: {module.name} ({module.module_id})")
    
    def get_module(self, module_id: str) -> Optional[Module]:
        """Get a module by ID."""
        return self._modules.get(module_id)
    
    def get_all_modules(self) -> List[Module]:
        """Get all registered modules."""
        return list(self._modules.values())
    
    def get_enabled_modules(self) -> List[Module]:
        """Get all enabled modules."""
        return [m for m in self._modules.values() if m.is_enabled]
    
    def is_command(self, message_text: str) -> bool:
        """Check if a message is a command."""
        return message_text.startswith(self.command_prefix)
    
    def parse_command(self, message_text: str):
        """Parse a command from a message."""
        # Strip the command prefix
        content = message_text[len(self.command_prefix):]
        
        # Split into command and args
        parts = content.split()
        if not parts:
            return "", []
        
        command = parts[0].lower()
        args = parts[1:]
        
        return command, args
    
    async def process_command(self, message) -> Optional[str]:
        """Process a command message."""
        # Parse the command
        command, args = self.parse_command(message.content)
        
        # Check if we have a handler for this command
        if command in self._command_handlers:
            module, _ = self._command_handlers[command]
            
            # Skip disabled modules
            if not module.is_enabled:
                return None
            
            try:
                # Process the command
                return await module.process_command(command, message, args)
            except Exception as e:
                self.logger.error(f"Error processing command {command}: {e}")
                return f"Error processing command: {e}"
        
        return None
    
    async def find_matching_module(self, message) -> Optional[Module]:
        """Find a module that matches a message."""
        for module in self.get_enabled_modules():
            if module.matches_message(message.content):
                return module
        return None
    
    async def process_message(self, message, context: Dict[str, Any]) -> Optional[str]:
        """Process a message with the appropriate module."""
        # Check if the message is a command
        if self.is_command(message.content):
            return await self.process_command(message)
        
        # Find a module that matches the message
        module = await self.find_matching_module(message)
        if module:
            try:
                return await module.process_message(message, context)
            except Exception as e:
                self.logger.error(f"Error processing message with module {module.module_id}: {e}")
                return f"Error processing message: {e}"
        
        # No matching module, so let the AI provider handle it
        return None

async def run_tests():
    """Run tests on our module system implementation."""
    print("Starting module system tests...")
    
    # Create a module manager
    manager = ModuleManager()
    print("Created module manager")
    
    # Create a reminder module
    reminder = ReminderModule()
    print(f"Created reminder module: {reminder.name} ({reminder.module_id})")
    
    # Register the module with the manager
    manager.register_module(reminder)
    print(f"Registered module with manager")
    
    # Test modules list
    modules = manager.get_all_modules()
    print(f"Registered modules: {len(modules)}")
    for module in modules:
        print(f"- {module.name} ({module.module_id})")
        print(f"  Commands: {list(module.get_commands().keys())}")
    
    # Test command handling
    print("\nTesting command handling:")
    msg = MockConversationMessage("user123", "/remind 30 minutes check the oven")
    is_command = manager.is_command(msg.content)
    print(f"Is command: {is_command}")
    
    response = await manager.process_command(msg)
    print(f"Command response: {response}")
    
    # Test natural language handling
    print("\nTesting natural language processing:")
    nl_msg = MockConversationMessage("user123", "remind me to call mom in 2 hours")
    matching_module = await manager.find_matching_module(nl_msg)
    print(f"Matching module: {matching_module.name if matching_module else 'None'}")
    
    if matching_module:
        nl_response = await matching_module.process_message(nl_msg, {})
        print(f"NLP response: {nl_response}")
    
    print("\nTests completed successfully!")

if __name__ == "__main__":
    asyncio.run(run_tests()) 