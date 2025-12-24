import os
import time
from agent 
import TradingAgent

BOT_TOKEN = os.getenv("BOT_TOKEN")
CHAT_ID = os.getenv("CHAT_ID")
DEEPSEEK_KEY = os.getenv("DEEPSEEK_API_KEY") 

# Проверка наличия ключей
if not DEEPSEEK_KEY:
    print("❌ ОШИБКА: Не задан DEEPSEEK_API_KEY")
    exit()

# Передаем ключ DeepSeek в агента
agent = TradingAgent(BOT_TOKEN, CHAT_ID, DEEPSEEK_KEY)

agent.send("🤖 AI Agent Activated with DeepSeek logic.")

while True:
    try:
        agent.analyze()
        time.sleep(60) 
    except Exception as e:
        print(f"Critical Loop Error: {e}")
        time.sleep(60)
