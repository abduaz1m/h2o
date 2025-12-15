import os
import time
from trading_agent import TradingAgent

BOT_TOKEN = os.getenv("BOT_TOKEN")
CHAT_ID = os.getenv("CHAT_ID")

if not BOT_TOKEN or not CHAT_ID:
    raise RuntimeError("BOT_TOKEN или CHAT_ID не заданы")

agent = TradingAgent(BOT_TOKEN, CHAT_ID)

agent.send_message("🚀 ETH OKX Bot запущен\n⏱ Таймфрейм: 15m\n⚙️ Плечо: 10x")

INTERVAL = 900  # 15 минут

while True:
    try:
        agent.run()
    except Exception as e:
        agent.send_message(f"❌ Критическая ошибка: {e}")

    time.sleep(INTERVAL)
