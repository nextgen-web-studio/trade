import os
import csv
import json
import logging
import asyncio
import requests
import urllib3

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
logger = logging.getLogger(__name__)

MCP_URL = "https://turbo-options.mcp.iqoption.com/message"

def _get_headers():
    token = os.getenv("IQ_OPTION_TOKEN")
    return {
        'Authorization': f'Bearer {token}',
        'Content-Type': 'application/json'
    }

def _fetch_balance_sync():
    """Fetches real balance from IQ Option. Runs in a thread."""
    payload = [
        {
            "jsonrpc": "2.0", "id": "init", "method": "initialize",
            "params": {
                "protocolVersion": "2024-11-05",
                "capabilities": {},
                "clientInfo": {"name": "telegram-bot", "version": "1.0.0"}
            }
        },
        {"jsonrpc": "2.0", "method": "notifications/initialized"},
        {
            "jsonrpc": "2.0", "id": "list_balances",
            "method": "tools/call",
            "params": {"name": "list_balances", "arguments": {}}
        }
    ]
    try:
        response = requests.post(MCP_URL, json=payload, headers=_get_headers(), verify=False, timeout=10)
        response.raise_for_status()
        data = response.json()
        for item in data:
            if item.get("id") == "list_balances":
                content = item.get("result", {}).get("content", [{}])[0].get("text", "{}")
                return json.loads(content)
    except Exception as e:
        logger.error(f"Error fetching balance: {e}")
    return None

def _read_trade_history():
    """Reads trade history from local CSV log."""
    csv_file = "trades.csv"
    if not os.path.isfile(csv_file):
        return []
    rows = []
    try:
        with open(csv_file, mode='r') as f:
            reader = csv.DictReader(f)
            for row in reader:
                rows.append(row)
    except Exception as e:
        logger.error(f"Error reading trade history: {e}")
    return rows

async def handle_bot_command(event):
    """
    Handles slash commands sent privately to the bot.
    This is completely separate from trade logic — read-only, no timing impact.
    """
    text = event.raw_text.strip().lower()

    if text == "/balance":
        await event.reply("Fetching your IQ Option balance...")
        try:
            data = await asyncio.to_thread(_fetch_balance_sync)
            if not data or not data.get("balances"):
                await event.reply("Could not fetch balance. Please check your IQ Option token.")
                return

            lines = ["Your IQ Option Balances:\n"]
            for b in data["balances"]:
                account_type = b.get("type", "unknown").upper()
                label = "REAL MONEY" if account_type == "REGULAR" else "DEMO"
                amount = b.get("amount", 0)
                currency = b.get("currency", "")
                lines.append(f"[{label}] {amount} {currency}")
            await event.reply("\n".join(lines))
        except Exception as e:
            await event.reply(f"Error: {e}")

    elif text == "/history":
        rows = _read_trade_history()
        if not rows:
            await event.reply(
                "No trade history found yet.\n"
                "Trades are logged here once the bot places them."
            )
            return

        # Show last 10 trades
        recent = rows[-10:]
        lines = [f"Last {len(recent)} trades:\n"]
        lines.append(f"{'Date':<12} {'Time':<10} {'Asset':<10} {'Dir':<5} {'Status'}")
        lines.append("-" * 55)
        for r in recent:
            date = r.get("Date", "")
            time = r.get("Time", "")
            asset = r.get("Asset", "")
            direction = r.get("Direction", "")
            status = r.get("Status", "")
            lines.append(f"{date:<12} {time:<10} {asset:<10} {direction:<5} {status}")

        await event.reply("```\n" + "\n".join(lines) + "\n```", parse_mode="markdown")

    elif text == "/tradeamount":
        amount = os.getenv("TRADE_AMOUNT", "10")
        account = os.getenv("ACCOUNT_TYPE", "training").upper()
        await event.reply(
            f"Current Trade Settings:\n"
            f"Account: {account}\n"
            f"Trade Amount: {amount}\n"
            f"(To change, update the env variable on Render)"
        )

    elif text == "/help":
        await event.reply(
            "Available Commands:\n\n"
            "/balance - Show your IQ Option account balance\n"
            "/history - Show last 10 trades placed by the bot\n"
            "/tradeamount - Show current trade amount setting\n"
            "/help - Show this menu"
        )
