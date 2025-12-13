import os
import time
import threading
import schedule
import requests
from flask import Flask, request

from crypto_trading_agent import CryptoTradingAgent


app = Flask(__name__)

# Загружаем переменные окружения Render
BOT_TOKEN = os.getenv("BOT_TOKEN")
CHAT_ID = os.getenv("CHAT_ID")
CRYPTOS = os.getenv("CRYPTOS", "BTC,ETH,SOL").split(",")

# Приводим в формат BingX: BTC → BTC-USDT
SYMBOLS = [c.strip().upper() + "-USDT" for c in CRYPTOS]


agent = CryptoTradingAgent(BOT_TOKEN, CHAT_ID)


# ----------------------------------------------------------
# Обработка Telegram команд (webhook)
# ----------------------------------------------------------
@app.route("/", methods=["POST"])
def telegram_webhook():
    data = request.json

    if "message" in data:
        chat_id = data["message"]["chat"]["id"]
        text = data["message"].get("text", "")

        if str(chat_id) == CHAT_ID:
            handled = agent.handle_command(text, SYMBOLS)
            if handled:
                return {"ok": True}

    return {"ok": True}


# ----------------------------------------------------------
# Периодический анализ
# ----------------------------------------------------------
def run_periodic_analysis():
    print("🕒 Выполняю периодический анализ...")
    agent.run_analysis(SYMBOLS)


def start_scheduler():
    print("⏱ Scheduler started! Every 10 min.")
    schedule.every(10).minutes.do(run_periodic_analysis)

    # Первый запуск сразу
    threading.Thread(target=run_periodic_analysis, daemon=True).start()

    while True:
        schedule.run_pending()
        time.sleep(1)


# ----------------------------------------------------------
# Запуск фонового планировщика + Flask сервера
# ----------------------------------------------------------
if __name__ == "__main__":

    print("🔥 bot_runner.py STARTED (НОВАЯ BINGX ВЕРСИЯ)")

    scheduler_thread = threading.Thread(target=start_scheduler, daemon=True)
    scheduler_thread.start()

    print("🌍 Flask server starting...")
    app.run(host="0.0.0.0", port=10000)
