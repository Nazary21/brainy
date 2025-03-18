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
        
        # Pattern 1: "remind me to X in Y minutes/hours/etc."
        pattern1 = r"remind\s+(?:me\s+)?(?:to\s+)?(.+?)\s+in\s+(\d+)\s+(\w+)"
        match = re.search(pattern1, message_text, re.IGNORECASE)
        if match:
            task = match.group(1).strip()
            quantity = int(match.group(2))
            unit = match.group(3).lower()
            return await self._handle_reminder_match(message, task, quantity, unit)
        
        # Pattern 2: "set a reminder for X in Y minutes/hours/etc."
        pattern2 = r"set\s+(?:a\s+)?reminder\s+(?:for\s+)?(.+?)\s+in\s+(\d+)\s+(\w+)"
        match = re.search(pattern2, message_text, re.IGNORECASE)
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
        Handle a matched reminder pattern.
        
        Args:
            message: The message containing the reminder
            task: The task to be reminded of
            quantity: The quantity of time units
            unit: The time unit (minute, hour, day, etc.)
            
        Returns:
            Response message
        """
        # Get the user ID from metadata
        user_id = message.metadata.get("user_id")
        conversation_id = message.metadata.get("conversation_id")
        platform = message.metadata.get("platform")
        
        if not user_id or not conversation_id or not platform:
            return "⚠️ Error: User information not available. Please try again."
        
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
        await self._set_reminder(user_id, conversation_id, platform, task, reminder_time)
        
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
        # If no arguments provided, show usage information
        if not args or len(args) < 3:
            return (
                "⏰ **Reminder Help**\n\n"
                "To set a reminder, use the format:\n"
                "`/remind <time> <unit> <message>`\n\n"
                "📝 **Examples:**\n"
                "• `/remind 5 minutes check oven`\n"
                "• `/remind 1 hour call mom`\n"
                "• `/remind 2 days review document`\n\n"
                "⚙️ **Available Commands:**\n"
                "• `/reminders` - List your active reminders\n"
                "• `/clear_reminders` - Delete all reminders"
            )
        
        try:
            # Get the user ID from metadata
            user_id = message.metadata.get("user_id")
            conversation_id = message.metadata.get("conversation_id")
            platform = message.metadata.get("platform")
            
            if not user_id or not conversation_id or not platform:
                return "⚠️ Error: User information not available. Please try again."
            
            quantity = int(args[0])
            unit = args[1].lower()
            task = " ".join(args[2:])
            
            # Validate input
            if quantity <= 0:
                return "⚠️ Please provide a positive number for the time."
                
            if not task or len(task) < 2:
                return "⚠️ Please provide a more descriptive message for your reminder."
            
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
            await self._set_reminder(user_id, conversation_id, platform, task, reminder_time)
            
            # Calculate time difference in a more human-readable format
            time_diff = reminder_time - now
            days = time_diff.days
            hours, remainder = divmod(time_diff.seconds, 3600)
            minutes, seconds = divmod(remainder, 60)
            
            time_parts = []
            if days > 0:
                time_parts.append(f"{days} day{'s' if days != 1 else ''}")
            if hours > 0:
                time_parts.append(f"{hours} hour{'s' if hours != 1 else ''}")
            if minutes > 0:
                time_parts.append(f"{minutes} minute{'s' if minutes != 1 else ''}")
            if seconds > 0 and not (days or hours or minutes):
                time_parts.append(f"{seconds} second{'s' if seconds != 1 else ''}")
            
            human_time = ", ".join(time_parts)
            
            # Format the response with more details
            formatted_date = reminder_time.strftime("%A, %b %d")
            formatted_time = reminder_time.strftime("%I:%M %p")
            
            # Count active reminders
            active_count = len(self._active_reminders.get(user_id, []))
            
            return (
                f"✅ **Reminder Set!**\n\n"
                f"I'll remind you about: \"{task}\"\n\n"
                f"⏰ Due in: {human_time}\n"
                f"📅 Date: {formatted_date}\n"
                f"🕒 Time: {formatted_time}\n\n"
                f"You now have {active_count} active reminder{'s' if active_count != 1 else ''}. "
                f"Use /reminders to see all."
            )
            
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
        # Get the user ID from metadata
        user_id = message.metadata.get("user_id")
        
        if not user_id:
            return "⚠️ Error: User information not available. Please try again."
        
        if user_id not in self._active_reminders or not self._active_reminders[user_id]:
            return "You don't have any active reminders. Use /remind <time> <unit> <message> to set one."
        
        reminders = self._active_reminders[user_id]
        
        # Sort reminders by time
        reminders.sort(key=lambda r: r["time"])
        
        # Format the response
        response = "📋 Your active reminders:\n\n"
        
        now = datetime.datetime.now()
        
        for i, reminder in enumerate(reminders, 1):
            # Calculate time remaining
            time_until = reminder["time"] - now
            days = time_until.days
            hours, remainder = divmod(time_until.seconds, 3600)
            minutes, seconds = divmod(remainder, 60)
            
            # Format time in a more readable way
            if days > 0:
                time_remaining = f"{days} day{'s' if days != 1 else ''}, {hours} hour{'s' if hours != 1 else ''}"
            elif hours > 0:
                time_remaining = f"{hours} hour{'s' if hours != 1 else ''}, {minutes} minute{'s' if minutes != 1 else ''}"
            elif minutes > 0:
                time_remaining = f"{minutes} minute{'s' if minutes != 1 else ''}"
            else:
                time_remaining = f"{seconds} second{'s' if seconds != 1 else ''}"
                
            # Format date and time
            formatted_time = reminder["time"].strftime("%I:%M %p on %A, %b %d")
            
            response += (
                f"{i}. \"{reminder['task']}\"\n"
                f"   ⏰ Due in: {time_remaining}\n"
                f"   🕒 Time: {formatted_time}\n\n"
            )
            
        response += "To add another reminder, use `/remind <time> <unit> <message>`"
        return response

    async def clear_reminders_command(
        self,
        message: ConversationMessage,
        args: List[str]
    ) -> str:
        """
        Command handler for clearing all reminders.
        
        Args:
            message: The message containing the command
            args: Command arguments
            
        Returns:
            Response message
        """
        # Get the user ID from metadata
        user_id = message.metadata.get("user_id")
        
        if not user_id:
            return "⚠️ Error: User information not available. Please try again."
        
        if user_id not in self._active_reminders or not self._active_reminders[user_id]:
            return "You don't have any active reminders to clear."
        
        # Count reminders
        count = len(self._active_reminders[user_id])
        
        # Clear the reminders
        self._active_reminders[user_id] = []
        
        return f"✅ Cleared {count} reminder{'s' if count != 1 else ''}. Your reminder list is now empty."

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
            platform: Platform the user is on
            task: Task to remind about
            reminder_time: Time to send the reminder
        """
        # Create the reminder
        reminder = {
            "user_id": user_id,
            "conversation_id": conversation_id,
            "platform": platform,
            "task": task,
            "time": reminder_time,
            "created_at": datetime.datetime.now()
        }
        
        # Ensure the user has an entry in the reminders dict
        if user_id not in self._active_reminders:
            self._active_reminders[user_id] = []
        
        # Add the reminder
        self._active_reminders[user_id].append(reminder)
        
        # Calculate delay in seconds
        now = datetime.datetime.now()
        delay = (reminder_time - now).total_seconds()
        
        # Ensure the delay is positive
        if delay <= 0:
            delay = 1  # Send immediately if in the past
        
        # Schedule the reminder with a task
        asyncio.create_task(self._handle_reminder(reminder, delay))
        
        logger.info(f"Set reminder for user {user_id}: {task} at {reminder_time}")

    async def _handle_reminder(self, reminder: Dict[str, Any], delay: float) -> None:
        """
        Handle a scheduled reminder.
        
        Args:
            reminder: The reminder to handle
            delay: Delay in seconds before sending the reminder
        """
        # Sleep until it's time to send the reminder
        await asyncio.sleep(delay)
        
        user_id = reminder["user_id"]
        task = reminder["task"]
        platform = reminder["platform"]
        
        try:
            logger.info(f"Time reached for reminder to user {user_id}: {task}")
            print(f"[DEBUG REMINDER] Sending reminder to user {user_id}: {task}")
            
            # Send reminder based on platform
            if platform == "telegram":
                from brainy.adapters.messengers import get_telegram_adapter
                try:
                    telegram_adapter = get_telegram_adapter()
                    success = await telegram_adapter.send_reminder(user_id, task)
                    
                    if success:
                        logger.info(f"Successfully delivered reminder to user {user_id}: {task}")
                        print(f"[DEBUG REMINDER] Successfully delivered reminder to user {user_id}")
                    else:
                        logger.error(f"Failed to deliver reminder to user {user_id}: {task}")
                        print(f"[DEBUG REMINDER] Failed to deliver reminder to user {user_id}")
                except Exception as telegram_error:
                    logger.error(f"Telegram error when sending reminder: {str(telegram_error)}", exc_info=True)
                    print(f"[DEBUG REMINDER] Telegram error: {str(telegram_error)}")
            else:
                logger.warning(f"Unsupported platform for sending reminders: {platform}")
                print(f"[DEBUG REMINDER] Unsupported platform: {platform}")
            
            # Remove the reminder from active reminders regardless of delivery success
            # This prevents failed reminders from being stuck
            if user_id in self._active_reminders:
                previous_count = len(self._active_reminders[user_id])
                self._active_reminders[user_id] = [
                    r for r in self._active_reminders[user_id] 
                    if r.get("task") != task or r.get("time") != reminder["time"]
                ]
                new_count = len(self._active_reminders[user_id])
                
                removed = previous_count - new_count
                logger.info(f"Removed {removed} reminder(s) for user {user_id}")
                print(f"[DEBUG REMINDER] Removed {removed} reminder(s) for user {user_id}")
            
        except Exception as e:
            logger.error(f"Error handling reminder: {e}", exc_info=True)
            print(f"[DEBUG REMINDER] General error in reminder handling: {str(e)}")
            
            # Still try to remove the reminder to prevent it from being stuck
            try:
                if user_id in self._active_reminders:
                    self._active_reminders[user_id] = [
                        r for r in self._active_reminders[user_id] 
                        if r.get("task") != task or r.get("time") != reminder["time"]
                    ]
                    logger.info(f"Removed reminder for user {user_id} after error")
            except Exception as cleanup_error:
                logger.error(f"Error cleaning up reminder after error: {cleanup_error}", exc_info=True)


def create_reminder_module() -> ReminderModule:
    """
    Create a reminder module instance.
    
    Returns:
        A reminder module instance
    """
    return ReminderModule()