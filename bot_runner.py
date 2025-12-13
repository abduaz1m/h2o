import os
import time
import requests
from crypto_trading_agent import CryptoTradingAgent

BOT_TOKEN = os.getenv("BOT_TOKEN")
CHAT_ID = os.getenv("CHAT_ID")
CRYPTOS = os.getenv("CRYPTOS", "bitcoin,ethereum,solana").split(",")

TELEGRAM_API = f"https://api.telegram.org/bot{BOT_TOKEN}"

print("🤖 BOT STARTED (Background Worker)")
print("CRYPTOS:", CRYPTOS)

agent = CryptoTradingAgent(
    telegram_bot_token=BOT_TOKEN,
    telegram_chat_id=CHAT_ID
)

last_update_id = None


# -------------------------------
# Получение сообщений Telegram
# -------------------------------
def get_updates():
    global last_update_id
    params = {"timeout": 30}
    if last_update_id:
        params["offset"] = last_update_id + 1

    r = requests.get(f"{TELEGRAM_API}/getUpdates", params=params)
    data = r.json()

    if not data.get("ok"):
        return []

    return data["result"]


# -------------------------------
# Обработка команд
# -------------------------------
def handle_message(text):
    if text == "/check":
        agent.send_telegram_message("🔍 Запускаю быстрый анализ (CoinGecko)...")
        agent.run_analysis(CRYPTOS)

    elif text == "/status":
        agent.send_telegram_message(
            "✅ Бот работает\n"
            f"📊 Монеты: {', '.join(CRYPTOS)}\n"
            "⏱ Автоанализ каждые 10 минут"
        )


# -------------------------------
# Основной цикл
# -------------------------------
def main_loop():
    global last_update_id

    while True:
        updates = get_updates()

        for update in updates:
            last_update_id = update["update_id"]

            message = update.get("message")
            if not message:
                continue

            text = message.get("text", "")
            chat_id = str(message["chat"]["id"])

            if chat_id != CHAT_ID:
                continue

            print("📩 COMMAND:", text)
            handle_message(text)

        time.sleep(1)


# -------------------------------
# Плановый анализ каждые 10 минут
# -------------------------------
def scheduled_analysis():
    while True:
        print("⏱ Auto analysis started")
        agent.run_analysis(CRYPTOS)
        time.sleep(600)


# -------------------------------
# Запуск
# -------------------------------
import threading

threading.Thread(target=scheduled_analysis, daemon=True).start()
main_loop()
