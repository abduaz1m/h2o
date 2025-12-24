# bot_runner.py
import os
import sys
import signal
from agent import TradingAgent

def signal_handler(sig, frame):
    print('\n🛑 Получен сигнал остановки, завершаем работу...')
    sys.exit(0)

def main():
    print("🤖 Запуск аналитического агента...")
    print("📊 Режим: Только сигналы (без автоторговли)")
    print("🔔 Сигналы будут отправляться в Telegram")
    print("="*50)
    
    # Регистрируем обработчик сигналов
    signal.signal(signal.SIGINT, signal_handler)
    
    # Проверяем необходимые переменные окружения
    if not os.getenv("DEEPSEEK_API_KEY"):
        print("⚠️  ВНИМАНИЕ: AI анализ будет отключен")
        print("   Задайте DEEPSEEK_API_KEY для полного функционала")
    
    if not os.getenv("TELEGRAM_BOT_TOKEN") or not os.getenv("TELEGRAM_CHAT_ID"):
        print("⚠️  ВНИМАНИЕ: Telegram уведомления отключены")
        print("   Задайте TELEGRAM_BOT_TOKEN и TELEGRAM_CHAT_ID для уведомлений")
    
    try:
        # Создаем агента
        agent = TradingAgent()
        
        # Запускаем
        agent.run()
        
    except KeyboardInterrupt:
        print("\n🛑 Агент остановлен пользователем")
    except Exception as e:
        print(f"❌ Критическая ошибка: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
