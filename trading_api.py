import asyncio
from datetime import datetime, timedelta
import logging
import csv
import os
import requests
import json
import urllib3

# Disable insecure request warnings since we are using verify=False for safety against local SSL issues
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

logger = logging.getLogger(__name__)

CSV_FILE = "trades.csv"
MCP_URL = "https://turbo-options.mcp.iqoption.com/message"

def get_headers():
    token = os.getenv("IQ_OPTION_TOKEN")
    return {
        'Authorization': f'Bearer {token}',
        'Content-Type': 'application/json'
    }

class MCPClient:
    def __init__(self):
        self.msg_id = 1
        self.session = requests.Session()
        self.session.verify = False

    def rpc_call(self, method, params=None):
        payload = {
            "jsonrpc": "2.0",
            "id": self.msg_id,
            "method": method,
        }
        if params is not None:
            payload["params"] = params
            
        self.msg_id += 1
        
        response = self.session.post(MCP_URL, json=payload, headers=get_headers())
        response.raise_for_status()
        return response.json()

    def rpc_notify(self, method, params=None):
        payload = {
            "jsonrpc": "2.0",
            "method": method,
        }
        if params is not None:
            payload["params"] = params
        self.session.post(MCP_URL, json=payload, headers=get_headers())

    def initialize(self):
        logger.info("Initializing MCP Session with IQ Option...")
        # 1. Send initialize
        init_params = {
            "protocolVersion": "2024-11-05",
            "capabilities": {},
            "clientInfo": {"name": "telegram-bot", "version": "1.0.0"}
        }
        res = self.rpc_call("initialize", init_params)
        
        if "error" in res:
            logger.error(f"Failed to initialize: {res['error']}")
            return False
            
        # 2. Send initialized notification
        self.rpc_notify("notifications/initialized")
        logger.info("MCP Session Initialized!")
        return True

    def call_tool(self, tool_name, arguments):
        params = {
            "name": tool_name,
            "arguments": arguments
        }
        res = self.rpc_call("tools/call", params)
        if "error" in res:
            raise Exception(f"Tool {tool_name} error: {res['error']}")
            
        # The result of a tool call is usually in res['result']['content'][0]['text'] (as JSON string)
        try:
            content = res['result']['content'][0]['text']
            return json.loads(content)
        except Exception as e:
            logger.error(f"Failed to parse tool response: {res}")
            raise e

def is_trading_hours() -> bool:
    return datetime.now().weekday() < 5


# Tweak this value if your computer's clock is slightly faster or slower than IQ Option's server.
# Because the bot is now hosted on Render (which has a perfectly accurate clock), 
# we set this to a slightly negative number to account for network latency.
TRADE_DELAY_SECONDS = -0.525

def _execute_mcp_batch(batch_commands):
    payload = []
    # Every batch MUST start with initialize and notifications/initialized
    payload.append({
        "jsonrpc": "2.0",
        "id": "init",
        "method": "initialize",
        "params": {
            "protocolVersion": "2024-11-05",
            "capabilities": {},
            "clientInfo": {"name": "telegram-bot", "version": "1.0.0"}
        }
    })
    payload.append({
        "jsonrpc": "2.0",
        "method": "notifications/initialized"
    })
    
    for cmd in batch_commands:
        payload.append(cmd)
        
    response = requests.post(MCP_URL, json=payload, headers=get_headers(), verify=False)
    response.raise_for_status()
    return response.json()

def _sync_prepare_trade(asset_name: str, trade_time: datetime):
    """Fetches balances and assets BEFORE the wait timer."""
    logger.info("Fetching balances and assets from IQ Option...")
    read_batch = [
        {"jsonrpc": "2.0", "id": "list_balances", "method": "tools/call", "params": {"name": "list_balances", "arguments": {}}},
        {"jsonrpc": "2.0", "id": "list_assets", "method": "tools/call", "params": {"name": "list_assets", "arguments": {}}}
    ]
    
    read_results = _execute_mcp_batch(read_batch)
    
    balances_result = None
    assets_result = None
    
    for res in read_results:
        if res.get("id") == "list_balances":
            content = res.get("result", {}).get("content", [{}])[0].get("text", "{}")
            balances_result = json.loads(content)
        elif res.get("id") == "list_assets":
            content = res.get("result", {}).get("content", [{}])[0].get("text", "{}")
            assets_result = json.loads(content)
            
    if not balances_result or not assets_result:
        return None, "READ_BATCH_FAILED"
        
    target_balance_id = None
    target_balance_amount = 0
    account_type_env = os.getenv("ACCOUNT_TYPE", "training").lower()
    
    # IQ Option uses "regular" for real money accounts and "training" for demo accounts
    if account_type_env == "real":
        valid_types = ["regular", "real", "1", 1]
    else:
        valid_types = ["training", "practice", "4", 4]
    
    for b in balances_result.get("balances", []):
        if b.get("type") in valid_types:
            target_balance_id = b.get("balance_id")
            target_balance_amount = b.get("amount", 0)
            break
            
    if not target_balance_id:
        return None, f"NO_{account_type_env.upper()}_BALANCE"
        
    target_asset = None
    search_name = asset_name.upper()
    search_name_no_slash = search_name.replace("/", "")
    
    for a in assets_result.get("assets", []):
        a_name = str(a.get("name", "")).upper()
        if a_name == search_name or a_name == search_name_no_slash:
            target_asset = a
            break
            
    if not target_asset:
        return None, "ASSET_NOT_FOUND"
        
    asset_id = target_asset["asset_id"]
    profit_percent = target_asset.get("profit_percent", 0)
    expirations = target_asset.get("expirations", [])
    
    if not expirations:
        return None, "NO_EXPIRATIONS"
        
    target_expiration_dt = trade_time + timedelta(minutes=1)
    target_ts = int(target_expiration_dt.timestamp())
    
    future_expirations = [ts for ts in expirations if ts >= target_ts]
    best_expiration = min(future_expirations) if future_expirations else max(expirations)
    
    return {
        "asset_id": asset_id,
        "balance_id": target_balance_id,
        "balance_amount": target_balance_amount,
        "profit_percent": profit_percent,
        "expiration": best_expiration
    }, "SUCCESS"

def _sync_execute_trade(trade_args: dict):
    """Executes the trade INSTANTLY after the wait timer finishes."""
    try:
        trade_batch = [
            {"jsonrpc": "2.0", "id": "place_trade", "method": "tools/call", "params": {"name": "place_trade", "arguments": trade_args}}
        ]
        
        trade_result = _execute_mcp_batch(trade_batch)
        
        for res in trade_result:
            if res.get("id") == "place_trade":
                if "error" in res:
                    logger.error(f"Trade failed (JSON-RPC): {res['error']}")
                    return False, f"TRADE_ERROR: {res['error']}"
                elif res.get("result", {}).get("isError") == True:
                    err_msg = res.get("result", {}).get("content", [{}])[0].get("text", "Unknown Tool Error")
                    logger.error(f"Trade failed (Tool Error): {err_msg}")
                    return False, f"TRADE_ERROR: {err_msg}"
                else:
                    account_type = os.getenv("ACCOUNT_TYPE", "training").upper()
                    logger.info(f"✅ Trade successfully placed on IQ Option {account_type} Account!")
                    return True, "SUCCESS"
                    
        return False, "UNKNOWN_TRADE_RESPONSE"
        
    except Exception as e:
        logger.error(f"Error executing MCP trade: {e}")
        return False, f"ERROR: {str(e)}"

async def schedule_trade(asset: str, direction: str, client=None):
    from bot_logic import send_loud_notification
    if not is_trading_hours():
        logger.warning(f"Trade skipped for {asset} {direction}: Outside trading hours (Weekend).")
        log_trade(asset, direction, "SKIPPED_WEEKEND")
        await send_loud_notification(f"Trade skipped for {asset} {direction}: Outside trading hours (Weekend).")
        return

    now = datetime.now()
    # Always target the NEXT minute candle.
    # Even if the signal arrives at :58/:59 and the API prep takes ~1s,
    # we fire immediately at 12:06:00 — the candle just opened and IQ Option still accepts it.
    next_minute = (now + timedelta(minutes=1)).replace(second=0, microsecond=0)
    
    # Fetch all API data and IDs immediately so we don't waste time at the 00 second mark
    prep_data, status = await asyncio.to_thread(_sync_prepare_trade, asset, next_minute)
    if prep_data is None:
        logger.error(f"Failed to prepare trade: {status}")
        log_trade(asset, direction, status, next_minute)
        
        # Send loud Telegram notification based on error type
        from bot_logic import send_loud_notification
        if status == "ASSET_NOT_FOUND":
            await send_loud_notification(f"⚠️ Asset not found on IQ Option: {asset}\nNo trade was placed.")
        else:
            await send_loud_notification(f"❌ Failed to prepare trade for {asset}: {status}")
        return
        
    api_direction = "call" if direction.upper() == "CALL" else "put"
    
    trade_amount_env = os.getenv("TRADE_AMOUNT", "10").strip()
    
    if float(prep_data["balance_amount"]) <= 0:
        logger.error("Trade aborted: Account balance is zero.")
        log_trade(asset, direction, "INSUFFICIENT_FUNDS", next_minute)
        from bot_logic import send_loud_notification
        await send_loud_notification(f"❌ Trade skipped for {asset}.\nReason: Your account balance is $0.00!")
        return

    if trade_amount_env.endswith("%"):
        percent = float(trade_amount_env.replace("%", "")) / 100
        trade_amount = float(prep_data["balance_amount"]) * percent
        trade_amount = round(trade_amount, 2)
        # Cap at IQ Option maximum (default $20,000)
        max_allowed = float(os.getenv("MAX_TRADE_AMOUNT", "20000"))
        trade_amount = min(trade_amount, max_allowed)
    else:
        trade_amount = float(trade_amount_env)
        
    trade_args = {
        "asset_id": prep_data["asset_id"],
        "direction": api_direction,
        "expired": prep_data["expiration"],
        "amount": trade_amount,
        "profit_percent": prep_data["profit_percent"],
        "balance_id": prep_data["balance_id"]
    }
    
    # 2. Precision Sleep Timer
    # We sleep until slightly before the target, then spin-wait for exact microsecond accuracy
    # We also apply TRADE_DELAY_SECONDS to account for the computer clock being slightly faster than IQ Option's servers.
    target_time = next_minute + timedelta(seconds=TRADE_DELAY_SECONDS)
    
    logger.info(f"Target execution set for {target_time.strftime('%H:%M:%S.%f')[:-3]} (Includes {TRADE_DELAY_SECONDS}s offset). Waiting...")
    
    while True:
        now = datetime.now()
        diff = (target_time - now).total_seconds()
        
        if diff <= 0:
            break
        elif diff > 0.1:
            await asyncio.sleep(diff - 0.05)
        else:
            await asyncio.sleep(0) # Spin-wait yield for the last few milliseconds
            
    # 3. Fire trade instantly
    logger.info(f"EXECUTING IQ OPTION TRADE -> Asset: {asset} | Direction: {direction} | Time: {datetime.now().strftime('%H:%M:%S.%f')[:-3]}")
    success, exec_status = await asyncio.to_thread(_sync_execute_trade, trade_args)
    
    log_trade(asset, direction, exec_status, next_minute)
    
    from bot_logic import send_loud_notification
    if success:
        await send_loud_notification(f"✅ Trade placed successfully!\nAsset: {asset}\nDirection: {direction}\nAmount: ${trade_args['amount']}")
    else:
        await send_loud_notification(f"❌ Failed to execute trade for {asset}.\nReason: {exec_status}")

def log_trade(asset: str, direction: str, status: str, trade_time: datetime = None):
    if trade_time is None:
        trade_time = datetime.now()
        
    file_exists = os.path.isfile(CSV_FILE)
    
    with open(CSV_FILE, mode='a', newline='') as file:
        writer = csv.writer(file)
        if not file_exists:
            writer.writerow(['Date', 'Time', 'Asset', 'Direction', 'Status'])
            
        writer.writerow([
            trade_time.strftime('%Y-%m-%d'),
            trade_time.strftime('%H:%M:%S'),
            asset,
            direction,
            status
        ])
