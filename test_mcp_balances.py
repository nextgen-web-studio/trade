import os
import json
import requests
from dotenv import load_dotenv
import urllib3

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
load_dotenv()

MCP_URL = "https://turbo-options.mcp.iqoption.com/message"
token = os.getenv("IQ_OPTION_TOKEN")

headers = {
    'Authorization': f'Bearer {token}',
    'Content-Type': 'application/json'
}

payload = [
    {
        "jsonrpc": "2.0",
        "id": "init",
        "method": "initialize",
        "params": {
            "protocolVersion": "2024-11-05",
            "capabilities": {},
            "clientInfo": {"name": "telegram-bot", "version": "1.0.0"}
        }
    },
    {
        "jsonrpc": "2.0",
        "method": "notifications/initialized"
    },
    {
        "jsonrpc": "2.0",
        "id": "list_balances",
        "method": "tools/call",
        "params": {"name": "list_balances", "arguments": {}}
    }
]

response = requests.post(MCP_URL, json=payload, headers=headers, verify=False)
data = response.json()

print(json.dumps(data, indent=2))
