import os
import time
import threading
from okx_strategy import OKXStrategy
from llm_explainer import explain_signal

BOT_TOKEN = os.getenv("BOT_TOKEN")
CHAT_ID = os.getenv("CHAT_ID")

SYMBOLS = [
    "ETH-USDT-SWAP",
    "OP-USDT-SWAP",
    "ARB-USDT-SWAP",
    "AVAX-USDT-SWAP",
    "NEAR-USDT-SWAP"
]

INTERVAL = 15 * 60   # 15 минут
LEVERAGE = 10

def send_message(text):
    import requests
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    requests.post(url, json={
        "chat_id": CHAT_ID,
        "text": text
    })

def run_loop():
    send_message(
        "🚀 ETH OKX Bot запущен\n"
        "⏱ Таймфрейм: 15m\n"
        "⚙️ Плечо: 10x\n"
        "📊 Монеты: ETH / OP / ARB / AVAX / NEAR"
    )

    strategy = OKXStrategy()

    while True:
        for symbol in SYMBOLS:
            try:
                signal = strategy.analyze(symbol)

                if signal["action"] in ("BUY", "SELL"):
                    explanation = explain_signal(signal)
                    msg = (
                        f"📊 {symbol}\n"
                        f"🧭 Сигнал: {signal['action']}\n"
                        f"💰 Цена: {signal['price']}\n"
                        f"📉 RSI: {signal['rsi']}\n"
                        f"📈 EMA: {signal['ema_fast']} / {signal['ema_slow']}\n"
                        f"🎯 TP: {signal['tp']}\n"
                        f"🛑 SL: {signal['sl']}\n"
                        f"⚙️ Плечо: 10x\n\n"
                        f"🤖 AI:\n{explanation}"
                    )
                    send_message(msg)

            except Exception as e:
                send_message(f"⚠️ Ошибка {symbol}: {e}")

        time.sleep(INTERVAL)

if __name__ == "__main__":
    threading.Thread(target=run_loop, daemon=True).start()
    while True:
        time.sleep(60)
