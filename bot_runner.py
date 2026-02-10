import os
import time
from agent import TradingAgent

BOT_TOKEN = os.getenv("BOT_TOKEN")
CHAT_ID = os.getenv("CHAT_ID")
DEEPSEEK_KEY = os.getenv("DEEPSEEK_API_KEY")

if not DEEPSEEK_KEY:
    print("⚠️ WARNING: DEEPSEEK_API_KEY not found. Using Tech-Only mode.")
    # Можно продолжить без ключа, код агента это обработает

# Инициализация
agent = TradingAgent(BOT_TOKEN, CHAT_ID, DEEPSEEK_KEY)
agent.send("🤖 **Scalp Bot V3 Activated**\nStrategy: Bollinger + RSI (Aggressive)")

print("✅ Bot started. Waiting for market moves...")

while True:
    try:
        agent.analyze_market()
        # Пауза 30 секунд (для 5-минуток этого достаточно)
        print("⏳ Waiting 30s...")
        time.sleep(30)
    except KeyboardInterrupt:
        print("🛑 Bot stopped manually")
        break
    except Exception as e:
        print(f"❌ Critical Error: {e}")
        time.sleep(10)
