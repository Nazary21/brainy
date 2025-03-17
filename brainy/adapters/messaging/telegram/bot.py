"""
Telegram bot implementation for Brainy.
"""
import asyncio
from typing import Dict, Any, Optional

from telegram import Update
from telegram.ext import (
    Application,
    ApplicationBuilder,
    CommandHandler,
    ContextTypes,
    MessageHandler,
    filters,
)

from brainy.config import settings
from brainy.utils.logging import get_logger

# Initialize logger
logger = get_logger(__name__)

# Global application instance
application: Optional[Application] = None


async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Send a message when the command /start is issued."""
    user = update.effective_user
    logger.info(f"User {user.id} ({user.username}) started the bot")
    
    await update.message.reply_text(
        f"👋 Hello, {user.first_name}! I'm Brainy, your AI assistant.\n\n"
        f"I can help you with a variety of tasks and remember our conversations.\n\n"
        f"Use /help to see available commands."
    )


async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Send a message when the command /help is issued."""
    help_text = (
        "Here are the commands you can use:\n\n"
        "/start - Start the bot\n"
        "/help - Show this help message\n"
        "/profile - Show what I know about you\n"
        "/clear - Clear conversation history\n"
        "/settings - Configure bot settings"
    )
    await update.message.reply_text(help_text)


async def profile_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Show what the bot knows about the user."""
    user = update.effective_user
    
    # For now, we just return basic information
    # Later, this will include preferences and conversation history summary
    await update.message.reply_text(
        f"User Profile:\n"
        f"- ID: {user.id}\n"
        f"- Name: {user.first_name} {user.last_name or ''}\n"
        f"- Username: @{user.username or 'None'}\n"
    )


async def clear_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Clear conversation history."""
    user = update.effective_user
    logger.info(f"User {user.id} cleared conversation history")
    
    # This will be implemented in Phase 1 with memory management
    await update.message.reply_text(
        "Conversation history cleared. I've forgotten our previous conversations."
    )


async def settings_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Configure bot settings."""
    # This will be implemented in Phase 2/3 with the web dashboard
    await update.message.reply_text(
        "Settings will be available in a future update. "
        "For now, you can access settings through the web dashboard."
    )


async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Process incoming messages."""
    user = update.effective_user
    message_text = update.message.text
    
    logger.debug(f"Message from {user.id}: {message_text}")
    
    # For initial implementation, we just reply with a simple message
    # In Phase 1, this will use the AI provider and memory system
    await update.message.reply_text(
        "I'm a simple bot for now. In the future, I'll be able to have more complex conversations!"
    )


async def setup_telegram_bot() -> None:
    """Set up the Telegram bot with all handlers."""
    global application
    
    token = settings.telegram_bot_token.get_secret_value()
    
    try:
        # Initialize the bot
        application_builder = ApplicationBuilder().token(token)
        application = application_builder.build()
        
        # Add command handlers
        application.add_handler(CommandHandler("start", start_command))
        application.add_handler(CommandHandler("help", help_command))
        application.add_handler(CommandHandler("profile", profile_command))
        application.add_handler(CommandHandler("clear", clear_command))
        application.add_handler(CommandHandler("settings", settings_command))
        
        # Add message handler for regular messages
        application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
        
        # Start the bot in a background task
        asyncio.create_task(application.run_polling(allowed_updates=Update.ALL_TYPES))
        
        logger.info("Telegram bot started successfully")
    except Exception as e:
        logger.error(f"Failed to start Telegram bot: {str(e)}")
        raise 