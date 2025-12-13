import os
import time
from crypto_trading_agent import CryptoTradingAgent

BOT_TOKEN = os.getenv("BOT_TOKEN")
CHAT_ID = os.getenv("CHAT_ID")
COINGECKO_API_KEY = os.getenv("COINGECKO_API_KEY")

if not BOT_TOKEN or not CHAT_ID or not COINGECKO_API_KEY:
    raise RuntimeError("❌ ENV variables not set")

print("🔥 ETH BOT STARTED (FINAL VERSION)")
print("📡 Background Worker mode")

agent = CryptoTradingAgent(
    telegram_bot_token=BOT_TOKEN,
    telegram_chat_id=CHAT_ID,
    coingecko_api_key=COINGECKO_API_KEY
)

# основной цикл
while True:
    try:
        agent.run()
    except Exception as e:
        print("❌ ERROR:", e)

    # ⏱ важно — защита от бана
    time.sleep(300)  # 5 минут
