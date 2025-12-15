import os
import time
from agent import TradingAgent

BOT_TOKEN = os.getenv("BOT_TOKEN")
CHAT_ID = os.getenv("CHAT_ID")

INTERVAL_SECONDS = 15 * 60  # 15 минут

agent = TradingAgent(BOT_TOKEN, CHAT_ID)

# 🔥 1 РАЗ ПРИ СТАРТЕ
agent.send(
    "🚀 ETH OKX Bot запущен\n"
    "⏱ Таймфрейм: 15m\n"
    "⚙️ Плечо: 10x"
)

# ♻️ ОСНОВНОЙ ЦИКЛ
while True:
    agent.analyze()

    # ❤️ heartbeat раз в 15 минут
    agent.send("💓 Bot alive | OKX 15m")

    time.sleep(INTERVAL_SECONDS)
