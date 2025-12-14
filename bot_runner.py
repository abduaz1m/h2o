import os
import time
import requests
import threading
from crypto_trading_agent import CryptoTradingAgent

# ==============================
# ENV
# ==============================
BOT_TOKEN = os.getenv("BOT_TOKEN")
CHAT_ID = os.getenv("CHAT_ID")

if not BOT_TOKEN or not CHAT_ID:
    raise RuntimeError("❌ BOT_TOKEN или CHAT_ID не заданы в Render ENV")

# ==============================
# CONFIG
# ==============================
ANALYSIS_INTERVAL = 10 * 60  # 10 минут
SYMBOL = "ethereum"          # ❗ ТОЛЬКО ETH

print("🔥 ETH BOT STARTED (FINAL VERSION)")
print("📌 SYMBOL:", SYMBOL)

# ==============================
# INIT AGENT
# ==============================
agent = CryptoTradingAgent(
    telegram_bot_token=BOT_TOKEN,
    telegram_chat_id=CHAT_ID
)

# ==============================
# TELEGRAM API
# ==============================
BASE_URL = f"https://api.telegram.org/bot{BOT_TOKEN}"

def send_message(text: str):
    requests.post(
        f"{BASE_URL}/sendMessage",
        data={"chat_id": CHAT_ID, "text": text}
    )

# ==============================
# COMMAND HANDLER
# ==============================
def handle_command(text: str):
    text = text.strip().lower()

    if text == "/check":
        send_message("🔍 Запускаю анализ ETH...")
        agent.run_once()
        return

    if text == "/status":
        send_message(
            "🟢 ETH Bot активен\n"
            "⏱ Интервал: 10 минут\n"
            "📊 Индикаторы: RSI / EMA\n"
            "🎯 Только BUY / SELL"
        )
        return

# ==============================
# TELEGRAM LONG POLLING
# ==============================
def telegram_listener():
    print("👂 Telegram listener started")
    offset = None

    while True:
        try:
            resp = requests.get(
                f"{BASE_URL}/getUpdates",
                params={"timeout": 60, "offset": offset},
                timeout=90
            ).json()

            for update in resp.get("result", []):
                offset = update["update_id"] + 1

                message = update.get("message")
                if not message:
                    continue

                if str(message.get("chat", {}).get("id")) != str(CHAT_ID):
                    continue

                text = message.get("text", "")
                if text.startswith("/"):
                    handle_command(text)

        except Exception as e:
            print("❌ Telegram error:", e)
            time.sleep(5)

# ==============================
# SCHEDULED ANALYSIS
# ==============================
def scheduled_analysis():
    while True:
        try:
            print("⏱ Scheduled ETH analysis...")
            agent.run_once()
        except Exception as e:
            print("❌ Analysis error:", e)

        time.sleep(ANALYSIS_INTERVAL)

# ==============================
# START THREADS
# ==============================
threading.Thread(target=telegram_listener, daemon=True).start()
threading.Thread(target=scheduled_analysis, daemon=True).start()

# ==============================
# KEEP ALIVE
# ==============================
while True:
    time.sleep(60)
