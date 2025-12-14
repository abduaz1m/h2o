import os
import time
from crypto_trading_agent import CryptoTradingAgent

BOT_TOKEN = os.getenv("BOT_TOKEN")
CHAT_ID = os.getenv("CHAT_ID")

INTERVAL_SECONDS = 600  # 10 минут

if not BOT_TOKEN or not CHAT_ID:
    raise RuntimeError("❌ BOT_TOKEN или CHAT_ID не заданы")

print("🔥 ETH BINANCE BOT STARTED (BACKGROUND WORKER)")
print("⏱ Interval:", INTERVAL_SECONDS, "sec")

agent = CryptoTradingAgent(
    telegram_bot_token=BOT_TOKEN,
    telegram_chat_id=CHAT_ID
)

agent.send_message("🚀 ETH Binance Bot запущен и работает в фоне")

while True:
    try:
        agent.run()
    except Exception as e:
        agent.send_message(f"⚠️ Ошибка:\n{e}")

    time.sleep(INTERVAL_SECONDS)
