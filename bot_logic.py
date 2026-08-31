import logging
import re
from telethon import events
from trading_api import schedule_trade

logger = logging.getLogger(__name__)

# State management (In-memory for simplicity)
bot_state = {"mode": "IDLE", "asset": None}

# List of accepted sticker IDs (Supports both your test channel and Magnus Pro)
CALL_STICKER_IDS = [6116081567497459695, 6116272169556121384]   # UP / CALL
PUT_STICKER_IDS = [6116266384235174391]                         # DOWN / PUT

async def send_loud_notification(text: str):
    import os
    import aiohttp
    bot_token = os.getenv("BOT_TOKEN")
    if bot_token:
        try:
            url = f"https://api.telegram.org/bot{bot_token}/sendMessage"
            payload = {"chat_id": 5188160752, "text": text}
            async with aiohttp.ClientSession() as session:
                await session.post(url, json=payload)
        except Exception as e:
            logger.error(f"Failed to send loud notification: {e}")

async def handle_message(event: events.NewMessage.Event, client) -> None:
    """Handles incoming channel messages and stickers via Telethon."""
    
    global bot_state
    
    # Handle Stickers (The Trigger)
    if event.message.sticker:
        sticker_id = event.message.document.id
        logger.info(f"Received sticker with ID: {sticker_id}")
            
        # Direction Trigger (CALL/PUT)
        if bot_state["mode"] == "ASSET_RECEIVED":
            if sticker_id in CALL_STICKER_IDS:
                direction = "CALL"
            elif sticker_id in PUT_STICKER_IDS:
                direction = "PUT"
            else:
                logger.info("Received a sticker, but it does not match known UP/DOWN stickers. Ignoring.")
                return

            asset = bot_state["asset"]
            logger.info(f"Direction {direction} received for {asset}. Triggering trade.")
            
            # Send immediate loud notification
            await send_loud_notification(f"🚀 Signal received!\nAsset: {asset}\nDirection: {direction}\nPreparing trade...")
            
            # Reset state immediately to avoid duplicate triggers
            bot_state["mode"] = "IDLE"
            bot_state["asset"] = None
            
            # Trigger the trade scheduling asynchronously
            await schedule_trade(asset, direction, client)
            
        elif bot_state["mode"] != "ASSET_RECEIVED":
            logger.info("Received a sticker, but we don't have an active asset yet. Ignoring.")
            
        return

    # Handle Text (The Asset)
    if event.message.text:
        text = event.message.text.upper()
        
        # Look for the asset pair (e.g. "EUR/USD" or "GBP/JPY")
        match = re.search(r"([A-Z]{3}/[A-Z]{3})", text)
        if match:
            asset = match.group(1)
            bot_state["asset"] = asset
            bot_state["mode"] = "ASSET_RECEIVED"
            logger.info(f"Asset detected: {asset}. Mode: ASSET_RECEIVED. Waiting for direction sticker.")
