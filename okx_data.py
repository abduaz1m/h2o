import requests

BASE = "https://www.okx.com/api/v5/market/candles"

def get_candles(symbol, limit=200):
    params = {
        "instId": symbol + "-USDT-SWAP",
        "bar": "15m",
        "limit": limit
    }
    r = requests.get(BASE, params=params, timeout=10).json()
    return r["data"] if r.get("data") else []
