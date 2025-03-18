"""
Main entry point for the Brainy application.
"""
import asyncio
import os
from pathlib import Path

import uvicorn
from fastapi import FastAPI

from brainy.config import settings
from brainy.utils.logging import get_logger
from brainy.adapters.messengers import get_telegram_adapter
from brainy.core.conversation import get_conversation_handler
from brainy.core.character import get_character_manager
from brainy.core.memory_manager import get_memory_manager
from brainy.core.modules import register_builtin_modules
from brainy.core.conversation import ConversationHandler
from brainy.adapters.messengers import TelegramAdapter
from brainy.core.ai_provider import get_ai_provider_manager

# Initialize logger
logger = get_logger(__name__)

# Initialize FastAPI application
app = FastAPI(
    title="Brainy API",
    description="AI Bot Manager API",
    version="0.1.0",
    docs_url="/docs" if settings.DEBUG else None,
    redoc_url="/redoc" if settings.DEBUG else None,
)

# Store the telegram adapter instance globally
_telegram_adapter = None

@app.get("/health")
async def health_check():
    """Health check endpoint for monitoring."""
    return {"status": "ok"}


@app.on_event("startup")
async def startup_event():
    """Initialize resources when the application starts up."""
    global _telegram_adapter
    
    # Create necessary directories
    data_dir = Path(__file__).parent / "data"
    data_dir.mkdir(parents=True, exist_ok=True)
    
    # Characters directory
    characters_dir = data_dir / "characters"
    characters_dir.mkdir(parents=True, exist_ok=True)
    
    # Vector DB directory
    vector_db_path = Path(settings.VECTOR_DB_PATH)
    vector_db_path.mkdir(parents=True, exist_ok=True)
    
    logger.info("Starting Brainy AI Bot Manager")
    logger.info(f"Log level: {settings.LOG_LEVEL}")
    logger.info(f"Vector DB path: {settings.VECTOR_DB_PATH}")
    
    try:
        # Initialize core components
        memory_manager = get_memory_manager()
        character_manager = get_character_manager()
        ai_provider_manager = get_ai_provider_manager()
        
        # Initialize conversation handler
        conversation_handler = ConversationHandler(
            memory_manager=memory_manager,
            character_manager=character_manager,
            ai_provider_manager=ai_provider_manager
        )
        
        # Register built-in modules
        await register_builtin_modules()
        logger.info("Registered built-in modules")
        
        # Initialize Telegram bot
        if not settings.TELEGRAM_BOT_TOKEN:
            logger.warning("Telegram bot token not set, skipping bot initialization")
        else:
            # Initialize the Telegram adapter
            _telegram_adapter = TelegramAdapter(
                token=settings.TELEGRAM_BOT_TOKEN,
                conversation_handler=conversation_handler
            )
            
            # Start the Telegram adapter in a separate task
            asyncio.create_task(_telegram_adapter.start())
            logger.info("Started Telegram bot adapter")
    except Exception as e:
        logger.error(f"Error during startup: {str(e)}", exc_info=True)
        raise


@app.on_event("shutdown")
async def shutdown_event():
    """Clean up resources when the application shuts down."""
    global _telegram_adapter
    
    # Stop the Telegram bot if it's running
    if _telegram_adapter is not None:
        await _telegram_adapter.stop()
        logger.info("Stopped Telegram bot adapter")
    
    logger.info("Shutting down Brainy AI Bot Manager")


def run():
    """Run the application using uvicorn."""
    uvicorn.run(
        "brainy.main:app",
        host="0.0.0.0",
        port=int(os.getenv("PORT", 8000)),
        reload=settings.DEBUG,
        log_level=settings.LOG_LEVEL.lower(),
    )


if __name__ == "__main__":
    run() 