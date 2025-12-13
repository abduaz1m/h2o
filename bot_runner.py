print("🔥 bot_runner.py STARTED (ЭТО НОВАЯ ВЕРСИЯ)")
import os
import time
import threading
import schedule
from crypto_trading_agent import CryptoTradingAgent
from server import app

def run_trading_bot():
    bot_token = os.getenv('BOT_TOKEN')
    chat_id = os.getenv('CHAT_ID')
    cryptos = os.getenv('CRYPTOS', 'bitcoin,ethereum').split(',')

    print("🔍 DEBUG:")
    print("BOT_TOKEN:", bot_token)
    print("CHAT_ID:", chat_id)
    print("CRYPTOS:", cryptos)

    if not bot_token or not chat_id:
        print("❌ Переменные окружения не установлены!")
        return

    try:
        agent = CryptoTradingAgent(
            telegram_bot_token=bot_token,
            telegram_chat_id=chat_id
        )

        agent.run_analysis(cryptos)
        print("✅ Анализ завершён")

    except Exception as e:
        print("❌ Ошибка в run_trading_bot:", e)


def start_scheduler():
    print("📅 Планировщик запущен. Анализ каждые 10 минут.")
    schedule.every(10).minutes.do(run_trading_bot)

    # Первый запуск сразу
    threading.Thread(target=run_trading_bot, daemon=True).start()

    while True:
        schedule.run_pending()
        time.sleep(1)


# Запускаем scheduler перед Flask
scheduler_thread = threading.Thread(target=start_scheduler, daemon=True)
scheduler_thread.start()

print("🔥 Scheduler поток запущен!")

# Запускаем Flask-сервер
if __name__ == "__main__":
    print("🌐 Запускается Flask веб-сервер...")
    app.run(host="0.0.0.0", port=10000)
