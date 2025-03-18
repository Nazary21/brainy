"""
Script to reset Telegram bot webhook and update offset.

This script deletes any existing webhook and resets the update offset,
which can solve issues with not receiving updates via polling.
"""
import os
import asyncio
import requests
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Get the bot token
TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
if not TOKEN:
    raise ValueError("TELEGRAM_BOT_TOKEN not found in environment")

# Base URL for Telegram Bot API
BASE_URL = f"https://api.telegram.org/bot{TOKEN}"

async def reset_webhook_and_updates():
    """Delete webhook and reset update offset."""
    print(f"Using token: {TOKEN[:5]}...{TOKEN[-5:]}")
    
    # Step 1: Delete webhook
    print("\n1. Deleting any existing webhook...")
    delete_webhook_url = f"{BASE_URL}/deleteWebhook?drop_pending_updates=true"
    response = requests.get(delete_webhook_url)
    if response.status_code == 200 and response.json().get("ok"):
        print("✓ Webhook deleted successfully")
    else:
        print(f"✗ Failed to delete webhook: {response.text}")
    
    # Step 2: Get updates with offset -1 to reset the update counter
    print("\n2. Resetting update offset...")
    get_updates_url = f"{BASE_URL}/getUpdates?offset=-1&limit=1"
    response = requests.get(get_updates_url)
    if response.status_code == 200 and response.json().get("ok"):
        print("✓ Update offset reset successfully")
    else:
        print(f"✗ Failed to reset update offset: {response.text}")
    
    # Step 3: Verify that polling can receive updates
    print("\n3. Verifying polling setup...")
    get_me_url = f"{BASE_URL}/getMe"
    response = requests.get(get_me_url)
    if response.status_code == 200 and response.json().get("ok"):
        bot_info = response.json().get("result", {})
        print(f"✓ Connected to bot: @{bot_info.get('username')}")
        print(f"Bot name: {bot_info.get('first_name')}")
        print(f"Bot ID: {bot_info.get('id')}")
    else:
        print(f"✗ Failed to get bot info: {response.text}")
    
    print("\nReset completed. Your bot should now be able to receive updates via polling.")
    print("Please restart your main application and try sending a message to the bot again.")

if __name__ == "__main__":
    asyncio.run(reset_webhook_and_updates()) 