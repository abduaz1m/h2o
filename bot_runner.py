import os
import time
import threading
import schedule
import requests

from crypto_trading_agent import CryptoTradingAgent


BOT_TOKEN = os.getenv("BOT_TOKEN")
CHAT_ID = os.getenv("CHAT_ID")

# Монеты в формате: BTC,ETH,SOL
SYMBOLS = os.getenv("CRYPTOS", "BTC,ETH,SOL").split(",")

agent = CryptoTradingAgent(BOT_TOKEN, CHAT_ID)


# --------------------------------------------------
# Проверка команд (/check) через getUpdates
# --------------------------------------------------
def listen_commands():
    print("👂 Listening Telegram commands...")
    last_update_id = None

    while True:
        try:
            url = f"https://api.telegram.org/bot{BOT_TOKEN}/getUpdates"
            params = {"offset": last_update_id, "timeout": 10}
            r = requests.get(url, params=params).json()

            for update in r.get("result", []):
                last_update_id = update["update_id"] + 1
                msg = update.get("message", {})
                text = msg.get("text", "")
                chat_id = str(msg.get("chat", {}).get("id"))

                if chat_id == CHAT_ID:
                    agent.handle_command(text, SYMBOLS)

        except Exception as e:
            print("❌ Telegram polling error:", e)

        time.sleep(2)


# --------------------------------------------------
# Планировщик
# --------------------------------------------------
def scheduled_analysis():
    print("⏱ Scheduled analysis")
    agent.run_analysis(SYMBOLS)


def scheduler_loop():
    schedule.every(10).minutes.do(scheduled_analysis)
    scheduled_analysis()

    while True:
        schedule.run_pending()
        time.sleep(1)


# --------------------------------------------------
# START
# --------------------------------------------------
if __name__ == "__main__":
    print("🔥 Bot started (CoinGecko version)")
    print("SYMBOLS:", SYMBOLS)

    threading.Thread(target=listen_commands, daemon=True).start()
    threading.Thread(target=scheduler_loop, daemon=True).start()

    while True:
        time.sleep(60)
