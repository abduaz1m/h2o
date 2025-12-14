import os
import time
from crypto_trading_agent import CryptoTradingAgent

BOT_TOKEN = os.getenv("BOT_TOKEN")
CHAT_ID = os.getenv("CHAT_ID")

print("🚀 ETH Binance Bot STARTED (Background Worker)")

agent = CryptoTradingAgent(
    telegram_bot_token=BOT_TOKEN,
    telegram_chat_id=CHAT_ID
)

# --------- БЕСКОНЕЧНЫЙ ЦИКЛ ----------
while True:
    try:
        agent.run()
    except Exception as e:
        print("❌ Ошибка:", e)

    time.sleep(600)  # ⏱ 10 минут (БЕЗ БАНОВ)
