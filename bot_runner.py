# bot_runner.py
import os
import sys

# Добавляем путь к проекту
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from agent import TradingAgent

def main():
    print("🤖 Запуск торгового бота...")
    
    # Проверка обязательных переменных
    required_vars = ["OKX_API_KEY", "OKX_API_SECRET", "OKX_PASSWORD"]
    missing_vars = [var for var in required_vars if not os.getenv(var)]
    
    if missing_vars:
        print(f"❌ Отсутствуют переменные окружения: {', '.join(missing_vars)}")
        sys.exit(1)
    
    try:
        # Создаем агента
        agent = TradingAgent()
        
        # Запускаем
        agent.run()
        
    except KeyboardInterrupt:
        print("\n🛑 Бот остановлен пользователем")
    except Exception as e:
        print(f"💥 Критическая ошибка: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
