"""
Direct Telegram API Test

This script directly calls the Telegram API without using python-telegram-bot's update handling.
It will show what updates (if any) are being received from Telegram's API.
"""
import os
import time
import json
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

def get_updates(offset=None, limit=100, timeout=30):
    """Get updates directly from Telegram API."""
    params = {
        "offset": offset,
        "limit": limit,
        "timeout": timeout
    }
    
    # Remove None values
    params = {k: v for k, v in params.items() if v is not None}
    
    url = f"{BASE_URL}/getUpdates"
    response = requests.get(url, params=params)
    
    if response.status_code == 200:
        return response.json()
    else:
        print(f"Error getting updates: {response.text}")
        return None

def pretty_print_update(update):
    """Format update for nice display."""
    print("\n" + "="*50)
    print(f"Update ID: {update.get('update_id')}")
    
    if 'message' in update:
        msg = update['message']
        print(f"Message ID: {msg.get('message_id')}")
        print(f"From: {msg.get('from', {}).get('first_name')} (ID: {msg.get('from', {}).get('id')})")
        print(f"Chat: {msg.get('chat', {}).get('title') or msg.get('chat', {}).get('first_name')} (ID: {msg.get('chat', {}).get('id')})")
        print(f"Date: {msg.get('date')}")
        print(f"Text: {msg.get('text')}")
    
    print("="*50)

def main():
    """Run the direct API test."""
    print(f"Starting direct Telegram API test with token: {TOKEN[:5]}...{TOKEN[-5:]}")
    print("This script will poll Telegram's API directly to see what updates are received.")
    print("Please send a message to your bot while this script is running...")
    print("\nPress Ctrl+C to stop.\n")
    
    # Delete webhook to ensure polling works
    print("Deleting webhook...")
    requests.get(f"{BASE_URL}/deleteWebhook?drop_pending_updates=false")
    
    # Get initial updates to clear the queue
    updates_response = get_updates(limit=1)
    
    if not updates_response or not updates_response.get("ok"):
        print("Failed to get initial updates.")
        return
    
    # Get the last update_id to avoid processing old messages
    updates = updates_response.get("result", [])
    offset = updates[-1].get("update_id") + 1 if updates else None
    
    print(f"Starting with offset: {offset}")
    
    try:
        while True:
            print("\nPolling for updates...")
            updates_response = get_updates(offset=offset, timeout=10)
            
            if updates_response and updates_response.get("ok"):
                updates = updates_response.get("result", [])
                
                if updates:
                    print(f"\nReceived {len(updates)} update(s)!")
                    
                    for update in updates:
                        pretty_print_update(update)
                        # Update offset to acknowledge this update
                        offset = update.get("update_id") + 1
                else:
                    print("No new updates.")
            else:
                print("Failed to get updates or timeout occurred.")
            
            # Wait a bit between polls
            time.sleep(2)
    except KeyboardInterrupt:
        print("\nStopping...")

if __name__ == "__main__":
    main() 