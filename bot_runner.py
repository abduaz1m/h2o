import os
import time
import requests
from trading_agent import TradingAgent
from llm_explainer import explain

BOT_TOKEN = os.getenv("BOT_TOKEN")
CHAT_ID = os.getenv("CHAT_ID")

agent = TradingAgent()

def send(text):
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    requests.post(url, data={"chat_id": CHAT_ID, "text": text})

print("🔥 OKX ETH BOT STARTED")

while True:
    try:
        signal = agent.analyze()
        if signal:
            ai_text = explain(signal)
            msg = f"""
📊 ETH FUTURES SIGNAL (15m)

📍 Signal: {signal['signal']}
💰 Price: {signal['price']:.2f}
📈 EMA50 / EMA200
RSI: {signal['rsi']:.2f}

🎯 TP: {signal['tp']:.2f}
🛑 SL: {signal['sl']:.2f}
⚖️ Leverage: x{signal['leverage']}

🧠 AI:
{ai_text}

⏰ {signal['time']}
"""
            send(msg)
            time.sleep(900)  # анти-дубликаты
        time.sleep(60)
    except Exception as e:
        print("ERROR:", e)
        time.sleep(30)
