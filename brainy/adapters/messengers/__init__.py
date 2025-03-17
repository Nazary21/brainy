"""
Messenger adapters for Brainy.

This module provides adapters for different messaging platforms.
"""
from brainy.adapters.messengers.telegram_adapter import TelegramAdapter, get_telegram_adapter

__all__ = ["TelegramAdapter", "get_telegram_adapter"] 