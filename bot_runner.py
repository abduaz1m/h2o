import os
import time
import threading
import requests
from crypto_trading_agent import CryptoTradingAgent

BOT_TOKEN = os.getenv("BOT_TOKEN")
CHAT_ID = os.getenv("CHAT_ID")

if not BOT_TOKEN or not CHAT_ID:
    raise RuntimeError("❌ BOT_TOKEN или CHAT_ID не заданы")

agent = CryptoTradingAgent(BOT_TOKEN, CHAT_ID)

print("🔥 ETH BOT STARTED (Background Worker)")

LAST_UPDATE_ID = None
TELEGRAM_API = f"https://api.telegram.org/bot{BOT_TOKEN}"

# --------------------------------------------------
# Проверка команд
# --------------------------------------------------
def check_commands():
    global LAST_UPDATE_ID

    params = {"timeout": 20}
    if LAST_UPDATE_ID:
        params["offset"] = LAST_UPDATE_ID + 1

    r = requests.get(f"{TELEGRAM_API}/getUpdates", params=params, timeout=30)
    updates = r.json().get("result", [])

    for upd in updates:
        LAST_UPDATE_ID = upd["update_id"]
        msg = upd.get("message", {})
        text = msg.get("text", "")
        chat_id = str(msg.get("chat", {}).get("id"))

        if chat_id != CHAT_ID:
            continue

        if text == "/check":
            agent.send_message("🔍 Анализ ETH...")
            agent.run_analysis()

        elif text == "/status":
            agent.send_message(
                "✅ Бот работает\n"
                "🪙 Монета: ETH\n"
                "📊 Индикаторы: RSI + EMA\n"
                "⏱ Авто-анализ каждые 10 минут"
            )

# --------------------------------------------------
# Авто-анализ
# --------------------------------------------------
def auto_analysis():
    while True:
        agent.run_analysis()
        time.sleep(600)  # 10 минут

# --------------------------------------------------
# START
# --------------------------------------------------
threading.Thread(target=auto_analysis, daemon=True).start()

while True:
    try:
        check_commands()
        time.sleep(2)  # ⬅️ защита от Telegram лимитов
    except Exception as e:
        print("❌ ERROR:", e)
        time.sleep(5)
