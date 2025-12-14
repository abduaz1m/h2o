import os
import time
import threading
from crypto_trading_agent import CryptoTradingAgent

# ==============================
# ENV
# ==============================
BOT_TOKEN = os.getenv("BOT_TOKEN")
CHAT_ID = os.getenv("CHAT_ID")

if not BOT_TOKEN or not CHAT_ID:
    raise RuntimeError("❌ BOT_TOKEN или CHAT_ID не заданы в Render ENV")

SYMBOL = "ethereum"
INTERVAL = 600  # 10 минут

print("🔥 ETH BOT STARTED (FINAL VERSION)")
print(f"📌 SYMBOL: {SYMBOL}")
print(f"⏱ INTERVAL: {INTERVAL} sec")

# ==============================
# Agent
# ==============================
agent = CryptoTradingAgent(
    telegram_bot_token=BOT_TOKEN,
    telegram_chat_id=CHAT_ID
)

# ==============================
# Main loop
# ==============================
def run_loop():
    # Сообщение при старте (1 раз)
    agent.send_message("🚀 ETH Bot запущен и работает в фоне")

    while True:
        try:
            print("📊 Анализ ETH...")
            signal = agent.run()

            if signal:
                agent.send_message(signal)
            else:
                print("ℹ️ Нет BUY/SELL сигнала")

        except Exception as e:
            error_msg = f"❌ Ошибка в боте: {e}"
            print(error_msg)
            agent.send_message(error_msg)

        # ⏱ защита от лимитов
        time.sleep(INTERVAL)


# ==============================
# Start background thread
# ==============================
thread = threading.Thread(target=run_loop, daemon=True)
thread.start()

# Render Background Worker не должен завершаться
while True:
    time.sleep(60)
