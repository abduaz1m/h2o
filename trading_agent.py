import time
import requests
import numpy as np
from datetime import datetime

OKX_URL = "https://www.okx.com/api/v5/market/candles"

class TradingAgent:
    def __init__(self, bot_token, chat_id):
        self.bot_token = bot_token
        self.chat_id = chat_id

        self.symbols = {
            "ETH": "ETH-USDT",
            "SOL": "SOL-USDT",
            "AVAX": "AVAX-USDT",
            "MATIC": "MATIC-USDT",
            "BNB": "BNB-USDT"
        }

        self.interval = "15m"
        self.leverage = 10

    # -----------------------------
    def send_message(self, text):
        url = f"https://api.telegram.org/bot{self.bot_token}/sendMessage"
        requests.post(url, data={"chat_id": self.chat_id, "text": text})

    # -----------------------------
    def get_candles(self, symbol):
        params = {
            "instId": symbol,
            "bar": self.interval,
            "limit": 200
        }
        r = requests.get(OKX_URL, params=params)
        r.raise_for_status()
        data = r.json()["data"]
        closes = [float(c[4]) for c in data]
        return closes[::-1]

    # -----------------------------
    def rsi(self, prices, period=14):
        deltas = np.diff(prices)
        gain = np.mean([d for d in deltas[-period:] if d > 0])
        loss = abs(np.mean([d for d in deltas[-period:] if d < 0]))
        if loss == 0:
            return 100
        rs = gain / loss
        return 100 - (100 / (1 + rs))

    # -----------------------------
    def ema(self, prices, period):
        weights = np.exp(np.linspace(-1., 0., period))
        weights /= weights.sum()
        return np.convolve(prices, weights, mode='valid')[-1]

    # -----------------------------
    def analyze(self, name, symbol):
        prices = self.get_candles(symbol)
        price = prices[-1]

        rsi = self.rsi(prices)
        ema_fast = self.ema(prices, 20)
        ema_slow = self.ema(prices, 50)

        signal = None

        if rsi < 30 and ema_fast > ema_slow:
            signal = "BUY"
        elif rsi > 70 and ema_fast < ema_slow:
            signal = "SELL"

        if not signal:
            return None

        tp = price * (1.015 if signal == "BUY" else 0.985)
        sl = price * (0.99 if signal == "BUY" else 1.01)

        return {
            "coin": name,
            "signal": signal,
            "price": price,
            "tp": tp,
            "sl": sl,
            "rsi": rsi
        }

    # -----------------------------
    def run(self):
        for name, symbol in self.symbols.items():
            try:
                result = self.analyze(name, symbol)
                if not result:
                    continue

                msg = (
                    f"🚀 {result['signal']} {result['coin']} (OKX 15m)\n\n"
                    f"💰 Цена: {result['price']:.2f}\n"
                    f"📊 RSI: {result['rsi']:.1f}\n"
                    f"⚙️ Плечо: {self.leverage}x\n\n"
                    f"🎯 TP: {result['tp']:.2f}\n"
                    f"🛑 SL: {result['sl']:.2f}\n\n"
                    f"🕒 {datetime.utcnow().strftime('%Y-%m-%d %H:%M UTC')}"
                )

                self.send_message(msg)
                time.sleep(2)

            except Exception as e:
                self.send_message(f"⚠️ Ошибка {name}: {e}")
