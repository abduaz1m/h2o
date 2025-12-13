import os
import time
import json
import schedule
import threading
import requests
from flask import Flask, request

from crypto_trading_agent import CryptoTradingAgent


# ============================================================
# Flask (для Render, чтобы сервис не падал)
# ============================================================
app = Flask(__name__)


@app.route("/")
def home():
    return "👍 Crypto Bot is running!"


# ============================================================
# TELEGRAM ОБРАБОТЧИК ВЕБХУКА
# ============================================================
@app.route("/webhook", methods=["POST"])
def webhook():
    data = request.json

    if "message" not in data:
        return "ok"

    message = data["message"]
    chat_id = str(message["chat"]["id"])
    text = message.get("text", "")

    # Если команда — запускаем анализ
    if text == "/check":
        print("📩 Получена команда /check от пользователя")

        bot = CryptoTradingAgent(
            telegram_bot_token=os.getenv("BOT_TOKEN"),
            telegram_chat_id=chat_id
        )

        bot.send_telegram_message("🔍 Выполняю быстрый анализ (BingX)...")
        bot.run_analysis(CRYPTOS)

    return "ok"


# ============================================================
# Основной функционал бота
# ============================================================

# Загружаем переменные окружения
BOT_TOKEN = os.getenv("BOT_TOKEN")
CHAT_ID = os.getenv("CHAT_ID")
CRYPTOS = os.getenv("CRYPTOS", "bitcoin,ethereum,solana").split(",")


def run_trading_bot():
    """Запуск регулярного анализа"""
    print("\n🚀 START ANALYSIS...")
    print(f"Список монет: {CRYPTOS}")

    try:
        agent = CryptoTradingAgent(
            telegram_bot_token=BOT_TOKEN,
            telegram_chat_id=CHAT_ID
        )

        agent.run_analysis(CRYPTOS)
        print("✅ Анализ завершён!")

    except Exception as e:
        print("❌ Ошибка в run_trading_bot:", e)


def scheduler_loop():
    """Отдельный поток для планировщика"""
    print("⏱️ Scheduler started! Every 10 min.")

    # Каждые 10 минут запуск анализа
    schedule.every(10).minutes.do(run_trading_bot)

    # Первый запуск сразу
    run_trading_bot()

    while True:
        schedule.run_pending()
        time.sleep(1)


# ============================================================
# ЗАПУСК ВСЕГО БОТА
# ============================================================
if __name__ == "__main__":
    print("🔥 bot_runner.py STARTED (НОВАЯ BINGX ВЕРСИЯ)")
    print("🔧 DEBUG ENV:")
    print("BOT_TOKEN:", BOT_TOKEN)
    print("CHAT_ID:", CHAT_ID)
    print("CRYPTOS:", CRYPTOS)

    # Запуск планировщика
    thread = threading.Thread(target=scheduler_loop, daemon=True)
    thread.start()

    # Webhook URL Render → Telegram
    webhook_url = f"https://{os.getenv('RENDER_EXTERNAL_HOSTNAME')}/webhook"
    set_webhook_url = f"https://api.telegram.org/bot{BOT_TOKEN}/setWebhook"

    try:
        requests.post(set_webhook_url, data={"url": webhook_url})
        print(f"🌍 Webhook установлен: {webhook_url}")
    except Exception as e:
        print("⚠️ Ошибка установки webhook:", e)

    print("🌐 Flask server starting...")
    app.run(host="0.0.0.0", port=10000)
