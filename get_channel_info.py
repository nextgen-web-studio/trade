import os
import asyncio
import logging
from telethon import TelegramClient
from dotenv import load_dotenv

logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)

load_dotenv()
API_ID = os.getenv("API_ID")
API_HASH = os.getenv("API_HASH")

async def main():
    if not API_ID or not API_HASH:
        print("Error: Please set API_ID and API_HASH in your .env file.")
        return

    client = TelegramClient('sticker_helper_session', API_ID, API_HASH)
    
    await client.start()
    
    print("\n" + "="*50)
    print("Fetching your recent channels...")
    print("="*50)
    
    # Get all dialogs (chats) the user is in
    async for dialog in client.iter_dialogs():
        if dialog.is_channel:
            print(f"Channel Name: {dialog.name}")
            print(f"Channel ID:   {dialog.id}")
            print("-" * 30)
            
    print("="*50 + "\n")
    
    print("If you are looking for sticker IDs, leave this script running and send or forward a sticker to your 'Saved Messages'.")
    
    # Also keep listening for stickers just in case
    from telethon import events
    @client.on(events.NewMessage)
    async def print_sticker_id(event):
        if event.message.sticker:
            sticker_id = event.message.document.id
            print(f"\n---> STICKER UNIQUE ID: {sticker_id} <---")

    await client.run_until_disconnected()

if __name__ == "__main__":
    asyncio.run(main())
