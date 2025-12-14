import requests
import time
import numpy as np
from datetime import datetime

BINANCE_URL = "https://api.binance.com/api/v3/klines"
HEADERS = {
    "User-Agent": "Mozilla/5.0",
    "Accept": "application/json"
}

class CryptoTradingAgent:
    def __init__(self, bot_token, chat_id):
        self.bot_token = bot_token
        self.chat_id = chat_id
        self.symbol = "ETHUSDT"
        self.interval = "15m"

    # -----------------------------
    def get_klines(self):
        params = {
            "symbol": self.symbol,
            "interval": self.interval,
            "limit": 200
        }
        r = requests.get(BINANCE_URL, params=params, headers=HEADERS)
        r.raise_for_status()
        return r.json()

    # -----------------------------
    def ema(self, prices, period):
        weights = np.exp(np.linspace(-1., 0., period))
        weights /= weights.sum()
        return np.convolve(prices, weights, mode='valid')[-1]

    def rsi(self, prices, period=14):
        deltas = np.diff(prices)
        gains = deltas.clip(min=0)
        losses = -deltas.clip(max=0)
        avg_gain = np.mean(gains[-period:])
        avg_loss = np.mean(losses[-period:])
        if avg_loss == 0:
            return 100
        rs = avg_gain / avg_loss
        return 100 - (100 / (1 + rs))

    # -----------------------------
    def analyze(self):
        klines = self.get_klines()
        closes = np.array([float(k[4]) for k in klines])

        price = closes[-1]
        rsi = self.rsi(closes)
        ema50 = self.ema(closes, 50)
        ema200 = self.ema(closes, 200)

        signal = None

        if rsi < 30 and ema50 > ema200:
            signal = "🟢 BUY"
            tp = price * 1.03
            sl = price * 0.98
        elif rsi > 70 and ema50 < ema200:
            signal = "🔴 SELL"
            tp = price * 0.97
            sl = price * 1.02
        else:
            return None

        message = f"""
🚀 ETH BINANCE SIGNAL

💰 Price: {price:.2f}
📊 RSI: {rsi:.2f}
📈 EMA50 / EMA200: {ema50:.2f} / {ema200:.2f}

📌 Signal: {signal}
🎯 TP: {tp:.2f}
🛑 SL: {sl:.2f}

🤖 AI: сигнал основан на RSI + тренде EMA
⏰ {datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')}
"""
        return message.strip()

    # -----------------------------
    def send_message(self, text):
        url = f"https://api.telegram.org/bot{self.bot_token}/sendMessage"
        data = {"chat_id": self.chat_id, "text": text}
        requests.post(url, data=data)

    # -----------------------------
    def run(self):
        signal = self.analyze()
        if signal:
            self.send_message(signal)
