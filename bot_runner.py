import os
import time
import threading
import schedule
from crypto_trading_agent import CryptoTradingAgent
from server import app


def run_bot():
    bot_token = os.getenv("BOT_TOKEN")
    chat_id = os.getenv("CHAT_ID")
    cryptos = os.getenv("CRYPTOS", "bitcoin,ethereum").split(",")

    print("🔍 DEBUG:", bot_token, chat_id, cryptos)

    agent = CryptoTradingAgent(bot_token, chat_id)
    agent.run_analysis(cryptos)


def scheduler_loop():
    print("⏱ Scheduler started! Every 10 min.")
    schedule.every(10).minutes.do(run_bot)

    run_bot()  # первый запуск

    while True:
        schedule.run_pending()
        time.sleep(1)


# Запускаем планировщик в отдельном потоке
threading.Thread(target=scheduler_loop, daemon=True).start()


# Flask сервер
if __name__ == "__main__":
    print("🌍 Flask server starting...")
    app.run(host="0.0.0.0", port=10000)
