"""
Debug logging utility for Brainy.

This module provides a structured logging system for debugging
the message flow through different layers of the Brainy application.
It writes formatted logs to both the console and a timestamped log file.
"""
import os
import sys
import logging
import traceback
from datetime import datetime
from pathlib import Path
from logging.handlers import RotatingFileHandler

# Create logs directory if it doesn't exist
logs_dir = Path("logs")
logs_dir.mkdir(exist_ok=True)

# Create a timestamp for the log file
timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
log_file = logs_dir / f"brainy_debug_{timestamp}.log"

# Set up the logger
def setup_logger():
    """Set up and configure the debug logger."""
    # Create logger
    logger = logging.getLogger("brainy_debug")
    logger.setLevel(logging.DEBUG)
    
    # Create console handler
    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.DEBUG)
    
    # Create file handler
    file_handler = RotatingFileHandler(
        log_file,
        maxBytes=10 * 1024 * 1024,  # 10 MB
        backupCount=5
    )
    file_handler.setLevel(logging.DEBUG)
    
    # Create formatter
    formatter = logging.Formatter(
        '%(asctime)s - %(levelname)s - %(name)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    
    # Add formatter to handlers
    console_handler.setFormatter(formatter)
    file_handler.setFormatter(formatter)
    
    # Add handlers to logger
    logger.addHandler(console_handler)
    logger.addHandler(file_handler)
    
    return logger

# Create the debug logger
debug_logger = setup_logger()

def get_logger():
    """Get the debug logger."""
    return debug_logger

# Layer-specific logging functions
def log_telegram(message):
    """Log a Telegram-layer message."""
    debug_logger.info(f"TELEGRAM | {message}")

def log_module(message):
    """Log a Module-layer message."""
    debug_logger.info(f"MODULE | {message}")

def log_conversation(message):
    """Log a Conversation-layer message."""
    debug_logger.info(f"CONVERSATION | {message}")

def log_ai_provider(message):
    """Log an AI Provider-layer message."""
    debug_logger.info(f"AI_PROVIDER | {message}")

def log_error(component, message, exc_info=False):
    """Log an error with the component name."""
    error_message = f"{component} ERROR | {message}"
    if exc_info:
        error_message += f"\n{traceback.format_exc()}"
    debug_logger.error(error_message)

def log_startup():
    """Log application startup with system information."""
    debug_logger.info("-" * 50)
    debug_logger.info("STARTUP | Brainy Application Debug Logging Initialized")
    debug_logger.info(f"STARTUP | Python Version: {sys.version}")
    debug_logger.info(f"STARTUP | Platform: {sys.platform}")
    debug_logger.info(f"STARTUP | Working Directory: {os.getcwd()}")
    debug_logger.info(f"STARTUP | Log File: {log_file}")
    debug_logger.info("-" * 50)

# Initialize logging with startup information
log_startup() 