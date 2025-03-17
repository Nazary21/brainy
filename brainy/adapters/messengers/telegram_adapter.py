"""
Telegram adapter for Brainy.

This module provides integration with the Telegram API for sending and receiving messages.
"""
import asyncio
from typing import Optional, Dict, Any, List, Callable
import logging

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
from brainy.core.memory_manager import ConversationMessage

# Initialize logger
logger = get_logger(__name__)


class TelegramAdapter:
    """
    Adapter for the Telegram messaging platform.
    
    This adapter handles interaction with the Telegram Bot API,
    including processing messages, commands, and sending responses.
    """
    
    def __init__(self, token: str):
        """
        Initialize the Telegram adapter.
        
        Args:
            token: Telegram bot API token
        """
        self.token = token
        self.application: Optional[Application] = None
        self.bot: Optional[Bot] = None
        
        # Get the conversation handler
        self._conversation_handler = get_conversation_handler()
        
        # Get the character manager
        self._character_manager = get_character_manager()
        
        # Get the module manager
        self._module_manager = get_module_manager()
        
        # Set the platform name
        self._platform_name = "telegram"
        
        # Dictionary to map user IDs to chat IDs for reminders
        self._user_chat_map: Dict[str, int] = {}
        
        logger.info("Initialized Telegram adapter")
    
    async def setup(self) -> None:
        """Set up the Telegram bot and register handlers."""
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
        
        # Register module command handlers for dynamically registered commands
        # We'll catch all commands and route them to modules if applicable
        self.application.add_handler(
            MessageHandler(filters.COMMAND & ~filters.Command(["start", "help", "clear", "character", "characters"]), 
                           self._module_command_handler)
        )
        
        # Register message handler
        self.application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, self._message_handler))
        
        # Set up bot commands
        await self._setup_commands()
        
        logger.info("Set up Telegram bot handlers")
    
    async def _setup_commands(self) -> None:
        """Set up commands for the Telegram bot."""
        try:
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
            except Exception as e:
                logger.error(f"Failed to set bot commands: {e}")
        except Exception as e:
            logger.error(f"Error setting up commands: {e}")
    
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
        try:
            if self.application is None:
                await self.setup()
            
            # Start polling in a background task
            await self.application.initialize()
            await self.application.updater.start_polling(allowed_updates=Update.ALL_TYPES)
            
            logger.info("Started Telegram bot - now listening for messages")
        except Exception as e:
            logger.error(f"Failed to start Telegram bot: {e}")
            # Try to restart after a delay if there was an error
            asyncio.create_task(self._delayed_restart(10))
    
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
        if self.application is not None:
            await self.application.stop()
            logger.info("Stopped Telegram bot")
    
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
        
        # Get the character ID from arguments
        if not context.args or len(context.args) < 1:
            await context.bot.send_message(
                chat_id=chat_id,
                text="Please specify a character ID. Use /characters to see available characters."
            )
            return
        
        character_id = context.args[0]
        
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
        greeting = character.greeting or f"Hello! I'm {character.name}. How can I help you today?"
        
        await context.bot.send_message(chat_id=chat_id, text=greeting)
        
        logger.info(f"User {user_id} changed character to '{character.name}'")
    
    async def _list_characters_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Handle the /characters command."""
        if update.effective_chat is None:
            return
        
        chat_id = update.effective_chat.id
        
        # Get all available characters
        characters = self._character_manager.get_all_characters()
        
        if not characters:
            await context.bot.send_message(chat_id=chat_id, text="No characters available.")
            return
        
        # Format the character list
        character_list = "Available characters:\n\n"
        for character in characters:
            character_list += f"ID: {character.character_id}\n"
            character_list += f"Name: {character.name}\n"
            character_list += f"Description: {character.description}\n\n"
        
        character_list += "To switch character, use /character <id>"
        
        await context.bot.send_message(chat_id=chat_id, text=character_list)
    
    async def _module_command_handler(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """
        Handle commands that might be from modules.
        
        Args:
            update: Update from Telegram
            context: Context from Telegram
        """
        if update.effective_chat is None or update.effective_user is None or update.message is None:
            return
        
        user_id = str(update.effective_user.id)
        chat_id = update.effective_chat.id
        message_text = update.message.text
        
        if not message_text:
            return
        
        # Store the user's chat ID for reminders
        self._user_chat_map[user_id] = chat_id
        
        # Parse the command
        command, args = self._module_manager.parse_command(message_text)
        
        # Get all module commands
        module_commands = self._get_all_module_commands()
        
        # Check if this command is handled by a module
        if command in module_commands:
            module, handler_info = module_commands[command]
            
            # Get the handler function - it could be either directly a callable or in a dictionary
            if callable(handler_info):
                handler = handler_info
            elif isinstance(handler_info, dict) and 'handler' in handler_info:
                handler = handler_info['handler']
            else:
                await context.bot.send_message(
                    chat_id=chat_id,
                    text=f"Error: Invalid command handler configuration for /{command}"
                )
                return
            
            # Create a conversation message object
            message = ConversationMessage(
                message_id=str(update.message.message_id),
                conversation_id=f"{user_id}:{self._platform_name}",
                user_id=user_id,
                content=message_text,
                role="user",
                timestamp=update.message.date.timestamp(),
                platform=self._platform_name,
                metadata={
                    "telegram_chat_id": chat_id,
                    "telegram_message_id": update.message.message_id,
                    "telegram_user": {
                        "id": update.effective_user.id,
                        "username": update.effective_user.username,
                        "first_name": update.effective_user.first_name,
                        "last_name": update.effective_user.last_name
                    }
                }
            )
            
            try:
                # Indicate that the bot is typing
                await context.bot.send_chat_action(chat_id=chat_id, action="typing")
                
                # Call the handler
                response = await handler(message, args)
                
                if response:
                    # Send the response
                    await context.bot.send_message(chat_id=chat_id, text=response)
            except Exception as e:
                logger.error(f"Error handling module command: {e}", user_id=user_id, platform=self._platform_name)
                await context.bot.send_message(
                    chat_id=chat_id,
                    text=f"Sorry, there was an error processing your command: {str(e)}"
                )
        else:
            # Command not found
            await context.bot.send_message(
                chat_id=chat_id,
                text=f"Unknown command: {command}. Use /help to see available commands."
            )
    
    async def _message_handler(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Handle regular text messages."""
        if update.effective_chat is None or update.effective_user is None or update.message is None:
            return
        
        user_id = str(update.effective_user.id)
        chat_id = update.effective_chat.id
        message_text = update.message.text
        
        if not message_text:
            return
        
        # Store the user's chat ID for reminders
        self._user_chat_map[user_id] = chat_id
        
        # Prepare metadata
        metadata = {
            "telegram_chat_id": chat_id,
            "telegram_message_id": update.message.message_id,
            "telegram_user": {
                "id": update.effective_user.id,
                "username": update.effective_user.username,
                "first_name": update.effective_user.first_name,
                "last_name": update.effective_user.last_name
            }
        }
        
        # Create a conversation message object for module processing
        message = ConversationMessage(
            message_id=str(update.message.message_id),
            conversation_id=f"{user_id}:{self._platform_name}",
            user_id=user_id,
            content=message_text,
            role="user",
            timestamp=update.message.date.timestamp(),
            platform=self._platform_name,
            metadata=metadata
        )
        
        # Check if any module can handle this message based on trigger patterns
        module_response = None
        for module in self._module_manager.get_enabled_modules():
            if module.can_process(message_text):
                try:
                    # Call the module's process method
                    module_response = await module.process_message(
                        message, 
                        {"telegram_adapter": self}
                    )
                    if module_response:
                        break
                except Exception as e:
                    logger.error(f"Error in module processing: {e}", module_id=module.module_id)
        
        # If a module handled it, send the response and return
        if module_response:
            await context.bot.send_message(chat_id=chat_id, text=module_response)
            return
        
        # Log the incoming message
        logger.info(
            f"Received message from user {user_id}",
            user_id=user_id,
            platform=self._platform_name
        )
        
        # Indicate that the bot is typing
        await context.bot.send_chat_action(chat_id=chat_id, action="typing")
        
        try:
            # Process the message and get a response
            response = await self._conversation_handler.process_user_message(
                user_id, self._platform_name, message_text, metadata
            )
            
            # Send the response
            await context.bot.send_message(chat_id=chat_id, text=response)
            
            logger.info(
                f"Sent response to user {user_id}",
                user_id=user_id,
                platform=self._platform_name
            )
        except Exception as e:
            logger.error(f"Error processing message: {e}", user_id=user_id, platform=self._platform_name)
            await context.bot.send_message(
                chat_id=chat_id,
                text="Sorry, I'm having trouble processing your message. Please try again later."
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
            return False
        
        chat_id = self._user_chat_map[user_id]
        
        try:
            # Format the reminder message
            reminder_text = f"🔔 REMINDER: {task}"
            
            # Send the message
            if self.bot:
                await self.bot.send_message(chat_id=chat_id, text=reminder_text)
                logger.info(f"Sent reminder to user {user_id}: {task}")
                return True
            else:
                logger.error("Bot not initialized, cannot send reminder")
                return False
        except Exception as e:
            logger.error(f"Error sending reminder: {e}", user_id=user_id)
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