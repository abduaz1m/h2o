import os
import time
import requests
from strategy import fetch_candles, add_indicators, generate_signal

BOT_TOKEN = os.getenv("BOT_TOKEN")
CHAT_ID = os.getenv("CHAT_ID")

if not BOT_TOKEN or not CHAT_ID:
    raise RuntimeError("❌ BOT_TOKEN или CHAT_ID не заданы")

def send_message(text):
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    requests.post(url, data={
        "chat_id": CHAT_ID,
        "text": text
    })

print("🚀 OKX ETH 15m BOT STARTED")

last_signal = None

while True:
    try:
        df = fetch_candles()
        df = add_indicators(df)

        signal, leverage = generate_signal(df)

        if signal and signal != last_signal:
            price = df.iloc[-1]["c"]

            msg = (
                f"📊 ETH FUTURES SIGNAL (OKX 15m)\n\n"
                f"Action: {signal}\n"
                f"Price: {price}\n"
                f"Leverage: x{leverage}\n\n"
                f"Strategy: EMA20/50 + RSI\n"
            )

            send_message(msg)
            last_signal = signal

        time.sleep(60)

    except Exception as e:
        print("ERROR:", e)
        time.sleep(60)
