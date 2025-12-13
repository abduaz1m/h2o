print("🔥 bot_runner.py STARTED (НОВАЯ ФИНАЛЬНАЯ ВЕРСИЯ)")

import os
import time
import threading
import schedule
from crypto_trading_agent import CryptoTradingAgent
from server import app


def run_trading_bot():
    """Запуск анализа криптовалют"""
    bot_token = os.getenv("BOT_TOKEN")
    chat_id = os.getenv("CHAT_ID")
    cryptos = os.getenv("CRYPTOS", "bitcoin,ethereum").split(",")

    print("\n🔍 DEBUG:")
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
    """Фоновый планировщик"""
    print("📅 Планировщик запущен. Анализ каждые 10 минут.")

    # Каждый запуск — в новом потоке
    schedule.every(10).minutes.do(
        lambda: threading.Thread(target=run_trading_bot, daemon=True).start()
    )

    # Первый запуск — сразу и тоже в отдельном потоке
    threading.Thread(target=run_trading_bot, daemon=True).start()

    # Цикл планировщика
    while True:
        schedule.run_pending()
        time.sleep(1)


# Запускаем scheduler в отдельном потоке
scheduler_thread = threading.Thread(target=start_scheduler, daemon=True)
scheduler_thread.start()
print("🔥 Scheduler поток запущен!")


# Запускаем Flask (держит Render живым)
if __name__ == "__main__":
    print("🌐 Запускается Flask веб-сервер...")
    app.run(host="0.0.0.0", port=10000)
