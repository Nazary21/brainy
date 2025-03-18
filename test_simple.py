"""
Simplified Telegram bot to identify connectivity issues.
Based on the working test_telegram_ai.py script.
"""
import os
import logging
from dotenv import load_dotenv
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes

# Configure logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Load environment variables
load_dotenv()
TELEGRAM_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")

# Command handlers
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Send a message when the command /start is issued."""
    user = update.effective_user
    print(f"User {user.id} started the bot")
    await update.message.reply_text(f"Hello {user.first_name}! Send me a message and I'll echo it back.")

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Send a message when the command /help is issued."""
    await update.message.reply_text("I'm a simple echo bot. Send me a message and I'll repeat it.")

async def echo(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Echo the user's message."""
    if not update.message or not update.effective_user:
        return
        
    user_id = update.effective_user.id
    message_text = update.message.text
    print(f"Received message from user {user_id}: '{message_text}'")
    
    await update.message.reply_text(f"You said: {message_text}")
    print(f"Sent echo response to user {user_id}")

def main():
    """Run the bot."""
    print(f"Starting bot with token {TELEGRAM_TOKEN[:5]}...{TELEGRAM_TOKEN[-5:]}")
    
    # Create the application
    application = Application.builder().token(TELEGRAM_TOKEN).build()

    # Add handlers
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("help", help_command))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, echo))

    # Start the bot
    print("Bot starting...")
    application.run_polling()
    print("Bot stopped")

if __name__ == "__main__":
    main() 