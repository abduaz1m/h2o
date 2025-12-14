import os
import time
import schedule
from crypto_trading_agent import CryptoTradingAgent

BOT_TOKEN = os.getenv("BOT_TOKEN")
CHAT_ID = os.getenv("CHAT_ID")

if not BOT_TOKEN or not CHAT_ID:
    raise RuntimeError("BOT_TOKEN или CHAT_ID не заданы")

agent = CryptoTradingAgent(
    telegram_bot_token=BOT_TOKEN,
    telegram_chat_id=CHAT_ID
)

print("🚀 ETH OKX BOT STARTED (15m, Background Worker)")
agent.send_message("🚀 ETH OKX бот запущен (таймфрейм 15m)")

def job():
    try:
        agent.run()
    except Exception as e:
        agent.send_message(f"⚠️ Ошибка:\n{e}")

# каждые 15 минут
schedule.every(15).minutes.do(job)

# первый запуск сразу
job()

while True:
    schedule.run_pending()
    time.sleep(1)
