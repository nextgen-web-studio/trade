import os
import asyncio
from telethon import TelegramClient
from telethon.sessions import StringSession
from dotenv import load_dotenv

async def main():
    load_dotenv()
    API_ID = os.getenv("API_ID")
    API_HASH = os.getenv("API_HASH")

    if not API_ID or not API_HASH:
        print("ERROR: API_ID or API_HASH not found in .env file.")
        return

    print("Logging into Telegram to generate your String Session...")
    
    client = TelegramClient(StringSession(), API_ID, API_HASH)
    await client.start()
    
    session_string = client.session.save()
    
    print("\n" + "="*50)
    print("YOUR STRING SESSION HAS BEEN GENERATED SUCCESSFULLY!")
    print("="*50 + "\n")
    
    print(session_string)
    
    print("\n" + "="*50)
    print("INSTRUCTIONS:")
    print("1. Copy the extremely long block of text above.")
    print("2. Go to your Render Dashboard -> Environment Variables.")
    print("3. Add a new variable named: TELEGRAM_STRING_SESSION")
    print("4. Paste the text as the value and save.")
    print("="*50 + "\n")

if __name__ == "__main__":
    asyncio.run(main())
