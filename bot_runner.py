import os
import time
import threading
import schedule
import requests
from crypto_trading_agent import CryptoTradingAgent

BOT_TOKEN = os.getenv("BOT_TOKEN")
CHAT_ID = os.getenv("CHAT_ID")

agent = CryptoTradingAgent(BOT_TOKEN, CHAT_ID)

LAST_UPDATE_ID = None

print("🔥 ETH BOT STARTED (FINAL VERSION)")


# --------------------------------------------------
# Telegram polling
# --------------------------------------------------
def poll_commands():
    global LAST_UPDATE_ID

    url = f"https://api.telegram.org/bot{BOT_TOKEN}/getUpdates"

    while True:
        params = {"timeout": 20}
        if LAST_UPDATE_ID:
            params["offset"] = LAST_UPDATE_ID + 1

        r = requests.get(url, params=params, timeout=30).json()

        for upd in r.get("result", []):
            LAST_UPDATE_ID = upd["update_id"]

            msg = upd.get("message", {})
            text = msg.get("text", "")
            chat_id = str(msg.get("chat", {}).get("id"))

            if chat_id != CHAT_ID:
                continue

            if text == "/check":
                agent.send("🔍 Ручной анализ ETH...")
                agent.run()

            elif text == "/status":
                agent.send(
                    "✅ ETH бот работает\n"
                    "📊 Стратегия: EMA + RSI\n"
                    "🎯 Только BUY / SELL\n"
                    "⏱ Авто-анализ каждые 15 минут"
                )

        time.sleep(2)  # ← ВОТ ЗДЕСЬ time.sleep(2)


# --------------------------------------------------
# Плановый анализ (429-safe)
# --------------------------------------------------
def scheduled():
    agent.run()

schedule.every(15).minutes.do(scheduled)

# первый запуск
scheduled()

threading.Thread(target=poll_commands, daemon=True).start()

while True:
    schedule.run_pending()
    time.sleep(5)
