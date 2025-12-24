import os
import time
from agent import TradingAgent

BOT_TOKEN = os.getenv("BOT_TOKEN")
CHAT_ID = os.getenv("CHAT_ID")
DEEPSEEK_KEY = os.getenv("DEEPSEEK_API_KEY")

if not DEEPSEEK_KEY:
    print("❌ ОШИБКА: Не задан DEEPSEEK_API_KEY")
    exit()

agent = TradingAgent(BOT_TOKEN, CHAT_ID, DEEPSEEK_KEY)
agent.send("🤖 AI Agent by Azim Activated logic.")

while True:
    try:
        agent.analyze()
        print("Waiting 60s...")
        time.sleep(60)
    except Exception as e:
        print(f"Critical Loop Error: {e}")
        time.sleep(60)
