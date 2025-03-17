"""
Very simple test to validate the structure of our module system.
"""
import os
import sys
from abc import ABC, abstractmethod
from typing import Dict, List, Any, Optional, Callable

# Add the current directory to the Python path
sys.path.append(os.getcwd())

class DummyLogger:
    def info(self, message):
        print(f"INFO: {message}")
    
    def debug(self, message):
        print(f"DEBUG: {message}")
    
    def error(self, message):
        print(f"ERROR: {message}")

# Simple module system implementation for testing
class SimpleModule(ABC):
    def __init__(self, module_id, name, description=""):
        self.module_id = module_id
        self.name = name
        self.description = description
        self.commands = {}
        print(f"Initialized module: {name} ({module_id})")
    
    def register_command(self, command, handler, description):
        self.commands[command] = {"handler": handler, "description": description}
        print(f"Registered command {command} for module {self.module_id}")
    
    def get_commands(self):
        return self.commands

class SimpleReminderModule(SimpleModule):
    def __init__(self):
        super().__init__(
            module_id="reminder",
            name="Reminder",
            description="Set and manage reminders for future tasks."
        )
        
        # Register some commands
        self.register_command("remind", self.remind_command, "Set a reminder")
        self.register_command("reminders", self.list_reminders, "List your reminders")
    
    def remind_command(self, *args):
        return "Reminder set!"
    
    def list_reminders(self, *args):
        return "You have no reminders."

class SimpleModuleManager:
    def __init__(self):
        self.modules = {}
        print("Initialized module manager")
    
    def register_module(self, module):
        self.modules[module.module_id] = module
        print(f"Registered module: {module.name} ({module.module_id})")
    
    def get_all_modules(self):
        return list(self.modules.values())

# Execute test
if __name__ == "__main__":
    print("Testing simplified module system...")
    
    # Create manager
    manager = SimpleModuleManager()
    
    # Create and register module
    reminder = SimpleReminderModule()
    manager.register_module(reminder)
    
    # Get all modules
    modules = manager.get_all_modules()
    print(f"Registered modules: {len(modules)}")
    
    for module in modules:
        print(f"- {module.name} ({module.module_id})")
        print(f"  Commands: {list(module.get_commands().keys())}")
        print(f"  Description: {module.description}")
    
    print("\nTest completed successfully!") 