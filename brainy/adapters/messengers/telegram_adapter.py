"""
Telegram adapter for Brainy.

This module provides integration with the Telegram API for sending and receiving messages.
"""
import asyncio
import sys
from typing import Optional, Dict, Any, List, Callable
import logging
import traceback
import datetime
import re

from telegram import Update, Bot, BotCommand
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    ContextTypes,
    CallbackContext,
    filters
)

from brainy.utils.logging import get_logger
from brainy.config import settings
from brainy.core.conversation import get_conversation_handler
from brainy.core.character import get_character_manager, CharacterManager
from brainy.core.modules import get_module_manager, ModuleManager
from brainy.core.memory_manager import ConversationMessage, MessageRole

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
def debug(component, message):
    if debug_log:
        if component == "telegram":
            debug_logging.log_telegram(message)
        elif component == "module":
            debug_logging.log_module(message)
        else:
            debug_logging.get_logger().info(f"{component} | {message}")
    # Also log at debug level in standard logger
    logger.debug(message)


class TelegramAdapter:
    """
    Adapter for the Telegram messaging platform.
    
    This adapter handles interaction with the Telegram Bot API,
    including processing messages, commands, and sending responses.
    """
    
    def __init__(self, token: str, conversation_handler=None):
        """
        Initialize the Telegram adapter.
        
        Args:
            token: Telegram bot API token
            conversation_handler: Optional conversation handler to use
                If not provided, will use the default conversation handler
        """
        self.token = token
        self.application: Optional[Application] = None
        self.bot: Optional[Bot] = None
        self._is_setup = False  # Track if setup has been completed
        self._polling_task = None  # Task for polling
        
        # Get the conversation handler
        self._conversation_handler = conversation_handler or get_conversation_handler()
        
        # Get the character manager
        self._character_manager = get_character_manager()
        
        # Get the module manager
        self._module_manager = get_module_manager()
        
        # Set the platform name
        self._platform_name = "telegram"
        
        # Dictionary to map user IDs to chat IDs for reminders
        self._user_chat_map: Dict[str, int] = {}
        
        logger.info("Initialized Telegram adapter")
        debug("telegram", "Telegram adapter initialized")
    
    async def setup(self) -> None:
        """Set up the Telegram bot and register handlers."""
        debug("telegram", "Setting up Telegram bot handlers...")
        
        # Create the application
        self.application = Application.builder().token(self.token).build()
        
        # Get the bot instance
        self.bot = self.application.bot
        
        # Register built-in command handlers
        self.application.add_handler(CommandHandler("start", self._start_command))
        self.application.add_handler(CommandHandler("help", self._help_command))
        self.application.add_handler(CommandHandler("clear", self._clear_command))
        self.application.add_handler(CommandHandler("character", self._character_command))
        self.application.add_handler(CommandHandler("characters", self._list_characters_command))
        self.application.add_handler(CommandHandler("create_character", self._create_character_command))
        self.application.add_handler(CommandHandler("edit_character", self._edit_character_command))
        self.application.add_handler(CommandHandler("delete_character", self._delete_character_command))
        
        # Add explicit handlers for reminder commands - this ensures they're processed directly
        self.application.add_handler(CommandHandler("remind", self._module_command_handler))
        self.application.add_handler(CommandHandler("reminders", self._module_command_handler))
        self.application.add_handler(CommandHandler("clear_reminders", self._module_command_handler))
        
        # Add explicit handler for provider command
        self.application.add_handler(CommandHandler("provider", self._module_command_handler))
        
        # Add explicit handler for debug commands when in debug mode
        if settings.DEBUG:
            self.application.add_handler(CommandHandler("debug_rag", self._module_command_handler))
            logger.info("Registered debug_rag command handler")
            debug("telegram", "Registered debug_rag command handler")
        
        # Register module command handlers for dynamically registered commands
        # We'll catch all commands and route them to modules if applicable
        self.application.add_handler(
            MessageHandler(filters.COMMAND & ~filters.Command(["start", "help", "clear", "character", "characters", 
                                                              "create_character", "edit_character", "delete_character",
                                                              "remind", "reminders", "clear_reminders", "provider"] + 
                                                              (["debug_rag"] if settings.DEBUG else [])), 
                           self._module_command_handler)
        )
        
        # Register message handler
        self.application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, self._message_handler))
        
        # Set up bot commands
        await self._setup_commands()
        
        # Mark setup as complete
        self._is_setup = True
        
        logger.info("Set up Telegram bot handlers")
        debug("telegram", "Telegram bot handlers setup complete")
    
    async def _setup_commands(self) -> None:
        """Set up commands for the Telegram bot."""
        try:
            debug("telegram", "Setting up bot commands...")
            
            # Create a list of commands to register
            commands = [
                BotCommand(command="start", description="Start a conversation with the bot"),
                BotCommand(command="help", description="Show help message"),
                BotCommand(command="clear", description="Clear the conversation history"),
                BotCommand(command="character", description="Change the bot's character"),
                BotCommand(command="characters", description="List available characters"),
                BotCommand(command="create_character", description="Create a new character"),
                BotCommand(command="edit_character", description="Edit an existing character"),
                BotCommand(command="delete_character", description="Delete a character"),
                BotCommand(command="provider", description="View or change AI provider"),
                BotCommand(command="remind", description="Set a reminder"),
                BotCommand(command="reminders", description="List your pending reminders"),
                BotCommand(command="clear_reminders", description="Delete all your reminders")
            ]
            
            # Add debugging commands if in debug mode
            if settings.DEBUG:
                commands.append(BotCommand(command="debug_rag", description="Debug RAG retrieval"))
            
            # Add module commands
            module_commands = self._get_all_module_commands()
            for command, command_info in module_commands.items():
                # Skip commands we've already added explicitly
                if command in ["remind", "reminders", "clear_reminders", "provider", "debug_rag"]:
                    continue
                    
                module, handler_info = command_info
                if isinstance(handler_info, dict) and "description" in handler_info:
                    description = handler_info["description"]
                else:
                    # If handler_info is not a dictionary or doesn't contain description,
                    # use a default description or the module's description
                    description = f"{command} command for {module.name} module"
                
                commands.append(BotCommand(command=command, description=description))
            
            try:
                await self.bot.set_my_commands(commands)
                logger.info(f"Set up {len(commands)} bot commands")
                debug("telegram", f"Registered {len(commands)} bot commands successfully")
            except Exception as e:
                logger.error(f"Failed to set bot commands: {e}")
                if debug_log:
                    debug_logging.log_error("TELEGRAM", f"Failed to set bot commands: {e}", exc_info=True)
        except Exception as e:
            logger.error(f"Error setting up commands: {e}")
            if debug_log:
                debug_logging.log_error("TELEGRAM", f"Error setting up commands: {e}", exc_info=True)
    
    def _get_all_module_commands(self) -> Dict[str, Any]:
        """Get all module commands."""
        module_manager = get_module_manager()
        modules = module_manager.get_enabled_modules()
        
        all_commands = {}
        for module in modules:
            for command, command_info in module.get_commands().items():
                all_commands[command] = (module, command_info)
        
        return all_commands
    
    async def start(self) -> None:
        """Start the Telegram bot."""
        logger.info("Starting Telegram bot")
        debug("telegram", "Starting Telegram bot...")
        
        # Set up handlers and commands if needed
        if not self._is_setup:
            debug("telegram", "Bot not set up yet, initializing...")
            await self.setup()
        
        try:
            # Initialize the application
            debug("telegram", "Initializing application...")
            await self.application.initialize()
            
            # Start the polling process in a separate task
            debug("telegram", "Creating polling task...")
            self._polling_task = asyncio.create_task(self._start_polling())
            
            logger.info("Telegram bot started")
            debug("telegram", "Telegram bot started successfully")
        except Exception as e:
            logger.error(f"Failed to start Telegram bot: {str(e)}", exc_info=True)
            if debug_log:
                debug_logging.log_error("TELEGRAM", f"Failed to start Telegram bot: {str(e)}", exc_info=True)
            # Try to restart after a delay
            await self._delayed_restart(10)

    async def _start_polling(self) -> None:
        """Start polling for updates."""
        try:
            # Delete any existing webhook to ensure polling works
            print("[DEBUG] Deleting any existing webhook...")
            debug("telegram", "Deleting any existing webhook to ensure polling works")
            await self.bot.delete_webhook(drop_pending_updates=False)
            print("[DEBUG] Webhook deleted successfully")
            
            # Force update the handlers registry to ensure our handlers are registered
            print("[DEBUG] Refreshing handlers registry...")
            self.application.update_persistence()
            print("[DEBUG] Handlers registry refreshed")
            
            # Debug helper to see all updates
            async def process_update(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
                update_str = str(update)
                debug("telegram", f"RAW UPDATE RECEIVED: {update_str}")
                # Print to stdout as well to ensure we're seeing it
                print(f"\n[TELEGRAM RAW UPDATE] {update_str}\n")
                
                # Log update details
                update_type = "unknown"
                if update.message:
                    update_type = "message"
                    debug("telegram", f"Message text: '{update.message.text}'")
                    debug("telegram", f"From user ID: {update.effective_user.id}")
                elif update.edited_message:
                    update_type = "edited_message"
                elif update.callback_query:
                    update_type = "callback_query"
                
                debug("telegram", f"Update type: {update_type}")
                print(f"[DEBUG] Processing update of type: {update_type}")
            
            # Add a handler that will catch all updates for debugging with highest priority
            print("[DEBUG] Registering ALL-UPDATES debug handler...")
            self.application.add_handler(MessageHandler(filters.ALL, process_update), group=-999)
            print(f"[DEBUG] Handlers registered: {len(self.application.handlers)}")
            
            # Add a direct print of the first few handlers for debugging
            for group_id, handlers_group in list(self.application.handlers.items())[:2]:
                print(f"[DEBUG] Handler group {group_id}: {len(handlers_group)} handlers")
                for handler in handlers_group[:2]:  # Only show first 2 per group
                    print(f"[DEBUG]   - {handler.__class__.__name__}")
            
            # Start polling in a non-blocking way
            debug("telegram", "Starting polling...")
            print("[DEBUG] Starting Telegram polling now...")
            
            # Configure polling with more debugging
            print("[DEBUG] Starting updater with these settings:")
            print("[DEBUG]   - allowed_updates: ALL_TYPES")
            print("[DEBUG]   - drop_pending_updates: False")
            print("[DEBUG]   - read_timeout: 30s")
            
            # START THE APPLICATION - this is critical for v21.x
            # This starts the process that takes updates from the queue and sends them to handlers
            print("[DEBUG] Starting application to process updates...")
            await self.application.start()
            print("[DEBUG] Application started successfully")
            
            # Now start the updater to fetch updates
            await self.application.updater.start_polling(
                allowed_updates=Update.ALL_TYPES,
                drop_pending_updates=False,
                read_timeout=30,
                write_timeout=30,
                connect_timeout=30,
                pool_timeout=30,
                bootstrap_retries=5
            )
            
            logger.info("[DEBUG] Polling started successfully, waiting for messages...")
            debug("telegram", "Polling started successfully, waiting for messages...")
            print("[DEBUG] Telegram polling is active and waiting for messages...")
            bot_info = await self.bot.get_me()
            print(f"[DEBUG] Bot info: {bot_info.first_name} (@{bot_info.username}) ID:{bot_info.id}")
            
            # Keep the task alive
            while True:
                await asyncio.sleep(10)
                print(f"[DEBUG] Still polling for Telegram updates as @{self.bot.username}...")
                debug("telegram", f"Still polling for updates as @{self.bot.username}")
                
                # Try to peek at the update queue to see if there's anything there
                try:
                    queue_size = self.application.update_queue.qsize()
                    print(f"[DEBUG] Update queue size: {queue_size}")
                    if queue_size > 0:
                        print("[DEBUG] There are updates in the queue that are not being processed!")
                except Exception as e:
                    print(f"[DEBUG] Could not check queue size: {e}")
                
        except Exception as e:
            logger.error(f"Error in Telegram polling: {str(e)}", exc_info=True)
            print(f"[DEBUG] CRITICAL ERROR IN POLLING: {str(e)}")
            print(f"[DEBUG] Full error: {traceback.format_exc()}")
            if debug_log:
                debug_logging.log_error("TELEGRAM", f"Error in Telegram polling: {str(e)}", exc_info=True)
            # Try to restart after a delay
            await self._delayed_restart(10)
        finally:
            # Ensure application and updater are both stopped correctly
            if self.application is not None:
                print("[DEBUG] Stopping application and updater...")
                try:
                    await self.application.stop()
                    if hasattr(self.application, 'updater'):
                        await self.application.updater.stop()
                    print("[DEBUG] Application and updater stopped successfully")
                except Exception as e:
                    print(f"[DEBUG] Error stopping application: {e}")
            
            logger.info("Telegram polling stopped")
            debug("telegram", "Telegram polling stopped")

    async def _delayed_restart(self, delay_seconds: int) -> None:
        """Attempt to restart the bot after a delay."""
        logger.info(f"Will attempt to restart Telegram bot in {delay_seconds} seconds")
        await asyncio.sleep(delay_seconds)
        try:
            # Reset the application
            self.application = None
            self.bot = None
            
            # Try to start again
            await self.start()
        except Exception as e:
            logger.error(f"Failed to restart Telegram bot: {e}")

    async def stop(self) -> None:
        """Stop the Telegram bot."""
        logger.info("Stopping Telegram bot")
        print("[DEBUG] Stopping Telegram bot...")
        
        # Cancel the polling task if it's running
        if hasattr(self, '_polling_task') and self._polling_task is not None:
            print("[DEBUG] Cancelling polling task...")
            self._polling_task.cancel()
            try:
                await self._polling_task
            except asyncio.CancelledError:
                pass
            self._polling_task = None
            print("[DEBUG] Polling task cancelled")
        
        # Stop the application if it's running
        if self.application is not None:
            try:
                # In v21.x, the order is important: first stop the updater, then the application
                print("[DEBUG] Stopping application...")
                
                # Stop the updater if it's running
                if hasattr(self.application, 'updater'):
                    print("[DEBUG] Stopping updater...")
                    await self.application.updater.stop()
                    print("[DEBUG] Updater stopped")
                
                # Shutdown the application
                await self.application.stop()
                print("[DEBUG] Application stopped")
                
                logger.info("Telegram bot stopped")
            except Exception as e:
                logger.error(f"Error stopping Telegram bot: {str(e)}", exc_info=True)
                print(f"[DEBUG] Error stopping Telegram bot: {str(e)}")
                if debug_log:
                    debug_logging.log_error("TELEGRAM", f"Error stopping Telegram bot: {str(e)}", exc_info=True)
    
    async def _start_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Handle the /start command."""
        if update.effective_chat is None or update.effective_user is None:
            return
        
        user_id = str(update.effective_user.id)
        chat_id = update.effective_chat.id
        
        # Store the user's chat ID for reminders
        self._user_chat_map[user_id] = chat_id
        
        # Get the default character
        character = self._character_manager.get_default_character()
        
        greeting = character.greeting or f"Hello! I'm {character.name}. How can I help you today?"
        
        await context.bot.send_message(chat_id=chat_id, text=greeting)
        
        logger.info(f"User {user_id} started a conversation")
    
    async def _help_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """
        Handle the /help command to display available commands.
        
        Args:
            update: The update object containing information about the incoming message.
            context: The context object for the callback.
        """
        debug("telegram", "Handling /help command")
        
        # Build help message
        help_text = (
            "🤖 *Brainy Bot Commands*\n\n"
            "*Basic Commands:*\n"
            "/start - Start a conversation with the bot\n"
            "/help - Show this help message\n"
            "/clear - Clear the current conversation history\n\n"
            
            "*Character Commands:*\n"
            "/character <id> - Switch to a specific character\n"
            "/characters - List all available characters\n"
            "/create_character - Create a new character\n"
            "/edit_character - Edit an existing character\n"
            "/delete_character <id> - Delete a character\n\n"
            
            "*AI Provider Commands:*\n"
            "/provider - View or change the AI provider\n\n"
            
            "*Other Features:*\n"
            "• You can create reminders by typing \"remind me to...\"\n"
            "• Use /reminders to see your pending reminders\n"
            "• Use /clear_reminders to clear all your reminders\n\n"
            
            "For more detailed help on a specific command, type the command without any arguments."
        )
        
        await update.message.reply_text(help_text, parse_mode="Markdown")
    
    async def _clear_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Handle the /clear command."""
        if update.effective_chat is None or update.effective_user is None:
            return
        
        user_id = str(update.effective_user.id)
        chat_id = update.effective_chat.id
        
        # Clear the conversation
        await self._conversation_handler.clear_conversation(user_id, self._platform_name)
        
        await context.bot.send_message(chat_id=chat_id, text="Conversation cleared. Let's start fresh!")
        
        logger.info(f"User {user_id} cleared their conversation")
    
    async def _character_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Handle the /character command."""
        if update.effective_chat is None or update.effective_user is None:
            return
        
        user_id = str(update.effective_user.id)
        chat_id = update.effective_chat.id
        
        # If no character ID is provided, show the current character
        if not context.args or len(context.args) < 1:
            # Get the current character for this user
            conversation_id = f"{self._platform_name}:{user_id}"
            current_character = self._character_manager.get_character_for_conversation(conversation_id)
            
            await context.bot.send_message(
                chat_id=chat_id,
                text=f"Current character: {current_character.name} (ID: {current_character.character_id})\n\n"
                     f"Description: {current_character.description}\n\n"
                     f"To change character, use /character ID\n"
                     f"For example: /character professor\n"
                     f"To see available characters, use /characters"
            )
            return
        
        # Strip any leading slash if someone types "/character /name" instead of "/character name"
        # Also remove any angle brackets if user included them (e.g., /character <professor>)
        character_id = context.args[0].lstrip('/').strip('<>')
        
        # Check if trying to switch to the same character
        conversation_id = f"{self._platform_name}:{user_id}"
        current_character = self._character_manager.get_character_for_conversation(conversation_id)
        if current_character.character_id.lower() == character_id.lower():
            await context.bot.send_message(
                chat_id=chat_id,
                text=f"You're already using the '{current_character.name}' character."
            )
            return
        
        # Change the character
        character = await self._conversation_handler.change_character(
            user_id, self._platform_name, character_id
        )
        
        if character is None:
            await context.bot.send_message(
                chat_id=chat_id,
                text=f"❌ Character '{character_id}' not found. Use /characters to see available characters."
            )
            return
        
        # Clear the conversation and add the system message for the new character
        await self._conversation_handler.clear_conversation(user_id, self._platform_name)
        
        # Send the greeting for the new character
        greeting = character.greeting or f"Hello! I'm now using the {character.name} character. How can I help you today?"
        
        await context.bot.send_message(
            chat_id=chat_id, 
            text=f"✅ *Successfully switched to character: {character.name}*\n\n{greeting}",
            parse_mode="Markdown"
        )
        
        logger.info(f"User {user_id} changed character to '{character.name}'")
    
    async def _list_characters_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Handle the /characters command."""
        if update.effective_chat is None or update.effective_user is None:
            return
        
        chat_id = update.effective_chat.id
        user_id = str(update.effective_user.id)
        
        # Get the current character for this user
        conversation_id = f"{self._platform_name}:{user_id}"
        current_character = self._character_manager.get_character_for_conversation(conversation_id)
        
        # Get all available characters
        characters = self._character_manager.get_all_characters()
        
        if not characters:
            await context.bot.send_message(chat_id=chat_id, text="No characters available.")
            return
        
        # Format the character list
        character_list = "🎭 **Available Characters** 🎭\n\n"
        
        for character in characters:
            # Check if this is the current character
            is_current = character.character_id == current_character.character_id
            prefix = "✅ " if is_current else "   "
            
            character_list += f"{prefix}**{character.name}** (ID: `{character.character_id}`)\n"
            character_list += f"   *{character.description}*\n"
            
            # Only show a preview of the system prompt (first 50 chars)
            system_preview = character.system_prompt[:50] + "..." if len(character.system_prompt) > 50 else character.system_prompt
            character_list += f"   System: {system_preview}\n\n"
        
        character_list += "To switch character, use `/character ID`\n"
        character_list += "Examples: `/character professor`, `/character ara`\n"
        character_list += "To see your current character details, use `/character`"
        
        # Send message with markdown parsing
        await context.bot.send_message(
            chat_id=chat_id, 
            text=character_list,
            parse_mode='Markdown'
        )
    
    async def _module_command_handler(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Handle commands that are processed by modules."""
        if not update.effective_user or not update.message or not update.message.text or not update.effective_chat:
            logger.warning("Received command without required data")
            debug("telegram", "Received command without required data")
            return
        
        user_id = str(update.effective_user.id)
        message_text = update.message.text
        chat_id = update.effective_chat.id
        
        print(f"[DEBUG] Processing module command: {message_text}")
        logger.info(f"Processing module command from user {user_id}: {message_text}")
        debug("telegram", f"Processing module command from user {user_id}: {message_text}")
        
        # Store the chat ID for this user (used for sending messages later)
        self._user_chat_map[user_id] = chat_id
        debug("telegram", f"Stored chat ID {chat_id} for user {user_id}")
        
        # Check if this is a debug_rag command - add special logging
        is_debug_rag = message_text.startswith('/debug_rag')
        if is_debug_rag:
            print(f"[DEBUG] Processing debug_rag command: {message_text}")
            logger.info(f"Processing debug_rag command from user {user_id}: {message_text}")
            debug("telegram", f"Processing debug_rag command from user {user_id}: {message_text}")
        
        try:
            # Parse the command
            command, args = self._module_manager.parse_command(message_text)
            print(f"[DEBUG] Parsed command: '{command}' with args: {args}")
            
            if is_debug_rag:
                print(f"[DEBUG] Parsed debug_rag command with args: {args}")
            
            # Print all available module commands
            all_module_commands = self._get_all_module_commands()
            print(f"[DEBUG] Available module commands: {list(all_module_commands.keys())}")
            
            # Check if the command is handled by a module
            if command in all_module_commands:
                print(f"[DEBUG] Command '{command}' is registered, processing it")
                # Show typing indicator
                await context.bot.send_chat_action(chat_id=chat_id, action="typing")
                
                # Create a conversation message object
                # Use the correct format for conversation_id (platform:user_id)
                conversation_id = f"{self._platform_name}:{user_id}"
                conv_message = ConversationMessage(
                    role=MessageRole.USER,
                    content=message_text,
                    metadata={
                        "user_id": user_id,
                        "platform": self._platform_name,
                        "conversation_id": conversation_id
                    }
                )
                
                # Process the command with the module manager
                print(f"[DEBUG] Calling module_manager.process_command for '{command}'")
                response = await self._module_manager.process_command(conv_message)
                print(f"[DEBUG] Module response: {response}")
                
                if response:
                    print(f"[DEBUG] Sending response: {response[:50]}...")
                    await context.bot.send_message(
                        chat_id=chat_id, 
                        text=response,
                        parse_mode='Markdown'  # Enable markdown parsing for responses
                    )
                    logger.info(f"Sent module command response to user {user_id}")
                    debug("telegram", f"Sent module command response to user {user_id}")
                else:
                    print(f"[DEBUG] No response received from module")
                    await context.bot.send_message(
                        chat_id=chat_id,
                        text="I'm sorry, I couldn't process that command."
                    )
            else:
                print(f"[DEBUG] Command '{command}' not found in module commands")
                logger.warning(f"Unknown command: {command}")
                await context.bot.send_message(
                    chat_id=chat_id,
                    text=f"Unknown command: {command}. Type /help to see available commands."
                )
        except Exception as e:
            print(f"[DEBUG] Error processing module command: {str(e)}")
            print(f"[DEBUG] Traceback: {traceback.format_exc()}")
            logger.error(f"Error processing module command: {str(e)}", exc_info=True)
            if debug_log:
                debug_logging.log_error("TELEGRAM", f"Error processing module command: {str(e)}", exc_info=True)
            await context.bot.send_message(
                chat_id=chat_id,
                text="I'm sorry, I encountered an error while processing your command. Please try again later."
            )
    
    async def _message_handler(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Handle regular messages."""
        # Ensure we have all the required data
        if not update.effective_user or not update.message or not update.message.text or not update.effective_chat:
            logger.warning("Received message without required data")
            debug("telegram", "Received message without required data")
            return
        
        user_id = str(update.effective_user.id)
        message_text = update.message.text
        chat_id = update.effective_chat.id
        
        logger.info(f"Received message from user {user_id}: '{message_text}'")
        debug("telegram", f"RECEIVED MESSAGE from user {user_id}: '{message_text}'")
        
        try:
            # Show typing indicator
            debug("telegram", f"Sending typing indicator to chat {chat_id}")
            await context.bot.send_chat_action(
                chat_id=chat_id, 
                action="typing"
            )
            
            # Store the chat ID for this user (used for sending messages later)
            self._user_chat_map[user_id] = chat_id
            debug("telegram", f"Stored chat ID {chat_id} for user {user_id}")
            
            # SIMPLIFIED APPROACH: Direct processing without complex module matching
            debug("telegram", f"Forwarding message to conversation handler")
            
            # Process the message with the conversation handler
            response = await self._conversation_handler.process_user_message(
                user_id=user_id,
                platform="telegram",
                message_text=message_text
            )
            
            debug("telegram", f"Got response from conversation handler: '{response[:50]}...'")
            
            # Send the response back to the user
            debug("telegram", f"Sending response to chat {chat_id}")
            await context.bot.send_message(chat_id=chat_id, text=response)
            logger.info(f"Sent response to user {user_id}")
            debug("telegram", f"Sent response to user {user_id}")
            
        except Exception as e:
            logger.error(f"Error processing message: {str(e)}", exc_info=True)
            if debug_log:
                debug_logging.log_error("TELEGRAM", f"Error processing message: {str(e)}", exc_info=True)
            # Send an error message to the user
            await context.bot.send_message(
                chat_id=chat_id,
                text=f"I'm sorry, I encountered an error while processing your message: {str(e)}"
            )
    
    async def send_reminder(self, user_id: str, task: str) -> bool:
        """
        Send a reminder to a user.
        
        Args:
            user_id: ID of the user to remind
            task: Task to remind about
            
        Returns:
            True if the reminder was sent, False otherwise
        """
        # Check if we have a chat ID for this user
        if user_id not in self._user_chat_map:
            logger.error(f"No chat ID for user {user_id}, cannot send reminder")
            if debug_log:
                debug_logging.log_error("TELEGRAM", f"No chat ID for user {user_id}, cannot send reminder")
            return False
        
        chat_id = self._user_chat_map[user_id]
        
        try:
            # Current time for timestamp
            current_time = datetime.datetime.now().strftime("%I:%M %p")
            
            # Format the reminder message
            reminder_text = (
                f"⏰ **Reminder!**\n\n"
                f"You asked me to remind you to:\n"
                f"\"{task}\"\n\n"
                f"Time: {current_time}\n\n"
                f"_To set another reminder, use /remind_"
            )
            
            # Log that we're sending a reminder
            logger.info(f"Attempting to send reminder to user {user_id} at chat {chat_id}")
            print(f"[DEBUG] Sending reminder to chat {chat_id}: {task}")
            
            if debug_log:
                debug_logging.log_telegram(f"Sending reminder: '{task}' to user {user_id} at chat {chat_id}")
            
            # Send the message
            if self.bot:
                await self.bot.send_message(
                    chat_id=chat_id, 
                    text=reminder_text,
                    parse_mode='Markdown'
                )
                logger.info(f"Successfully sent reminder to user {user_id}: {task}")
                if debug_log:
                    debug_logging.log_telegram(f"Successfully sent reminder: '{task}' to user {user_id}")
                return True
            else:
                logger.error("Bot not initialized, cannot send reminder")
                if debug_log:
                    debug_logging.log_error("TELEGRAM", "Bot not initialized, cannot send reminder")
                return False
        except Exception as e:
            logger.error(f"Error sending reminder to user {user_id}: {str(e)}", exc_info=True)
            if debug_log:
                debug_logging.log_error("TELEGRAM", f"Error sending reminder to user {user_id}: {str(e)}", exc_info=True)
            print(f"[DEBUG] Error sending reminder: {str(e)}")
            print(f"[DEBUG] {traceback.format_exc()}")
            return False

    async def _create_character_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """
        Handle the /create_character command to create a new character.
        
        Format: /create_character id=<id> name=<n> prompt=<system_prompt> [description=<description>] [greeting=<greeting>] [farewell=<farewell>]
        
        Args:
            update: The update object containing information about the incoming message.
            context: The context object for the callback.
        """
        debug("telegram", "Handling /create_character command")
        
        # Get the command arguments
        if not context.args:
            detailed_help = (
                "🎭 **Character Creation**\n\n"
                "Create a new AI character with a custom personality.\n\n"
                "**Usage:**\n"
                "`/create_character id=ID name=\"Name\" prompt=\"System prompt\" [description=\"Description\"] [greeting=\"Greeting\"] [farewell=\"Farewell\"]`\n\n"
                "**Required Parameters:**\n"
                "• `id` - A unique identifier (letters, numbers, underscores only)\n"
                "• `name` - The display name of the character\n"
                "• `prompt` - System prompt defining personality and behavior\n\n"
                "**Optional Parameters:**\n"
                "• `description` - Short description of the character\n"
                "• `greeting` - Custom greeting message\n"
                "• `farewell` - Custom farewell message\n"
                "• `avatar` - URL to an avatar image\n\n"
                "**Examples:**\n"
                "Simple character:\n"
                "`/create_character id=doctor name=\"Dr. Health\" prompt=\"You are a helpful medical assistant who provides general health advice.\"`\n\n"
                "Detailed character:\n"
                "`/create_character id=chef name=\"Chef Bot\" prompt=\"You are a helpful chef assistant.\" description=\"A cooking expert\" greeting=\"Hello, chef here!\" farewell=\"Bon appetit!\"`"
            )
            await update.message.reply_text(detailed_help, parse_mode="Markdown")
            return
        
        # Join the arguments into a single string
        args_text = " ".join(context.args)
        
        # Parse the arguments into a dictionary
        # We need to handle quoted values that might contain spaces
        params = {}
        current_key = None
        current_value = ""
        in_quotes = False
        
        # Add a space at the end to ensure the last key-value pair is processed
        args_text += " "
        
        for char in args_text:
            if char == "=" and not in_quotes and current_key is None:
                # End of key
                current_key = current_value.strip()
                current_value = ""
            elif char == '"':
                # Toggle quote state
                in_quotes = not in_quotes
            elif char.isspace() and not in_quotes and current_key is not None:
                # End of value
                params[current_key] = current_value.strip()
                current_key = None
                current_value = ""
            else:
                # Add to current token
                current_value += char
        
        # Check if we have the required parameters
        required_params = ["id", "name", "prompt"]
        missing_params = [param for param in required_params if param not in params]
        
        if missing_params:
            await update.message.reply_text(
                f"❌ Missing required parameters: {', '.join(missing_params)}\n\n"
                f"Use /create_character without arguments to see usage instructions."
            )
            return
        
        # Get the parameters
        character_id = params["id"]
        name = params["name"]
        system_prompt = params["prompt"]
        description = params.get("description", "")
        greeting = params.get("greeting")
        farewell = params.get("farewell")
        avatar_url = params.get("avatar")
        
        # Validate character ID
        if not character_id.isalnum() and not "_" in character_id:
            await update.message.reply_text(
                "❌ Character ID must contain only letters, numbers, and underscores."
            )
            return
        
        try:
            # Create the character
            character_manager = self._character_manager
            new_character = character_manager.create_character(
                character_id=character_id,
                name=name,
                system_prompt=system_prompt,
                description=description,
                greeting=greeting,
                farewell=farewell,
                avatar_url=avatar_url
            )
            
            if new_character:
                await update.message.reply_text(
                    f"✅ Character '{name}' (ID: {character_id}) created successfully!\n\n"
                    f"You can switch to this character with:\n"
                    f"`/character {character_id}`"
                , parse_mode="Markdown")
            else:
                await update.message.reply_text(f"❌ Error creating character: A character with ID '{character_id}' already exists.")
            
        except ValueError as e:
            await update.message.reply_text(f"❌ Error creating character: {str(e)}")
        except Exception as e:
            logger.error(f"Error creating character: {str(e)}")
            await update.message.reply_text("❌ An error occurred while creating the character. Please try again.")

    async def _edit_character_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """
        Handle the /edit_character command to edit an existing character.
        
        Format: /edit_character id=<id> [name=<name>] [prompt=<system_prompt>] [description=<description>] [greeting=<greeting>] [farewell=<farewell>]
        
        Args:
            update: The update object containing information about the incoming message.
            context: The context object for the callback.
        """
        debug("telegram", "Handling /edit_character command")
        
        # Get the command arguments
        if not context.args:
            detailed_help = (
                "🎭 **Edit Character**\n\n"
                "Modify properties of an existing character.\n\n"
                "**Usage:**\n"
                "`/edit_character id=character_id [name=\"New Name\"] [prompt=\"New System Prompt\"] [description=\"New Description\"] [greeting=\"New Greeting\"] [farewell=\"New Farewell\"]`\n\n"
                "**Required Parameters:**\n"
                "• `id` - Identifier of the character to edit\n\n"
                "**Optional Parameters:** (at least one required)\n"
                "• `name` - New display name\n"
                "• `prompt` - New system prompt\n"
                "• `description` - New description\n"
                "• `greeting` - New greeting message\n"
                "• `farewell` - New farewell message\n"
                "• `avatar` - New avatar URL\n\n"
                "**Examples:**\n"
                "Change name:\n"
                "`/edit_character id=chef name=\"Master Chef\"`\n\n"
                "Change prompt and greeting:\n"
                "`/edit_character id=professor prompt=\"You are a helpful math teacher.\" greeting=\"Hello! Ready to learn some math?\"`"
            )
            await update.message.reply_text(detailed_help, parse_mode="Markdown")
            return
        
        # Parse the command arguments
        # We need to join all args first because some values might contain spaces
        args_text = " ".join(context.args)
        
        # Parse key=value pairs
        # This regex handles both quoted and unquoted values
        pattern = r'(\w+)=(?:"([^"]*)"|([^ ]*))'
        matches = re.findall(pattern, args_text)
        
        params = {}
        for match in matches:
            key, quoted_value, unquoted_value = match
            value = quoted_value if quoted_value else unquoted_value
            params[key] = value
        
        # Check required parameters
        if "id" not in params:
            await update.message.reply_text(
                "❌ Missing required parameter: id\n\n"
                "The id parameter is required to identify which character to edit.\n"
                "Example: `/edit_character id=chef name=\"New Name\"`\n\n"
                "Type `/edit_character` without arguments for detailed help."
            , parse_mode="Markdown")
            return
        
        # Check if at least one optional parameter is provided
        if len(params) < 2:  # Only id is provided
            await update.message.reply_text(
                "❌ You must provide at least one parameter to update.\n\n"
                "For example: `/edit_character id=chef name=\"New Name\"`\n\n"
                "Type `/edit_character` without arguments for detailed help."
            , parse_mode="Markdown")
            return
        
        # Map the parameters to the edit_character method arguments
        character_id = params.pop("id")
        
        # Rename keys to match the edit_character method parameters
        if "prompt" in params:
            params["system_prompt"] = params.pop("prompt")
        if "avatar" in params:
            params["avatar_url"] = params.pop("avatar")
        
        try:
            # Use the existing character manager
            character_manager = self._character_manager
            
            # Check if the character exists first
            if not character_manager.get_character(character_id):
                await update.message.reply_text(
                    f"❌ Character with ID '{character_id}' does not exist.\n\n"
                    f"Use `/characters` to see available characters."
                , parse_mode="Markdown")
                return
                
            # Edit the character
            updated_character = character_manager.edit_character(character_id=character_id, **params)
            
            if updated_character:
                await update.message.reply_text(
                    f"✅ Character '{updated_character.name}' (ID: {character_id}) updated successfully!\n\n"
                    f"Updated fields: {', '.join(params.keys())}\n\n"
                    f"Switch to this character with:\n"
                    f"`/character {character_id}`"
                , parse_mode="Markdown")
            else:
                await update.message.reply_text(f"❌ Failed to update character (ID: {character_id})")
            
        except ValueError as e:
            await update.message.reply_text(f"❌ Error updating character: {str(e)}")
        except Exception as e:
            logger.error(f"Error updating character: {str(e)}")
            await update.message.reply_text("❌ An error occurred while updating the character. Please try again.")

    async def _delete_character_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """
        Handle the /delete_character command to delete an existing character.
        
        Format: /delete_character <character_id>
        
        Args:
            update: The update object containing information about the incoming message.
            context: The context object for the callback.
        """
        debug("telegram", "Handling /delete_character command")
        
        # Get the command arguments
        if not context.args or len(context.args) != 1:
            detailed_help = (
                "🗑️ **Delete Character**\n\n"
                "Remove an existing character from the system.\n\n"
                "**Usage:**\n"
                "`/delete_character character_id`\n\n"
                "The character ID should match one of the characters shown in the `/characters` list.\n\n"
                "**Notes:**\n"
                "• You cannot delete the default character\n"
                "• This action cannot be undone\n"
                "• If you delete the character you're currently using, you'll be switched to the default character\n\n"
                "**Example:**\n"
                "`/delete_character chef`"
            )
            await update.message.reply_text(detailed_help, parse_mode="Markdown")
            return
        
        # Get the character ID (remove any leading slash if present)
        character_id = context.args[0].lstrip('/').strip('<>')
        
        try:
            # Use the existing character manager instance
            character_manager = self._character_manager
            
            # Get the character first to show its name in the success message
            character = character_manager.get_character(character_id)
            if not character:
                await update.message.reply_text(
                    f"❌ Character '{character_id}' not found.\n\n"
                    f"Use `/characters` to see a list of available characters."
                , parse_mode="Markdown")
                return
                
            # Remember the name for the success message
            character_name = character.name
            
            # Delete the character
            result = character_manager.delete_character(character_id=character_id)
            if result:
                await update.message.reply_text(
                    f"✅ Character '{character_name}' (ID: {character_id}) deleted successfully!"
                )
            else:
                # This shouldn't happen often since we checked the character exists
                await update.message.reply_text(
                    f"❌ Failed to delete character '{character_id}'. It may be the default character which cannot be deleted."
                )
            
        except ValueError as e:
            await update.message.reply_text(f"❌ Error deleting character: {str(e)}")
        except Exception as e:
            logger.error(f"Error deleting character: {str(e)}")
            await update.message.reply_text("❌ An error occurred while deleting the character. Please try again.")


# Singleton instance
_telegram_adapter: Optional[TelegramAdapter] = None


def get_telegram_adapter() -> TelegramAdapter:
    """
    Get the Telegram adapter instance.
    
    Returns:
        The Telegram adapter instance
    """
    global _telegram_adapter
    if _telegram_adapter is None:
        token = settings.TELEGRAM_BOT_TOKEN
        if not token:
            raise ValueError("TELEGRAM_BOT_TOKEN is not set in environment variables")
        
        _telegram_adapter = TelegramAdapter(token)
    
    return _telegram_adapter 