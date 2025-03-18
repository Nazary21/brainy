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
from brainy.core.character import get_character_manager
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
        
        # Add explicit handlers for reminder commands - this ensures they're processed directly
        self.application.add_handler(CommandHandler("remind", self._module_command_handler))
        self.application.add_handler(CommandHandler("reminders", self._module_command_handler))
        self.application.add_handler(CommandHandler("clear_reminders", self._module_command_handler))
        
        # Register module command handlers for dynamically registered commands
        # We'll catch all commands and route them to modules if applicable
        self.application.add_handler(
            MessageHandler(filters.COMMAND & ~filters.Command(["start", "help", "clear", "character", "characters", 
                                                              "remind", "reminders", "clear_reminders"]), 
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
                BotCommand(command="characters", description="List available characters")
            ]
            
            # Add module commands
            module_commands = self._get_all_module_commands()
            for command, command_info in module_commands.items():
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
        """Handle the /help command."""
        if update.effective_chat is None:
            return
        
        chat_id = update.effective_chat.id
        
        # Basic help text
        help_text = (
            "I'm Brainy, your friendly AI assistant! Here's what you can do:\n\n"
            "/start - Start a conversation with me\n"
            "/help - Show this help message\n"
            "/clear - Clear our conversation history\n"
            "/character <id> - Change my character (e.g., /character default)\n"
            "/characters - List available characters\n\n"
        )
        
        # Add module commands to help text
        if self._module_manager.get_all_modules():
            help_text += "Module commands:\n"
            
            for module in self._module_manager.get_all_modules():
                for command, command_info in module.get_commands().items():
                    help_text += f"/{command} - {command_info['description']}\n"
            
            help_text += "\n"
        
        help_text += "Just send me a message and I'll respond!"
        
        await context.bot.send_message(chat_id=chat_id, text=help_text)
    
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
                     f"To change character, use /character <id>\n"
                     f"To see available characters, use /characters"
            )
            return
        
        character_id = context.args[0]
        
        # Check if trying to switch to the same character
        conversation_id = f"{self._platform_name}:{user_id}"
        current_character = self._character_manager.get_character_for_conversation(conversation_id)
        if current_character.character_id == character_id:
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
                text=f"Character '{character_id}' not found. Use /characters to see available characters."
            )
            return
        
        # Clear the conversation and add the system message for the new character
        await self._conversation_handler.clear_conversation(user_id, self._platform_name)
        
        # Send the greeting for the new character
        greeting = character.greeting or f"Hello! I'm now using the {character.name} character. How can I help you today?"
        
        await context.bot.send_message(
            chat_id=chat_id, 
            text=f"✅ Character changed to: {character.name}\n\n{greeting}"
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
        
        character_list += "To switch character, use `/character <id>`\n"
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
        
        try:
            # Parse the command
            command, args = self._module_manager.parse_command(message_text)
            print(f"[DEBUG] Parsed command: '{command}' with args: {args}")
            
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