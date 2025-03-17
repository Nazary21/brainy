"""
Logging configuration for Brainy application.
"""
import logging
import sys
from typing import Any, Dict, Optional

import structlog
from rich.console import Console
from rich.logging import RichHandler

from brainy.config import settings

# Configure rich console for pretty printing
console = Console(width=120)

# Get log level from settings (default to INFO if not valid)
try:
    log_level = getattr(logging, settings.LOG_LEVEL.upper())
except (AttributeError, ValueError):
    log_level = logging.INFO

# Configure structlog
structlog.configure(
    processors=[
        structlog.contextvars.merge_contextvars,
        structlog.processors.add_log_level,
        structlog.processors.StackInfoRenderer(),
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.dev.ConsoleRenderer() if settings.DEBUG else structlog.processors.JSONRenderer(),
    ],
    wrapper_class=structlog.make_filtering_bound_logger(log_level),
    context_class=dict,
    logger_factory=structlog.PrintLoggerFactory(),
    cache_logger_on_first_use=True,
)

# Configure standard logging to work with structlog
logging.basicConfig(
    level=log_level,
    format="%(message)s",
    datefmt="[%X]",
    handlers=[
        RichHandler(
            rich_tracebacks=True,
            markup=True,
            console=console,
            tracebacks_show_locals=settings.DEBUG,
        )
    ],
)

# Reduce noise from third-party libraries
for logger_name in ("uvicorn", "uvicorn.access", "uvicorn.error"):
    logger = logging.getLogger(logger_name)
    logger.setLevel(logging.WARNING)


def get_logger(name: Optional[str] = None) -> structlog.BoundLogger:
    """
    Get a logger instance with optional context information.

    Args:
        name: Optional name for the logger, typically the module name

    Returns:
        A bound logger instance
    """
    return structlog.get_logger(name) 