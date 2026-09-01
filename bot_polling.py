import os
import asyncio
import logging
import aiohttp
import json
import csv
import requests
import urllib3

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
logger = logging.getLogger(__name__)

MCP_URL = "https://turbo-options.mcp.iqoption.com/message"

def _get_iq_headers():
    token = os.getenv("IQ_OPTION_TOKEN")
    return {'Authorization': f'Bearer {token}', 'Content-Type': 'application/json'}

def _fetch_balance_sync():
    """Fetches IQ Option balances. Runs in a background thread."""
    payload = [
        {"jsonrpc": "2.0", "id": "init", "method": "initialize",
         "params": {"protocolVersion": "2024-11-05", "capabilities": {},
                    "clientInfo": {"name": "telegram-bot", "version": "1.0.0"}}},
        {"jsonrpc": "2.0", "method": "notifications/initialized"},
        {"jsonrpc": "2.0", "id": "list_balances", "method": "tools/call",
         "params": {"name": "list_balances", "arguments": {}}}
    ]
    try:
        r = requests.post(MCP_URL, json=payload, headers=_get_iq_headers(), verify=False, timeout=10)
        r.raise_for_status()
        for item in r.json():
            if item.get("id") == "list_balances":
                text = item.get("result", {}).get("content", [{}])[0].get("text", "{}")
                return json.loads(text)
    except Exception as e:
        logger.error(f"Error fetching balance: {e}")
    return None

def _read_history():
    """Reads last 10 trades from CSV log."""
    csv_file = "trades.csv"
    if not os.path.isfile(csv_file):
        return []
    try:
        with open(csv_file, mode='r') as f:
            rows = list(csv.DictReader(f))
        return rows[-10:]
    except Exception as e:
        logger.error(f"Error reading history: {e}")
        return []

async def _send_reply(bot_token: str, chat_id: int, text: str):
    """Sends a reply message via the Telegram Bot API."""
    url = f"https://api.telegram.org/bot{bot_token}/sendMessage"
    payload = {"chat_id": chat_id, "text": text, "parse_mode": "Markdown"}
    try:
        async with aiohttp.ClientSession() as session:
            await session.post(url, json=payload)
    except Exception as e:
        logger.error(f"Failed to send bot reply: {e}")

async def _handle_command(bot_token: str, chat_id: int, text: str):
    """Handles a single command and sends the reply."""
    cmd = text.strip().lower().split()[0]  # get just the command word

    if cmd == "/balance":
        await _send_reply(bot_token, chat_id, "Fetching your IQ Option balance...")
        data = await asyncio.to_thread(_fetch_balance_sync)
        if not data or not data.get("balances"):
            await _send_reply(bot_token, chat_id, "Could not fetch balance. Check your IQ Option token.")
            return
        lines = ["*Your IQ Option Balances:*\n"]
        for b in data["balances"]:
            btype = b.get("type", "").lower()
            label = "REAL MONEY" if btype == "regular" else "DEMO"
            amount = b.get("amount", 0)
            currency = b.get("currency", "")
            lines.append(f"[{label}] {amount} {currency}")
        await _send_reply(bot_token, chat_id, "\n".join(lines))

    elif cmd == "/history":
        rows = _read_history()
        if not rows:
            await _send_reply(bot_token, chat_id,
                "No trade history yet.\nTrades will appear here once the bot starts placing them.")
            return
        lines = ["*Last trades placed by bot:*\n"]
        lines.append("`Date       Time      Asset      Dir   Status`")
        lines.append("`" + "-" * 48 + "`")
        for r in rows:
            date = r.get("Date", "")[-5:]   # show MM-DD only
            time = r.get("Time", "")[:5]    # show HH:MM only
            asset = r.get("Asset", "")
            direction = r.get("Direction", "")
            status = r.get("Status", "")[:10]
            lines.append(f"`{date:<10} {time:<9} {asset:<10} {direction:<5} {status}`")
        await _send_reply(bot_token, chat_id, "\n".join(lines))

    elif cmd == "/tradeamount":
        amount = os.getenv("TRADE_AMOUNT", "10")
        account = os.getenv("ACCOUNT_TYPE", "training").upper()
        await _send_reply(bot_token, chat_id,
            f"*Current Trade Settings:*\n"
            f"Account: {account}\n"
            f"Trade Amount: {amount}\n\n"
            f"_(To change, update the env variable on Render)_")

    elif cmd == "/help":
        await _send_reply(bot_token, chat_id,
            "*Available Commands:*\n\n"
            "/balance - Show your IQ Option account balance\n"
            "/history - Show last 10 trades placed by the bot\n"
            "/tradeamount - Show current trade amount setting\n"
            "/help - Show this menu")

    else:
        await _send_reply(bot_token, chat_id,
            "Unknown command. Send /help to see available commands.")

async def start_bot_command_polling():
    """
    Polls the Telegram Bot API for new messages.
    This is a separate background task — completely isolated from trading logic.
    """
    bot_token = os.getenv("BOT_TOKEN")
    if not bot_token:
        logger.warning("BOT_TOKEN not set. Bot command polling disabled.")
        return

    logger.info("Bot command polling started. Send /help to your notification bot.")
    offset = None

    async with aiohttp.ClientSession() as session:
        while True:
            try:
                url = f"https://api.telegram.org/bot{bot_token}/getUpdates"
                params = {"timeout": 30, "allowed_updates": ["message"]}
                if offset:
                    params["offset"] = offset

                async with session.get(url, params=params, timeout=aiohttp.ClientTimeout(total=35)) as resp:
                    data = await resp.json()

                if not data.get("ok"):
                    await asyncio.sleep(5)
                    continue

                for update in data.get("result", []):
                    offset = update["update_id"] + 1
                    message = update.get("message", {})
                    msg_text = message.get("text", "")
                    chat_id = message.get("chat", {}).get("id")

                    if msg_text.startswith("/") and chat_id:
                        logger.info(f"Bot command received: {msg_text}")
                        # Handle command in background — no blocking of poll loop
                        asyncio.create_task(_handle_command(bot_token, chat_id, msg_text))

            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Bot polling error: {e}")
                await asyncio.sleep(5)
