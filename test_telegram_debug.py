"""
Debug script to test Telegram bot connectivity.
"""
import os
import asyncio
import logging
from dotenv import load_dotenv
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes

# Configure logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.DEBUG
)
logger = logging.getLogger(__name__)

# Load environment variables
load_dotenv()

# Get the Telegram bot token
TELEGRAM_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
if not TELEGRAM_TOKEN:
    raise ValueError("TELEGRAM_BOT_TOKEN not found in environment variables")

print(f"Using token: {TELEGRAM_TOKEN[:5]}...{TELEGRAM_TOKEN[-5:]}")

# Define handlers
async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle the /start command."""
    if update.effective_user:
        user_id = update.effective_user.id
        username = update.effective_user.username
        print(f"[DEBUG] /start command from user {user_id} (@{username})")
    
    await update.message.reply_text("Hello! This is a debug bot to test Telegram connectivity.")

async def echo_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Echo the user message to verify connectivity."""
    if not update.message or not update.effective_user:
        print("[DEBUG] Received update without message or user")
        return
    
    user_id = update.effective_user.id
    message_text = update.message.text
    print(f"[DEBUG] Received message from user {user_id}: '{message_text}'")
    
    await update.message.reply_text(f"You said: {message_text}")
    print(f"[DEBUG] Sent echo response to user {user_id}")

# Debug handler to catch ALL updates
async def debug_all_updates(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Log all updates received from Telegram."""
    update_type = "unknown"
    if update.message:
        update_type = "message"
    elif update.edited_message:
        update_type = "edited_message"
    elif update.callback_query:
        update_type = "callback_query"
    
    print(f"[DEBUG] RAW UPDATE RECEIVED - Type: {update_type}")
    print(f"[DEBUG] Update object: {update}")

def main():
    """Start the bot without using asyncio.run()."""
    print("Starting debug Telegram bot...")
    
    # Create the Application
    application = Application.builder().token(TELEGRAM_TOKEN).build()
    
    # Add debug handler for all updates
    application.add_handler(MessageHandler(filters.ALL, debug_all_updates), group=-999)
    
    # Add normal handlers
    application.add_handler(CommandHandler("start", start_command))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, echo_handler))
    
    # Start the bot
    print("[DEBUG] Starting polling...")
    application.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == "__main__":
    main() 