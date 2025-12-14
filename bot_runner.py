import os
import time
import threading
from crypto_trading_agent import CryptoTradingAgent

# =========================
# ENV
# =========================
BOT_TOKEN = os.getenv("BOT_TOKEN")
CHAT_ID = os.getenv("CHAT_ID")
COINGECKO_API_KEY = os.getenv("COINGECKO_API_KEY", "")

SYMBOL = "ethereum"
INTERVAL = 600  # 10 минут

print("🔥 ETH BOT STARTED (FINAL VERSION)")
print(f"📌 SYMBOL: {SYMBOL}")
print(f"⏱ INTERVAL: {INTERVAL} sec")

# =========================
# INIT AGENT
# =========================
agent = CryptoTradingAgent(
    telegram_bot_token=BOT_TOKEN,
    telegram_chat_id=CHAT_ID,
    coingecko_api_key=COINGECKO_API_KEY
)

# =========================
# ANALYSIS LOOP
# =========================
def run_loop():
    # Сообщение при старте
    agent.send_message("🚀 ETH Bot запущен и работает в фоне")

    while True:
        try:
            print("🔍 Анализ ETH...")
            agent.run()   # анализ + отправка сигнала
        except Exception as e:
            print("❌ ERROR:", e)
            agent.send_message(f"❌ Ошибка бота:\n{e}")

        time.sleep(INTERVAL)


# =========================
# START BACKGROUND WORKER
# =========================
threading.Thread(target=run_loop, daemon=True).start()

# Render Background Worker не должен завершаться
while True:
    time.sleep(60)
