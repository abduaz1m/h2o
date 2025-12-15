import requests
import pandas as pd
import time

OKX_CANDLES_URL = "https://www.okx.com/api/v5/market/candles"

def fetch_candles():
    params = {
        "instId": "ETH-USDT-SWAP",
        "bar": "15m",
        "limit": 100
    }
    r = requests.get(OKX_CANDLES_URL, params=params, timeout=10)
    r.raise_for_status()
    data = r.json()["data"]

    df = pd.DataFrame(data, columns=[
        "ts","o","h","l","c","vol","volCcy","volCcyQuote","confirm"
    ])

    df["c"] = df["c"].astype(float)
    return df.sort_index()

def add_indicators(df):
    df["EMA20"] = df["c"].ewm(span=20).mean()
    df["EMA50"] = df["c"].ewm(span=50).mean()

    delta = df["c"].diff()
    gain = delta.clip(lower=0).rolling(14).mean()
    loss = -delta.clip(upper=0).rolling(14).mean()
    rs = gain / loss
    df["RSI"] = 100 - (100 / (1 + rs))

    return df

def generate_signal(df):
    last = df.iloc[-1]
    prev = df.iloc[-2]

    # BUY
    if last["EMA20"] > last["EMA50"] and prev["RSI"] < 30 and last["RSI"] > 30:
        return "BUY", dynamic_leverage(last["RSI"])

    # SELL
    if last["EMA20"] < last["EMA50"] and prev["RSI"] > 70 and last["RSI"] < 70:
        return "SELL", dynamic_leverage(last["RSI"])

    return None, None

def dynamic_leverage(rsi):
    if rsi < 25 or rsi > 75:
        return 10
    if rsi < 35 or rsi > 65:
        return 7
    return 5
