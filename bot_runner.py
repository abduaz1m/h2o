import os
import time
from crypto_trading_agent import CryptoTradingAgent

BOT_TOKEN = os.getenv("BOT_TOKEN")
CHAT_ID = os.getenv("CHAT_ID")

if not BOT_TOKEN or not CHAT_ID:
    raise RuntimeError("❌ BOT_TOKEN или CHAT_ID не заданы")

agent = CryptoTradingAgent(
    bot_token=BOT_TOKEN,
    chat_id=CHAT_ID
)

agent.send_message("🚀 ETH Binance Bot запущен и работает в фоне")

INTERVAL = 600  # 10 минут

while True:
    try:
        agent.run_once()
    except Exception as e:
        agent.send_message(f"⚠️ Ошибка: {e}")

    time.sleep(INTERVAL)
