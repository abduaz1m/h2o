import os
import time
import schedule
import requests
from okx_data import get_candles
from strategy import signal, rsi
from risk import risk_params
from llm_analyzer import explain

BOT_TOKEN = os.getenv("BOT_TOKEN")
CHAT_ID = os.getenv("CHAT_ID")

SYMBOLS = ["ETH", "ARB", "OP", "AVAX", "NEAR"]

def send(text):
    requests.post(
        f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage",
        data={"chat_id": CHAT_ID, "text": text}
    )

send("✅ Бот запущен")  # ТОЛЬКО ОДИН РАЗ

def run():
    for sym in SYMBOLS:
        candles = get_candles(sym)
        prices = [float(c[4]) for c in candles[::-1]]

        s = signal(prices)
        if not s:
            continue

        price = prices[-1]
        tp, sl, lev = risk_params(price, s)
        r = rsi(prices)
        ai = explain(sym, s, r, lev)

        msg = f"""
📊 {sym} | OKX | 15m
Signal: {s}
Price: {price:.2f}
TP: {tp:.2f}
SL: {sl:.2f}
Leverage: {lev}x

🧠 AI:
{ai}
"""
        send(msg)
        time.sleep(2)

schedule.every(15).minutes.do(run)
run()

while True:
    schedule.run_pending()
    time.sleep(1)
