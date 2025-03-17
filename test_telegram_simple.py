"""
A very simple Telegram echo bot for testing purposes.
This script creates a basic Telegram bot that echoes any message it receives.
"""
import os
import asyncio
import logging
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes

# Set up logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Get the Telegram bot token from environment variables
from dotenv import load_dotenv
load_dotenv()

TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
if not TOKEN:
    raise ValueError("TELEGRAM_BOT_TOKEN environment variable not set")

# Command handler for /start
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Send a message when the command /start is issued."""
    user = update.effective_user
    await update.message.reply_text(f"Hello {user.first_name}! I'm a simple echo bot for testing.")
    logger.info(f"User {user.id} started the bot")

# Command handler for /help
async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Send a message when the command /help is issued."""
    await update.message.reply_text("I'm a simple echo bot. Just send me a message and I'll echo it back to you.")
    logger.info(f"User {update.effective_user.id} requested help")

# Message handler
async def echo(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Echo the user message."""
    message_text = update.message.text
    logger.info(f"Received message from {update.effective_user.id}: {message_text}")
    
    await update.message.reply_text(f"You said: {message_text}")
    logger.info(f"Sent echo response to {update.effective_user.id}")

async def main() -> None:
    """Start the bot."""
    logger.info("Starting simple echo bot")
    
    # Create the Application
    application = Application.builder().token(TOKEN).build()

    # Add handlers
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("help", help_command))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, echo))

    # Start the Bot
    logger.info("Bot starting...")
    await application.initialize()
    await application.updater.start_polling()
    logger.info("Bot started")
    
    # Run the bot until the user presses Ctrl-C
    await application.idle()

if __name__ == "__main__":
    asyncio.run(main()) 