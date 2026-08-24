import os
import asyncio
import logging
from telethon import TelegramClient, events
from telethon.sessions import StringSession
from dotenv import load_dotenv
from aiohttp import web

from bot_logic import handle_message

# Configure logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

load_dotenv()
API_ID = os.getenv("API_ID")
API_HASH = os.getenv("API_HASH")
TARGET_CHANNEL_ID = os.getenv("TARGET_CHANNEL_ID")
STRING_SESSION = os.getenv("TELEGRAM_STRING_SESSION")
PORT = int(os.getenv("PORT", 8080))

async def handle_ping(request):
    """Dummy web server endpoint to keep Render awake."""
    return web.Response(text="Trading Bot is alive and running!")

async def start_web_server():
    """Starts the dummy web server."""
    app = web.Application()
    app.router.add_get('/', handle_ping)
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, '0.0.0.0', PORT)
    await site.start()
    logger.info(f"Dummy web server listening on port {PORT}...")

async def main():
    if not API_ID or not API_HASH:
        logger.error("API_ID or API_HASH not found in .env file.")
        return

    # Start the dummy web server to keep Render awake
    await start_web_server()

    # Determine which session storage to use
    if STRING_SESSION:
        logger.info("Using StringSession for ephemeral cloud deployment (Render)...")
        session = StringSession(STRING_SESSION)
    else:
        logger.info("Using local SQLite session (trading_bot.session)...")
        session = 'trading_bot'

    client = TelegramClient(session, API_ID, API_HASH)

    @client.on(events.NewMessage(chats=int(TARGET_CHANNEL_ID) if TARGET_CHANNEL_ID else None))
    async def message_handler(event):
        await handle_message(event)

    logger.info("Starting Telethon Userbot...")
    await client.start()
    
    logger.info("Bot is running and listening for messages.")
    await client.run_until_disconnected()

if __name__ == "__main__":
    asyncio.run(main())
