"""
Reminder module for Brainy.

This module provides basic reminder functionality.
"""
import asyncio
import datetime
import re
from typing import Dict, List, Any, Optional, Set

from brainy.utils.logging import get_logger
from brainy.core.memory_manager import ConversationMessage
from brainy.core.modules.base import Module

# Initialize logger
logger = get_logger(__name__)


class ReminderModule(Module):
    """
    Module for managing reminders.
    
    This module allows users to set reminders for future tasks.
    """
    
    def __init__(self):
        """Initialize the reminder module."""
        super().__init__(
            module_id="reminder",
            name="Reminder",
            description="Set and manage reminders for future tasks."
        )
        
        # Dictionary to store active reminders
        # Key: user_id, Value: list of reminder dictionaries
        self._active_reminders: Dict[str, List[Dict[str, Any]]] = {}
        
        # Register commands
        self.register_command(
            "remind",
            self.remind_command,
            "Set a reminder for a future task",
            usage="/remind <time> <unit> <message>",
            examples=[
                "/remind 5 minutes check oven",
                "/remind 1 hour call mom",
                "/remind 2 days review document"
            ]
        )
        
        self.register_command(
            "reminders",
            self.list_reminders_command,
            "List all your active reminders",
            usage="/reminders"
        )
        
        self.register_command(
            "clear_reminders",
            self.clear_reminders_command,
            "Clear all your active reminders",
            usage="/clear_reminders"
        )
        
        # Register trigger patterns
        self.register_trigger_pattern(r"remind\s+(?:me\s+)?(?:to\s+)?(.+?)\s+in\s+(\d+)\s+(\w+)")
        self.register_trigger_pattern(r"set\s+(?:a\s+)?reminder\s+(?:for\s+)?(.+?)\s+in\s+(\d+)\s+(\w+)")

    async def process_message(
        self,
        message: ConversationMessage,
        context: Dict[str, Any]
    ) -> Optional[str]:
        """
        Process a message to detect reminder requests.
        
        Args:
            message: The message to process
            context: Additional context information
            
        Returns:
            Response message or None if the message wasn't processed
        """
        # Skip non-user messages
        if message.role != "user":
            return None
        
        # Check if the message matches any of our patterns
        message_text = message.content.strip()
        
        # Pattern 1: "remind me to X in Y minutes/hours/days"
        match = re.search(r"remind\s+(?:me\s+)?(?:to\s+)?(.+?)\s+in\s+(\d+)\s+(\w+)", message_text, re.IGNORECASE)
        if match:
            task = match.group(1).strip()
            quantity = int(match.group(2))
            unit = match.group(3).lower()
            
            return await self._handle_reminder_match(message, task, quantity, unit)
        
        # Pattern 2: "set a reminder for X in Y minutes/hours/days"
        match = re.search(r"set\s+(?:a\s+)?reminder\s+(?:for\s+)?(.+?)\s+in\s+(\d+)\s+(\w+)", message_text, re.IGNORECASE)
        if match:
            task = match.group(1).strip()
            quantity = int(match.group(2))
            unit = match.group(3).lower()
            
            return await self._handle_reminder_match(message, task, quantity, unit)
        
        return None
    
    async def _handle_reminder_match(
        self,
        message: ConversationMessage,
        task: str,
        quantity: int,
        unit: str
    ) -> str:
        """
        Handle a matched reminder request.
        
        Args:
            message: The message containing the reminder request
            task: The task to remind about
            quantity: The time quantity
            unit: The time unit (minutes, hours, days)
            
        Returns:
            Response message
        """
        # Normalize the unit to singular form
        if unit.endswith('s'):
            unit = unit[:-1]
        
        # Calculate the reminder time
        now = datetime.datetime.now()
        
        if unit in ["minute", "min", "m"]:
            reminder_time = now + datetime.timedelta(minutes=quantity)
            unit_str = "minute" if quantity == 1 else "minutes"
        elif unit in ["hour", "hr", "h"]:
            reminder_time = now + datetime.timedelta(hours=quantity)
            unit_str = "hour" if quantity == 1 else "hours"
        elif unit in ["day", "d"]:
            reminder_time = now + datetime.timedelta(days=quantity)
            unit_str = "day" if quantity == 1 else "days"
        else:
            return f"Sorry, I don't understand the time unit '{unit}'. Please use minutes, hours, or days."
        
        # Set the reminder
        await self._set_reminder(message.user_id, message.conversation_id, message.platform, task, reminder_time)
        
        # Format the response
        formatted_time = reminder_time.strftime("%Y-%m-%d %H:%M:%S")
        return f"✅ I'll remind you to {task} in {quantity} {unit_str} (at {formatted_time})."

    async def remind_command(
        self,
        message: ConversationMessage,
        args: List[str]
    ) -> str:
        """
        Command handler for setting reminders.
        
        Args:
            message: The message containing the command
            args: Command arguments
            
        Returns:
            Response message
        """
        if len(args) < 3:
            return (
                "⚠️ Please specify a time, unit, and message for your reminder.\n\n"
                "Usage: /remind <time> <unit> <message>\n\n"
                "Examples:\n"
                "/remind 5 minutes check oven\n"
                "/remind 1 hour call mom\n"
                "/remind 2 days review document"
            )
        
        try:
            quantity = int(args[0])
            unit = args[1].lower()
            task = " ".join(args[2:])
            
            # Normalize the unit to singular form
            if unit.endswith('s'):
                unit = unit[:-1]
            
            # Calculate the reminder time
            now = datetime.datetime.now()
            
            if unit in ["minute", "min", "m"]:
                reminder_time = now + datetime.timedelta(minutes=quantity)
                unit_str = "minute" if quantity == 1 else "minutes"
            elif unit in ["hour", "hr", "h"]:
                reminder_time = now + datetime.timedelta(hours=quantity)
                unit_str = "hour" if quantity == 1 else "hours"
            elif unit in ["day", "d"]:
                reminder_time = now + datetime.timedelta(days=quantity)
                unit_str = "day" if quantity == 1 else "days"
            else:
                return f"⚠️ Sorry, I don't understand the time unit '{unit}'. Please use minutes, hours, or days."
            
            # Set the reminder
            await self._set_reminder(message.user_id, message.conversation_id, message.platform, task, reminder_time)
            
            # Format the response
            formatted_time = reminder_time.strftime("%Y-%m-%d %H:%M:%S")
            return f"✅ I'll remind you to {task} in {quantity} {unit_str} (at {formatted_time})."
            
        except ValueError:
            return "⚠️ Please specify a valid number for the time."

    async def list_reminders_command(
        self,
        message: ConversationMessage,
        args: List[str]
    ) -> str:
        """
        Command handler for listing reminders.
        
        Args:
            message: The message containing the command
            args: Command arguments
            
        Returns:
            Response message
        """
        user_id = message.user_id
        
        if user_id not in self._active_reminders or not self._active_reminders[user_id]:
            return "You don't have any active reminders."
        
        reminders = self._active_reminders[user_id]
        
        # Sort reminders by time
        reminders.sort(key=lambda r: r["time"])
        
        # Format the response
        response = "Your active reminders:\n\n"
        
        for i, reminder in enumerate(reminders, 1):
            time_str = reminder["time"].strftime("%Y-%m-%d %H:%M:%S")
            response += f"{i}. {reminder['task']} (at {time_str})\n"
        
        return response

    async def clear_reminders_command(
        self,
        message: ConversationMessage,
        args: List[str]
    ) -> str:
        """
        Command handler for clearing reminders.
        
        Args:
            message: The message containing the command
            args: Command arguments
            
        Returns:
            Response message
        """
        user_id = message.user_id
        
        if user_id not in self._active_reminders or not self._active_reminders[user_id]:
            return "You don't have any active reminders to clear."
        
        # Count the reminders
        count = len(self._active_reminders[user_id])
        
        # Clear the reminders
        self._active_reminders[user_id] = []
        
        return f"✅ Cleared {count} active reminders."

    async def _set_reminder(
        self,
        user_id: str,
        conversation_id: str,
        platform: str,
        task: str,
        reminder_time: datetime.datetime
    ) -> None:
        """
        Set a reminder for a user.
        
        Args:
            user_id: ID of the user
            conversation_id: ID of the conversation
            platform: Platform of the conversation
            task: Task to remind about
            reminder_time: Time to send the reminder
        """
        # Initialize the user's reminder list if it doesn't exist
        if user_id not in self._active_reminders:
            self._active_reminders[user_id] = []
        
        # Create the reminder object
        reminder = {
            "user_id": user_id,
            "conversation_id": conversation_id,
            "platform": platform,
            "task": task,
            "time": reminder_time,
            "created_at": datetime.datetime.now()
        }
        
        # Add the reminder to the list
        self._active_reminders[user_id].append(reminder)
        
        # Calculate the delay in seconds
        now = datetime.datetime.now()
        delay = (reminder_time - now).total_seconds()
        
        # Ensure the delay is positive
        delay = max(delay, 0)
        
        # Schedule the reminder
        asyncio.create_task(self._handle_reminder(reminder, delay))
        
        logger.info(
            f"Set reminder for user {user_id}",
            task=task,
            delay_seconds=delay,
            reminder_time=reminder_time.isoformat()
        )

    async def _handle_reminder(self, reminder: Dict[str, Any], delay: float) -> None:
        """
        Handle a scheduled reminder.
        
        Args:
            reminder: The reminder object
            delay: Delay in seconds before sending the reminder
        """
        try:
            # Wait for the specified delay
            await asyncio.sleep(delay)
            
            # Get the user's active reminders
            user_id = reminder["user_id"]
            user_reminders = self._active_reminders.get(user_id, [])
            
            # Check if the reminder is still active
            if reminder not in user_reminders:
                logger.info(f"Reminder no longer active, skipping", user_id=user_id, task=reminder["task"])
                return
            
            # Remove the reminder from the active list
            user_reminders.remove(reminder)
            
            # Send the reminder based on the platform
            platform = reminder["platform"]
            task = reminder["task"]
            
            if platform == "telegram":
                # Import telegram adapter here to avoid circular imports
                from brainy.adapters.messengers import get_telegram_adapter
                
                telegram_adapter = get_telegram_adapter()
                success = await telegram_adapter.send_reminder(user_id, task)
                
                if success:
                    logger.info(f"Sent reminder to user {user_id} via Telegram", task=task)
                else:
                    logger.error(f"Failed to send reminder to user {user_id} via Telegram", task=task)
            else:
                logger.warning(f"Unsupported platform for sending reminders: {platform}")
            
        except Exception as e:
            logger.error(f"Error handling reminder: {e}", reminder=reminder, error=str(e))


def create_reminder_module() -> ReminderModule:
    """
    Create an instance of the reminder module.
    
    Returns:
        ReminderModule instance
    """
    return ReminderModule()