"""
A simplified Telegram bot with OpenAI integration for testing purposes.
This script creates a Telegram bot that responds to messages using OpenAI.
"""
import os
import asyncio
import logging
from typing import Dict, List, Any, Optional

from openai import AsyncOpenAI
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes
from dotenv import load_dotenv

# Set up logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Load environment variables
load_dotenv()

# Get environment variables
TELEGRAM_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

if not TELEGRAM_TOKEN:
    raise ValueError("TELEGRAM_BOT_TOKEN environment variable not set")
if not OPENAI_API_KEY:
    raise ValueError("OPENAI_API_KEY environment variable not set")

# Initialize OpenAI client
openai_client = AsyncOpenAI(api_key=OPENAI_API_KEY)

# Store conversation history
conversation_history: Dict[str, List[Dict[str, str]]] = {}

# Command handler for /start
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Send a message when the command /start is issued."""
    if not update.effective_user:
        return
    
    user = update.effective_user
    user_id = str(user.id)
    
    # Initialize conversation history for this user
    conversation_history[user_id] = [
        {"role": "system", "content": "You are Brainy, a helpful and friendly AI assistant."}
    ]
    
    await update.message.reply_text(
        f"Hello {user.first_name}! I'm Brainy, your AI assistant. How can I help you today?"
    )
    logger.info(f"User {user_id} started the bot")

# Command handler for /help
async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Send a message when the command /help is issued."""
    await update.message.reply_text(
        "I'm Brainy, your AI assistant. You can:\n"
        "/start - Start a new conversation\n"
        "/help - Show this help message\n"
        "/clear - Clear conversation history\n\n"
        "Just send me a message and I'll respond using AI!"
    )
    logger.info(f"User {update.effective_user.id} requested help")

# Command handler for /clear
async def clear_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Clear the conversation history."""
    if not update.effective_user:
        return
    
    user_id = str(update.effective_user.id)
    
    # Reset conversation history
    conversation_history[user_id] = [
        {"role": "system", "content": "You are Brainy, a helpful and friendly AI assistant."}
    ]
    
    await update.message.reply_text("Conversation history cleared. Let's start fresh!")
    logger.info(f"User {user_id} cleared conversation history")

# Generate a response using OpenAI
async def generate_ai_response(user_id: str, message_text: str) -> str:
    """Generate a response using OpenAI's API."""
    try:
        # Make sure user has conversation history
        if user_id not in conversation_history:
            conversation_history[user_id] = [
                {"role": "system", "content": "You are Brainy, a helpful and friendly AI assistant."}
            ]
        
        # Add user message to history
        conversation_history[user_id].append({"role": "user", "content": message_text})
        
        # Keep only the last 10 messages to avoid token limits
        if len(conversation_history[user_id]) > 11:  # 1 system message + 10 conversation messages
            # Keep the system message and the last 10 conversation messages
            conversation_history[user_id] = [
                conversation_history[user_id][0]
            ] + conversation_history[user_id][-10:]
        
        logger.info(f"Sending request to OpenAI for user {user_id}")
        
        # Call OpenAI API
        response = await openai_client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=conversation_history[user_id],
            temperature=0.7,
            max_tokens=1000
        )
        
        # Extract the response text
        response_text = response.choices[0].message.content
        
        # Add assistant response to history
        conversation_history[user_id].append({"role": "assistant", "content": response_text})
        
        logger.info(f"Received response from OpenAI for user {user_id}")
        return response_text
        
    except Exception as e:
        logger.error(f"Error generating AI response: {str(e)}", exc_info=True)
        return "I'm sorry, I encountered an error while generating a response. Please try again later."

# Message handler
async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle the user message and respond with AI."""
    if not update.effective_user or not update.message or not update.message.text:
        return
    
    user_id = str(update.effective_user.id)
    message_text = update.message.text
    
    logger.info(f"Received message from user {user_id}: {message_text}")
    
    # Show typing indicator
    await context.bot.send_chat_action(
        chat_id=update.effective_chat.id, 
        action="typing"
    )
    
    # Generate AI response
    response = await generate_ai_response(user_id, message_text)
    
    # Send the response
    await update.message.reply_text(response)
    logger.info(f"Sent AI response to user {user_id}")

def main():
    """Start the bot."""
    logger.info("Starting Telegram AI bot")
    
    # Create the Application
    application = Application.builder().token(TELEGRAM_TOKEN).build()

    # Add handlers
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("help", help_command))
    application.add_handler(CommandHandler("clear", clear_command))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

    # Start the Bot
    logger.info("Bot starting...")
    
    # Run the bot until Ctrl+C is pressed - this will block until the bot is stopped
    application.run_polling(allowed_updates=Update.ALL_TYPES)
    
    logger.info("Bot stopped")

if __name__ == "__main__":
    main() 