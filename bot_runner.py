import os
import time
from agent import TradingAgent

BOT_TOKEN = os.getenv("BOT_TOKEN")
CHAT_ID = os.getenv("CHAT_ID")
OPENAI_KEY = os.getenv("OPENAI_API_KEY") # 🆕 Берем ключ из переменных среды

# Проверка наличия ключей
if not OPENAI_KEY:
    print("❌ ОШИБКА: Не задан OPENAI_API_KEY")
    exit()

agent = TradingAgent(BOT_TOKEN, CHAT_ID, OPENAI_KEY)

agent.send("🤖 AI Agent Activated with GPT-4o-mini logic.")

while True:
    try:
        agent.analyze()
        time.sleep(60) # Простая пауза (лучше использовать "умную" паузу из прошлого ответа)
    except Exception as e:
        print(f"Critical Loop Error: {e}")
        time.sleep(60)
