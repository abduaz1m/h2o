import requests
from datetime import datetime

class CryptoTradingAgent:
    def __init__(self, telegram_bot_token, telegram_chat_id):
        self.bot_token = telegram_bot_token
        self.chat_id = telegram_chat_id
        self.symbol = "ETHUSDT"

    # ---------- Binance ----------
    def get_price(self):
        url = "https://api.binance.com/api/v3/ticker/24hr"
        params = {"symbol": self.symbol}
        r = requests.get(url, params=params, timeout=10)
        r.raise_for_status()
        return r.json()

    # ---------- Telegram ----------
    def send_message(self, text):
        url = f"https://api.telegram.org/bot{self.bot_token}/sendMessage"
        payload = {
            "chat_id": self.chat_id,
            "text": text
        }
        requests.post(url, data=payload, timeout=10)

    # ---------- Strategy ----------
    def analyze(self, data):
        price = float(data["lastPrice"])
        change = float(data["priceChangePercent"])

        if change > 2:
            action = "🟢 BUY"
        elif change < -2:
            action = "🔴 SELL"
        else:
            return None  # фильтр: НЕ присылаем HOLD

        return {
            "price": price,
            "change": change,
            "action": action
        }

    # ---------- Run ----------
    def run(self):
        data = self.get_price()
        signal = self.analyze(data)

        if not signal:
            print("ℹ️ Нет сигнала")
            return

        message = (
            "🤖 ETH Binance Signal\n\n"
            f"💰 Цена: ${signal['price']:.2f}\n"
            f"📊 24h: {signal['change']:+.2f}%\n\n"
            f"{signal['action']}\n\n"
            f"⏰ {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
        )

        self.send_message(message)
