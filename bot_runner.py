import os
import time
from crypto_trading_agent import CryptoTradingAgent

BOT_TOKEN = os.getenv("BOT_TOKEN")
CHAT_ID = os.getenv("CHAT_ID")

agent = CryptoTradingAgent(BOT_TOKEN, CHAT_ID)

print("🚀 ETH Binance Bot started")

while True:
    try:
        agent.run()
        time.sleep(900)  # 15 минут
    except Exception as e:
        print("❌ Error:", e)
        time.sleep(60)
