import os
import time
import schedule
import requests
from crypto_trading_agent import CryptoTradingAgent

print("🤖 BOT STARTED (Background Worker)")

BOT_TOKEN = os.getenv("BOT_TOKEN")
CHAT_ID = os.getenv("CHAT_ID")

agent = CryptoTradingAgent(
    telegram_bot_token=BOT_TOKEN,
    telegram_chat_id=CHAT_ID
)

# ================================
# Анализ каждые 10 минут
# ================================
def scheduled_analysis():
    try:
        agent.run_analysis()
    except Exception as e:
        print("❌ Analysis error:", e)

schedule.every(10).minutes.do(scheduled_analysis)

# ================================
# Telegram long-polling
# ================================
def listen_commands():
    offset = None
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/getUpdates"

    while True:
        params = {"timeout": 100}
        if offset:
            params["offset"] = offset

        response = requests.get(url, params=params, timeout=120)
        data = response.json()

        for update in data.get("result", []):
            offset = update["update_id"] + 1

            message = update.get("message")
            if not message:
                continue

            text = message.get("text", "")
            agent.handle_command(text)

        time.sleep(2)

# ================================
# Старт
# ================================
if __name__ == "__main__":
    # первый запуск
    scheduled_analysis()

    import threading
    threading.Thread(target=listen_commands, daemon=True).start()

    while True:
        schedule.run_pending()
        time.sleep(1)
