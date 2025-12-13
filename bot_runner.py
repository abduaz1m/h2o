import os
import time
from crypto_trading_agent import CryptoTradingAgent

BOT_TOKEN = os.getenv("BOT_TOKEN")
CHAT_ID = os.getenv("CHAT_ID")

agent = CryptoTradingAgent(
    telegram_bot_token=BOT_TOKEN,
    telegram_chat_id=CHAT_ID
)

print("🔥 ETH BOT STARTED (FINAL VERSION)")

while True:
    try:
        agent.run()
    except Exception as e:
        print("ERROR:", e)

    time.sleep(600)  # ⏱ 10 минут (НИКАКИХ 429)
