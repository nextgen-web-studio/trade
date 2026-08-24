import os
import asyncio
import logging
from telethon import TelegramClient, events
from dotenv import load_dotenv

logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)

load_dotenv()
API_ID = os.getenv("API_ID")
API_HASH = os.getenv("API_HASH")

async def main():
    if not API_ID or not API_HASH:
        print("Error: Please set API_ID and API_HASH in your .env file first.")
        print("You can get these by logging into my.telegram.org")
        return

    client = TelegramClient('sticker_helper_session', API_ID, API_HASH)

    @client.on(events.NewMessage)
    async def print_sticker_id(event):
        """Extracts and prints the sticker ID from a message."""
        if event.message.sticker:
            sticker_id = event.message.document.id
            
            # Try to get the emoji attribute
            emoji = ""
            for attr in event.message.document.attributes:
                if hasattr(attr, 'alt'):
                    emoji = attr.alt
                    break
                    
            print("\n" + "="*50)
            print(f"Sticker Emoji: {emoji}")
            print(f"STICKER UNIQUE ID: {sticker_id}")
            
            # Print the channel ID just in case they need it!
            if event.is_channel:
                print(f"CHANNEL ID: {event.chat_id}")
                
            print("="*50 + "\n")
            
            # Attempt to reply if it's not a channel
            if not event.is_channel:
                await event.reply(f"Sticker ID is: `{sticker_id}`")

    print("Bot is running! Send a sticker to your 'Saved Messages' or anywhere else and I will print its ID...")
    print("(If you send it to the private channel, I will also print the Channel ID for you!)")
    
    await client.start()
    await client.run_until_disconnected()

if __name__ == "__main__":
    asyncio.run(main())
