import os
import time
import schedule
import requests
from crypto_trading_agent import CryptoTradingAgent

print("🔥 BOT STARTED (Background Worker)")

BOT_TOKEN = os.getenv("BOT_TOKEN")
CHAT_ID = os.getenv("CHAT_ID")
CRYPTOS = os.getenv("CRYPTOS", "bitcoin,ethereum,solana").split(",")

if not BOT_TOKEN or not CHAT_ID:
    raise RuntimeError("❌ BOT_TOKEN или CHAT_ID не заданы")

print("✅ ENV OK")
print("🪙 Монеты:", CRYPTOS)

agent = CryptoTradingAgent(BOT_TOKEN, CHAT_ID)

# ---------- Telegram polling ----------
LAST_UPDATE_ID = 0

def check_commands():
    global LAST_UPDATE_ID

    url = f"https://api.telegram.org/bot{BOT_TOKEN}/getUpdates"
    params = {
        "timeout": 10,
        "offset": LAST_UPDATE_ID + 1
    }

    r = requests.get(url, params=params, timeout=15)
    data = r.json()

    for upd in data.get("result", []):
        LAST_UPDATE_ID = upd["update_id"]

        message = upd.get("message", {})
        text = message.get("text", "")
        chat_id = str(message.get("chat", {}).get("id"))

        # ❗️игнорируем чужие чаты
        if chat_id != CHAT_ID:
            continue

        print(f"📩 COMMAND RECEIVED: {text}")

        if text == "/check":
            agent.send_message("🔍 Выполняю быстрый анализ (CoinGecko)...")
            agent.run_analysis(CRYPTOS)

        elif text == "/status":
            agent.send_message(
                "✅ Бот работает\n"
                "⏱ Авто-анализ каждые 10 минут\n"
                f"🪙 Монеты: {', '.join(CRYPTOS)}"
            )

# ---------- Планировщик ----------
def scheduled_analysis():
    print("⏰ Плановый анализ")
    agent.run_analysis(CRYPTOS)

schedule.every(10).minutes.do(scheduled_analysis)

# Первый запуск
scheduled_analysis()

# ---------- MAIN LOOP ----------
while True:
    try:
        check_commands()
        schedule.run_pending()
        time.sleep(3)
    except Exception as e:
        print("❌ ERROR:", e)
        time.sleep(5)
