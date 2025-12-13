import requests
import time
from datetime import datetime
import math

class CryptoTradingAgent:
    def __init__(self, telegram_bot_token, telegram_chat_id):
        self.bot_token = telegram_bot_token
        self.chat_id = telegram_chat_id
        self.base_url = "https://api.coingecko.com/api/v3"
        self.coin_id = "ethereum"

    # -----------------------------
    # Telegram
    # -----------------------------
    def send_message(self, text):
        url = f"https://api.telegram.org/bot{self.bot_token}/sendMessage"
        requests.post(url, data={
            "chat_id": self.chat_id,
            "text": text
        })

    # -----------------------------
    # CoinGecko SAFE endpoint
    # -----------------------------
    def get_market_data(self):
        url = f"{self.base_url}/coins/markets"
        params = {
            "vs_currency": "usd",
            "ids": self.coin_id
        }
        r = requests.get(url, params=params)
        r.raise_for_status()
        return r.json()[0]

    # -----------------------------
    # Indicators
    # -----------------------------
    def calculate_rsi(self, prices, period=14):
        gains, losses = [], []
        for i in range(1, len(prices)):
            diff = prices[i] - prices[i-1]
            if diff >= 0:
                gains.append(diff)
            else:
                losses.append(abs(diff))
        avg_gain = sum(gains[-period:]) / period
        avg_loss = sum(losses[-period:]) / period if losses else 0.0001
        rs = avg_gain / avg_loss
        return 100 - (100 / (1 + rs))

    def ema(self, prices, period):
        k = 2 / (period + 1)
        ema = prices[0]
        for p in prices[1:]:
            ema = p * k + ema * (1 - k)
        return ema

    # -----------------------------
    # Strategy
    # -----------------------------
    def analyze(self):
        data = self.get_market_data()
        price = data["current_price"]
        change_24h = data["price_change_percentage_24h"]
        volume = data["total_volume"]

        # fake short history (safe)
        prices = [price * (1 + change_24h/100 * i/24) for i in range(24)]

        rsi = self.calculate_rsi(prices)
        ema_fast = self.ema(prices[-12:], 12)
        ema_slow = self.ema(prices[-26:], 26)

        signal = None
        reason = ""

        if rsi < 30 and ema_fast > ema_slow:
            signal = "🟢 BUY"
            reason = "RSI перепродан + бычий EMA"
        elif rsi > 70 and ema_fast < ema_slow:
            signal = "🔴 SELL"
            reason = "RSI перекуплен + медвежий EMA"

        if not signal:
            return None

        tp = price * 1.03
        sl = price * 0.97

        return f"""
🤖 ETH SIGNAL (CoinGecko)

💰 Price: ${price}
📊 24h: {change_24h:+.2f}%
📈 Volume: {volume:,}

📉 RSI: {rsi:.2f}
📊 EMA12 / EMA26: {ema_fast:.2f} / {ema_slow:.2f}

👉 {signal}
🎯 TP: ${tp:.2f}
🛑 SL: ${sl:.2f}

🧠 AI Reason:
{reason}

⏰ {datetime.utcnow()}
""".strip()

    # -----------------------------
    # RUN
    # -----------------------------
    def run(self):
        signal = self.analyze()
        if signal:
            self.send_message(signal)
