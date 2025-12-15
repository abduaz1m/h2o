import os
import time
import requests
from okx_strategy import generate_signal
from llm_explainer import explain_signal

BOT_TOKEN = os.getenv("BOT_TOKEN")
CHAT_ID = os.getenv("CHAT_ID")

def send_telegram(text):
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    requests.post(url, data={
        "chat_id": CHAT_ID,
        "text": text
    })


print("🔥 OKX ETH BOT STARTED (15m, futures)")

while True:
    try:
        signal = generate_signal()

        if signal:
            base_text = (
                f"📊 ETH-USDT-SWAP (15m)\n\n"
                f"Сигнал: {signal['side']}\n"
                f"Цена: {signal['price']}\n"
                f"RSI: {signal['rsi']}\n"
                f"EMA20 / EMA50: {signal['ema_fast']} / {signal['ema_slow']}\n\n"
                f"Плечо: x{signal['leverage']}\n"
                f"TP: {signal['tp']}\n"
                f"SL: {signal['sl']}"
            )

            explanation = explain_signal(base_text)

            send_telegram(base_text + "\n\n🧠 AI:\n" + explanation)

        time.sleep(900)  # 15 минут

    except Exception as e:
        print("ERROR:", e)
        time.sleep(60)
