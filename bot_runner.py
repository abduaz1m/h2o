import os
import time
import threading

from crypto_trading_agent import CryptoTradingAgent

# ===============================
# ENV
# ===============================
BOT_TOKEN = os.getenv("BOT_TOKEN")
CHAT_ID = os.getenv("CHAT_ID")
COINGECKO_API_KEY = os.getenv("COINGECKO_API_KEY")

if not BOT_TOKEN or not CHAT_ID or not COINGECKO_API_KEY:
    raise RuntimeError("❌ Не заданы BOT_TOKEN / CHAT_ID / COINGECKO_API_KEY")

# ===============================
# CONFIG
# ===============================
SYMBOL = "ethereum"
INTERVAL_SECONDS = 600  # 10 минут

print("🔥 ETH BOT STARTED (FINAL VERSION)")
print(f"🪙 SYMBOL: {SYMBOL}")
print(f"⏱ INTERVAL: {INTERVAL_SECONDS} sec")

# ===============================
# INIT AGENT
# ===============================
agent = CryptoTradingAgent(
    telegram_bot_token=BOT_TOKEN,
    telegram_chat_id=CHAT_ID,
    coingecko_api_key=COINGECKO_API_KEY
)

# ===============================
# ANALYSIS LOOP
# ===============================
def run_loop():
    print("🚀 Analysis loop started")
    while True:
        try:
            agent.run()   # внутри анализ ETH + отправка сигнала
        except Exception as e:
            print(f"❌ ERROR: {e}")

        time.sleep(INTERVAL_SECONDS)

# ===============================
# START
# ===============================
thread = threading.Thread(target=run_loop, daemon=True)
thread.start()

# Background Worker должен жить бесконечно
while True:
    time.sleep(60)
