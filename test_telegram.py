"""
Simple test script for Telegram bot functionality.
"""
import os
import asyncio
import sys
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes

# Get Telegram bot token from environment variable
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
if not TELEGRAM_BOT_TOKEN:
    with open(".env") as f:
        for line in f:
            if line.startswith("TELEGRAM_BOT_TOKEN="):
                TELEGRAM_BOT_TOKEN = line.strip().split("=", 1)[1]
                # Remove quotes if present
                TELEGRAM_BOT_TOKEN = TELEGRAM_BOT_TOKEN.strip("'\"")
                break

if not TELEGRAM_BOT_TOKEN:
    raise ValueError("TELEGRAM_BOT_TOKEN not found in environment or .env file")

print(f"Using Telegram token: {TELEGRAM_BOT_TOKEN[:5]}...{TELEGRAM_BOT_TOKEN[-5:]}")

async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Send a message when the command /start is issued."""
    user = update.effective_user
    print(f"User {user.id} ({user.username}) started the bot")
    
    await update.message.reply_text(
        f"👋 Hello, {user.first_name}! I'm Brainy, your AI assistant.\n\n"
        f"This is a simple test of basic functionality.\n\n"
        f"Use /help to see available commands."
    )

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Send a message when the command /help is issued."""
    help_text = (
        "Here are the commands you can use:\n\n"
        "/start - Start the bot\n"
        "/help - Show this help message\n"
    )
    await update.message.reply_text(help_text)

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Echo the user message."""
    print(f"Received message: {update.message.text}")
    await update.message.reply_text(f"You said: {update.message.text}\n\nThis is a simple echo test. The full bot would provide AI-powered responses with memory.")

async def main() -> None:
    """Run the bot."""
    # Create the Application
    application = Application.builder().token(TELEGRAM_BOT_TOKEN).build()

    # Add handlers
    application.add_handler(CommandHandler("start", start_command))
    application.add_handler(CommandHandler("help", help_command))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

    # Start polling in a separate task
    print("Starting bot...")
    await application.initialize()
    await application.updater.start_polling()
    
    print("Bot is running. Press Ctrl+C to stop.")
    
    # Simple way to keep the script running until interrupted
    try:
        # Keep running indefinitely
        while True:
            await asyncio.sleep(1)
    except KeyboardInterrupt:
        print("\nShutting down...")
    finally:
        # Clean up
        await application.updater.stop()
        await application.shutdown()

if __name__ == "__main__":
    asyncio.run(main()) 