import os
import time
from agent import TradingAgent

# Проверка наличия ключей
if not os.getenv("DEEPSEEK_API_KEY"):
    print("❌ ОШИБКА: Не задан DEEPSEEK_API_KEY")
    exit()

# Создаем агента
agent = TradingAgent()

# Отправляем сообщение о старте
agent.send_telegram("🤖 Bot started with DeepSeek V3 engine")

# Запускаем цикл вручную
try:
    while True:
        sleep_time = agent.run_cycle()
        time.sleep(sleep_time)
except KeyboardInterrupt:
    agent.log("🛑 Остановка по команде пользователя")
    agent.send_telegram("🛑 *Торговый агент остановлен*")
except Exception as e:
    agent.log(f"💥 Критическая ошибка: {e}", "CRITICAL")
    agent.send_telegram(f"💥 *Критическая ошибка:* {str(e)}")
    raise
