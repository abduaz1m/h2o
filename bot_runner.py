import os
import time
import schedule
from crypto_trading_agent import CryptoTradingAgent

def run_trading_bot():
    print("🚀 Запуск торгового бота...")

    # Загружаем переменные окружения
    bot_token = os.getenv('8541003949:AAFFwvo3kiTERGoD8iOenkIOgfEFyIJXRwc')
    chat_id = os.getenv('150858460')
    cryptos_raw = os.getenv('CRYPTOS', 'bitcoin,ethereum')
    cryptos = cryptos_raw.split(',')

    print(f"🤖 Анализ монет: {', '.join(cryptos)}")

    if not bot_token or not chat_id:
        print("❌ Ошибка: BOT_TOKEN или CHAT_ID не установлены в Render Environment!")
        return

    # Создаем торгового агента
    agent = CryptoTradingAgent(
        telegram_bot_token=bot_token,
        telegram_chat_id=chat_id
    )

    # Запускаем анализ
    agent.run_analysis(cryptos)

    print("✅ Анализ завершен.\n")


# Запускаем бота каждые 10 минут (можешь изменить)
schedule.every(10).minutes.do(run_trading_bot)

print("🤖 Bot Runner запущен... Ожидание следующего запуска...")

# Первый запуск сразу после старта
run_trading_bot()

# Основной цикл
while True:
    schedule.run_pending()
    time.sleep(1)
