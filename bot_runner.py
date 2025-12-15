import os
import time
from trading_agent import TradingAgent

BOT_TOKEN = os.getenv("BOT_TOKEN")
CHAT_ID = os.getenv("CHAT_ID")

agent = TradingAgent(BOT_TOKEN, CHAT_ID)

# 🚀 СООБЩЕНИЕ ТОЛЬКО 1 РАЗ
agent.send("🚀 ETH Bot запущен (таймфрейм 15m, плечо 10x)")

while True:
    try:
        agent.analyze()
    except Exception as e:
        agent.send(f"⚠️ Ошибка: {e}")

    time.sleep(15 * 60)  # 15 минут
