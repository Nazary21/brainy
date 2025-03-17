"""
Simple test script to verify our module system works.
"""
import sys
import os

# Add the current directory to the Python path
sys.path.append(os.getcwd())

try:
    from brainy.core.modules.base import Module, ModuleManager, get_module_manager
    from brainy.core.modules.reminder import ReminderModule, create_reminder_module
    
    # Create a module manager
    module_manager = get_module_manager()
    
    # Create a reminder module
    reminder_module = create_reminder_module()
    
    # Register the module
    module_manager.register_module(reminder_module)
    
    # Get all modules
    modules = module_manager.get_all_modules()
    
    print("Successfully imported and created module system components!")
    print(f"Registered modules: {len(modules)}")
    for module in modules:
        print(f"- {module.name} ({module.module_id})")
        print(f"  Commands: {list(module.get_commands().keys())}")
        print(f"  Description: {module.description}")
        print()
    
except Exception as e:
    print(f"Error: {e}")
    import traceback
    traceback.print_exc() 