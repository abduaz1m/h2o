import os
import time
from crypto_trading_agent import CryptoTradingAgent

BOT_TOKEN = os.getenv("BOT_TOKEN")
CHAT_ID = os.getenv("CHAT_ID")

if not BOT_TOKEN or not CHAT_ID:
    raise RuntimeError("❌ BOT_TOKEN или CHAT_ID не заданы")

agent = CryptoTradingAgent(
    telegram_token=BOT_TOKEN,
    chat_id=CHAT_ID
)

print("🚀 ETH OKX Bot запущен (15m, Futures, Background Worker)")

while True:
    try:
        agent.run()
    except Exception as e:
        agent.send_message(f"⚠️ Ошибка бота:\n{e}")
    time.sleep(900)  # ⏱ 15 минут
