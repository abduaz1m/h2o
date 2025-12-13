import os
import time
import threading
import requests
from crypto_trading_agent import CryptoTradingAgent

# ===============================
# ENV
# ===============================
BOT_TOKEN = os.getenv("BOT_TOKEN")
CHAT_ID = os.getenv("CHAT_ID")

if not BOT_TOKEN or not CHAT_ID:
    raise RuntimeError("❌ BOT_TOKEN или CHAT_ID не заданы")

# ===============================
# INIT
# ===============================
agent = CryptoTradingAgent(
    telegram_bot_token=BOT_TOKEN,
    telegram_chat_id=CHAT_ID
)

CRYPTO = "ethereum"
CHECK_INTERVAL = 600  # 10 минут
TELEGRAM_API = f"https://api.telegram.org/bot{BOT_TOKEN}"

print("🔥 ETH BOT STARTED (FINAL VERSION)")
print("🪙 Coin: ETH")
print("⏱ Interval: 10 min")

# ===============================
# TELEGRAM HELPERS
# ===============================
def send_message(text):
    requests.post(
        f"{TELEGRAM_API}/sendMessage",
        data={"chat_id": CHAT_ID, "text": text}
    )

def get_updates(offset=None):
    params = {"timeout": 30}
    if offset:
        params["offset"] = offset
    r = requests.get(f"{TELEGRAM_API}/getUpdates", params=params)
    return r.json()

# ===============================
# COMMAND HANDLER
# ===============================
def handle_command(text):
    if text == "/check":
        send_message("🔍 Запускаю анализ ETH...")
        agent.run()
    elif text == "/status":
        send_message("✅ Бот работает\n🪙 Монета: ETH\n⏱ Интервал: 10 минут")

# ===============================
# POLLING THREAD
# ===============================
def telegram_listener():
    print("👂 Telegram listener started")
    last_update_id = None

    while True:
        try:
            data = get_updates(last_update_id)
            for update in data.get("result", []):
                last_update_id = update["update_id"] + 1
                message = update.get("message", {})
                text = message.get("text")

                if text:
                    print(f"📩 Command: {text}")
                    handle_command(text)

        except Exception as e:
            print("⚠ Telegram error:", e)

        time.sleep(2)

# ===============================
# SCHEDULED ANALYSIS
# ===============================
def scheduled_analysis():
    while True:
        try:
            print("⏱ Scheduled ETH analysis...")
            agent.run()
        except Exception as e:
            print("⚠ Analysis error:", e)

        time.sleep(CHECK_INTERVAL)

# ===============================
# START THREADS
# ===============================
threading.Thread(target=telegram_listener, daemon=True).start()
threading.Thread(target=scheduled_analysis, daemon=True).start()

# ===============================
# KEEP ALIVE
# ===============================
while True:
    time.sleep(60)
