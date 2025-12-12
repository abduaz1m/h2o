import os
import time
import schedule
from crypto_trading_agent import CryptoTradingAgent

def run_trading_bot():
    # Получаем настройки из переменных окружения
    bot_token = os.getenv('8541003949:AAFFwvo3kiTERGoD8iOenkIOgfEFyIJXRwc')
    chat_id = os.getenv('150858460')
    cryptos = os.getenv('CRYPTOS', 'bitcoin,ethereum,cardano').split(',')
    
    print(f"🤖 Запуск бота для анализа: {', '.join(cryptos)}")
    
    # Создаем агента
    agent = CryptoTradingAgent(
        telegram_bot_token=bot_token,
        telegram_chat_id=chat_id
    )
    
    # Запускаем анализ
    agent.run_analysis(cryptos)
    print("✅ Анализ завершен")

def main():
    print("=" * 60)
    print("🚀 CRYPTO TRADING BOT STARTED")
    print("=" * 60)
    
    # Проверяем переменные окружения
    if not os.getenv('TELEGRAM_BOT_TOKEN'):
        print("❌ ОШИБКА: TELEGRAM_BOT_TOKEN не установлен!")
        return
    
    if not os.getenv('TELEGRAM_CHAT_ID'):
        print("❌ ОШИБКА: TELEGRAM_CHAT_ID не установлен!")
        return
    
    # Получаем интервал проверки (по умолчанию 1 час)
    check_interval = int(os.getenv('CHECK_INTERVAL', '3600'))
    
    print(f"⏰ Интервал проверки: {check_interval} секунд")
    
    # Первый запуск сразу
    run_trading_bot()
    
    # Настраиваем расписание
    schedule.every(check_interval).seconds.do(run_trading_bot)
    
    # Бесконечный цикл
    while True:
        schedule.run_pending()
        time.sleep(60)

if __name__ == "__main__":
    main()
