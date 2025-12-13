import os
import time
import threading
import schedule
import requests

from crypto_trading_agent import CryptoTradingAgent
from server import app


# ----------------------------------------------------------
#  Обработчик входящих Telegram-команд
# ----------------------------------------------------------
def listen_for_commands(agent, cryptos):
    print("📨 Командный слушатель запущен...")

    url = f"https://api.telegram.org/bot{agent.telegram_bot_token}/getUpdates"
    last_update_id = None

    while True:
        try:
            params = {"offset": last_update_id, "timeout": 10}
            response = requests.get(url, params=params).json()

            if "result" in response:
                for update in response["result"]:
                    last_update_id = update["update_id"] + 1

                    if "message" in update:
                        text = update["message"].get("text", "")
                        print(f"📩 Получена команда: {text}")

                        # передаём команду в класс агента
                        agent.handle_command(text, cryptos)

        except Exception as e:
            print("❌ Ошибка listen_for_commands:", e)

        time.sleep(2)


# ----------------------------------------------------------
# Запуск торгового анализа
# ----------------------------------------------------------
def run_trading_bot():
    bot_token = os.getenv('BOT_TOKEN')
    chat_id = os.getenv('CHAT_ID')
    cryptos = os.getenv('CRYPTOS', 'bitcoin,ethereum').split(',')

    print("🔍 DEBUG ENV:")
    print("BOT_TOKEN:", bot_token)
    print("CHAT_ID:", chat_id)
    print("CRYPTOS:", cryptos)

    if not bot_token or not chat_id:
        print("❌ Ошибка: переменные окружения не установлены!")
        return

    try:
        agent = CryptoTradingAgent(
            telegram_bot_token=bot_token,
            telegram_chat_id=chat_id
        )

        # 🚀 Запускаем обработчик команд /check
        threading.Thread(
            target=listen_for_commands,
            args=(agent, cryptos),
            daemon=True
        ).start()

        # Запуск анализа
        print("🚀 START ANALYSIS...")
        agent.run_analysis(cryptos)

    except Exception as e:
        print("❌ Ошибка в run_trading_bot:", e)


# ----------------------------------------------------------
# Планировщик (каждые 10 минут)
# ----------------------------------------------------------
def start_scheduler():
    print("⏱️ Scheduler started! Every 10 min.")

    schedule.every(10).minutes.do(run_trading_bot)

    # Первый запуск сразу!
    run_trading_bot()

    while True:
        schedule.run_pending()
        time.sleep(1)


# ----------------------------------------------------------
# Запуск приложения Render
# ----------------------------------------------------------
if __name__ == "__main__":
    print("🔥 bot_runner.py STARTED (НОВАЯ ФИНАЛЬНАЯ ВЕРСИЯ)")

    # Scheduler в отдельном потоке
    threading.Thread(target=start_scheduler, daemon=True).start()

    print("🌐 Flask server starting...")
    app.run(host="0.0.0.0", port=10000)
