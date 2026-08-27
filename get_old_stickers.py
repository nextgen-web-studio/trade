import os
import asyncio
import logging
from telethon import TelegramClient
from telethon.sessions import StringSession
from dotenv import load_dotenv

logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)

load_dotenv()
API_ID = os.getenv("API_ID")
API_HASH = os.getenv("API_HASH")

async def main():
    if not API_ID or not API_HASH:
        print("Error: Please set API_ID and API_HASH in your .env file.")
        return

    # Use the local authenticated session
    client = TelegramClient('trading_bot', API_ID, API_HASH)
    
    await client.start()
    
    print("\n" + "="*50)
    print("Fetching the last 10 stickers from Magnus Pro VIP...")
    print("="*50)
    
    magnus_pro_id = -1001762265688
    
    try:
        sticker_count = 0
        # Iterate through the last 100 messages to find the most recent stickers
        async for message in client.iter_messages(magnus_pro_id, limit=200):
            if message.sticker:
                sticker_id = message.document.id
                date_str = message.date.strftime("%Y-%m-%d %H:%M:%S")
                print(f"[{date_str}] Found Sticker ID: {sticker_id}")
                sticker_count += 1
                
                if sticker_count >= 10:
                    break
                    
        if sticker_count == 0:
            print("No stickers found in the last 200 messages.")
            
    except Exception as e:
        print(f"Error accessing channel: {e}")
        
    print("="*50 + "\n")
    print("Look at the dates above to match the sticker ID to the UP or DOWN signal Magnus posted!")

if __name__ == "__main__":
    asyncio.run(main())
