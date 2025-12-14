import os
import time
from crypto_trading_agent import CryptoTradingAgent

BOT_TOKEN = os.getenv("BOT_TOKEN")
CHAT_ID = os.getenv("CHAT_ID")

INTERVAL_SECONDS = 15 * 60  # 15 минут

print("🚀 ETH OKX BOT STARTED (15m, Background Worker)")

agent = CryptoTradingAgent(
    telegram_bot_token=BOT_TOKEN,
    telegram_chat_id=CHAT_ID
)

# уведомление при запуске
agent.send_message("🚀 ETH OKX бот запущен (таймфрейм 15m)")

while True:
    try:
        agent.run()
    except Exception as e:
        agent.send_message(f"⚠️ Ошибка бота:\n{e}")
    time.sleep(INTERVAL_SECONDS)
