import os
import time
import threading
import schedule
from crypto_trading_agent import CryptoTradingAgent
from server import app  # импортируем Flask сервер

def run_trading_bot():
    bot_token = os.getenv('8541003949:AAFFwvo3kiTERGoD8iOenkIOgfEFyIJXRwc')
    chat_id = os.getenv('150858460')
    cryptos = os.getenv('CRYPTOS', 'bitcoin,ethereum').split(',')

    if not bot_token or not chat_id:
        print("❌ Переменные окружения не установлены!")
        return

    agent = CryptoTradingAgent(
        telegram_bot_token=bot_token,
        telegram_chat_id=chat_id
    )

    agent.run_analysis(cryptos)
    print("✅ Анализ завершён")


def start_scheduler():
    schedule.every(10).minutes.do(run_trading_bot)
    run_trading_bot()

    while True:
        schedule.run_pending()
        time.sleep(1)


# --- Запускаем scheduler в отдельном потоке ---
threading.Thread(target=start_scheduler, daemon=True).start()

# --- Запускаем Flask-сервер (держит Render живым) ---
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=10000)
