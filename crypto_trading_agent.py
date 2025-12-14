import time
import requests
from datetime import datetime

class CryptoTradingAgent:
    def __init__(self, telegram_bot_token, telegram_chat_id):
        self.bot_token = telegram_bot_token
        self.chat_id = telegram_chat_id

        self.headers = {
            "User-Agent": "Mozilla/5.0 (compatible; ETHBot/1.0)"
        }

        self.url_24h = "https://api.binance.com/api/v3/ticker/24hr"

    # -------------------------------
    def get_eth_data(self):
        params = {"symbol": "ETHUSDT"}
        r = requests.get(self.url_24h, params=params, headers=self.headers, timeout=10)
        r.raise_for_status()
        return r.json()

    # -------------------------------
    def analyze(self):
        data = self.get_eth_data()

        price = float(data["lastPrice"])
        change = float(data["priceChangePercent"])
        volume = float(data["volume"])

        # ПРОСТАЯ, НО НАДЁЖНАЯ СТРАТЕГИЯ
        if change > 1.2:
            action = "🟢 BUY"
            reason = "Импульс роста за 24h"
        elif change < -1.2:
            action = "🔴 SELL"
            reason = "Сильное падение за 24h"
        else:
            return None  # HOLD → НИЧЕГО НЕ ШЛЁМ

        return {
            "price": price,
            "change": change,
            "volume": volume,
            "action": action,
            "reason": reason,
            "time": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        }

    # -------------------------------
    def send_message(self, text):
        url = f"https://api.telegram.org/bot{self.bot_token}/sendMessage"
        requests.post(url, data={
            "chat_id": self.chat_id,
            "text": text
        })

    # -------------------------------
    def run(self):
        signal = self.analyze()
        if not signal:
            print("ℹ️ HOLD — сигнал не отправлен")
            return

        msg = (
            f"🚀 ETH Binance Signal\n\n"
            f"💰 Цена: ${signal['price']}\n"
            f"📊 24h: {signal['change']}%\n"
            f"📈 Объём: {int(signal['volume'])}\n\n"
            f"{signal['action']}\n"
            f"🧠 Причина: {signal['reason']}\n\n"
            f"⏰ {signal['time']}"
        )

        self.send_message(msg)
