import os
import time
from trading_agent import TradingAgent

# ================== НАСТРОЙКИ ==================
INTERVAL = 15 * 60        # 15 минут
LEVERAGE = 10             # плечо 10x
SYMBOLS = ["ETH", "SOL", "AVAX", "ARB", "OP"]  # без MATIC
# ===============================================

BOT_TOKEN = os.getenv("BOT_TOKEN")
CHAT_ID = os.getenv("CHAT_ID")

if not BOT_TOKEN or not CHAT_ID:
    raise RuntimeError("❌ BOT_TOKEN или CHAT_ID не заданы")

agent = TradingAgent(
    telegram_bot_token=BOT_TOKEN,
    telegram_chat_id=CHAT_ID,
    leverage=LEVERAGE,
    symbols=SYMBOLS,
    timeframe="15m"
)

# 🔔 СООБЩЕНИЕ ТОЛЬКО 1 РАЗ
agent.send_message(
    "🚀 ETH OKX Bot запущен\n"
    "⏱ Таймфрейм: 15m\n"
    "⚙️ Плечо: 10x\n"
    "📊 Монеты: ETH, SOL, AVAX, ARB, OP"
)

print("✅ Bot started")

# 🔁 ОСНОВНОЙ ЦИКЛ
while True:
    try:
        agent.run()
    except Exception as e:
        agent.send_message(f"⚠️ Ошибка: {e}")

    time.sleep(INTERVAL)
