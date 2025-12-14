import os
import time
import schedule
from crypto_trading_agent import CryptoTradingAgent

BOT_TOKEN = os.getenv("BOT_TOKEN")
CHAT_ID = os.getenv("CHAT_ID")

if not BOT_TOKEN or not CHAT_ID:
    raise RuntimeError("BOT_TOKEN или CHAT_ID не заданы")

agent = CryptoTradingAgent(BOT_TOKEN, CHAT_ID)

print("🔥 OKX ETH Futures Bot started (15m)")

def job():
    try:
        agent.run()
    except Exception as e:
        print("ERROR:", e)

# каждые 15 минут
schedule.every(15).minutes.do(job)

# первый запуск
job()

while True:
    schedule.run_pending()
    time.sleep(5)
