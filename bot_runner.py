# bot_runner.py
import os
import sys
from agent import TradingAgent

if __name__ == "__main__":
    print("🤖 Запуск аналитического агента...")
    
    # Проверяем только AI ключ (опционально)
    if not os.getenv("DEEPSEEK_API_KEY"):
        print("⚠️  ВНИМАНИЕ: AI анализ будет отключен")
        print("   Задайте DEEPSEEK_API_KEY для полного функционала")
    
    try:
        agent = TradingAgent()
        agent.run()
    except KeyboardInterrupt:
        print("\n🛑 Агент остановлен")
    except Exception as e:
        print(f"❌ Ошибка: {e}")
