import os
import time
import threading
import requests

from crypto_trading_agent import CryptoTradingAgent

# ================== ENV ==================
BOT_TOKEN = os.getenv("BOT_TOKEN")
CHAT_ID = os.getenv("CHAT_ID")

SYMBOL = "ethereum"
INTERVAL = 600  # 10 минут

if not BOT_TOKEN or not CHAT_ID:
    raise RuntimeError("❌ BOT_TOKEN или CHAT_ID не заданы в Render ENV")

print("🔥 ETH BOT STARTED (FINAL VERSION)")
print("📌 SYMBOL:", SYMBOL)
print("⏱ INTERVAL:", INTERVAL, "sec")

# ================== AGENT ==================
agent = CryptoTradingAgent(
    telegram_bot_token=BOT_TOKEN,
    telegram_chat_id=CHAT_ID
)

# ================== TELEGRAM API ==================
TELEGRAM_API = f"https://api.telegram.org/bot{BOT_TOKEN}"

last_update_id = None


def send(text: str):
    requests.post(
        f"{TELEGRAM_API}/sendMessage",
        data={"chat_id": CHAT_ID, "text": text}
    )


# ================== COMMAND HANDLER ==================
def command_listener():
    global last_update_id
    print("👂 Командный слушатель запущен")

    while True:
        try:
            params = {"timeout": 30}
            if last_update_id:
                params["offset"] = last_update_id + 1

            r = requests.get(f"{TELEGRAM_API}/getUpdates", params=params, timeout=35)
            data = r.json()

            if not data.get("ok"):
                continue

            for update in data["result"]:
                last_update_id = update["update_id"]

                message = update.get("message", {})
                text = message.get("text", "")

                if not text:
                    continue

                if text == "/status":
                    send("✅ ETH Bot работает и ждёт сигналов")

                elif text == "/check":
                    send("🔍 Запускаю анализ ETH...")
                    agent.run()  # принудительный анализ

        except Exception as e:
            print("❌ Command listener error:", e)
            time.sleep(5)


# ================== SCHEDULED ANALYSIS ==================
def scheduled_runner():
    while True:
        try:
            agent.run()
        except Exception as e:
            print("❌ Scheduled error:", e)

        time.sleep(INTERVAL)


# ================== START ==================
send("🚀 ETH Bot запущен и работает в фоне")

threading.Thread(target=command_listener, daemon=True).start()
threading.Thread(target=scheduled_runner, daemon=True).start()

# держим процесс живым
while True:
    time.sleep(3600)
