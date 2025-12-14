import requests
import time
import numpy as np
from datetime import datetime

class CryptoTradingAgent:
    def __init__(self, telegram_bot_token: str, telegram_chat_id: str):
        self.bot_token = telegram_bot_token
        self.chat_id = telegram_chat_id

        self.symbol = "ETHUSDT"
        self.interval = "15m"
        self.limit = 200

        self.binance_url = "https://api.binance.com/api/v3/klines"

    # -------------------------------
    # Telegram
    # -------------------------------
    def send_message(self, text: str):
        url = f"https://api.telegram.org/bot{self.bot_token}/sendMessage"
        payload = {
            "chat_id": self.chat_id,
            "text": text,
            "parse_mode": "HTML"
        }
        requests.post(url, data=payload, timeout=10)

    # -------------------------------
    # Binance data
    # -------------------------------
    def get_prices(self):
        params = {
            "symbol": self.symbol,
            "interval": self.interval,
            "limit": self.limit
        }
        r = requests.get(self.binance_url, params=params, timeout=10)
        r.raise_for_status()
        data = r.json()

        closes = np.array([float(candle[4]) for candle in data])
        return closes

    # -------------------------------
    # Indicators
    # -------------------------------
    def ema(self, prices, period):
        weights = np.exp(np.linspace(-1., 0., period))
        weights /= weights.sum()
        return np.convolve(prices, weights, mode="valid")

    def rsi(self, prices, period=14):
        deltas = np.diff(prices)
        gains = np.where(deltas > 0, deltas, 0)
        losses = np.where(deltas < 0, -deltas, 0)

        avg_gain = np.mean(gains[-period:])
        avg_loss = np.mean(losses[-period:])

        if avg_loss == 0:
            return 100.0

        rs = avg_gain / avg_loss
        return 100 - (100 / (1 + rs))

    # -------------------------------
    # Strategy
    # -------------------------------
    def analyze(self):
        prices = self.get_prices()

        ema_fast = self.ema(prices, 20)[-1]
        ema_slow = self.ema(prices, 50)[-1]
        rsi_val = self.rsi(prices)

        price = prices[-1]
        action = None

        if ema_fast > ema_slow and rsi_val < 70:
            action = "BUY"
        elif ema_fast < ema_slow and rsi_val > 30:
            action = "SELL"
        else:
            return None  # ❗ ФИЛЬТР — HOLD не отправляем

        # TP / SL (пример)
        if action == "BUY":
            tp = price * 1.02
            sl = price * 0.98
        else:
            tp = price * 0.98
            sl = price * 1.02

        explanation = (
            f"EMA20 {'>' if ema_fast > ema_slow else '<'} EMA50\n"
            f"RSI = {rsi_val:.2f}\n"
            f"Тренд подтверждён"
        )

        msg = (
            f"🚀 <b>ETH Binance Signal</b>\n\n"
            f"💰 Price: <b>${price:.2f}</b>\n"
            f"📈 EMA20: {ema_fast:.2f}\n"
            f"📉 EMA50: {ema_slow:.2f}\n"
            f"📊 RSI: {rsi_val:.2f}\n\n"
            f"👉 <b>{action}</b>\n"
            f"🎯 TP: {tp:.2f}\n"
            f"🛑 SL: {sl:.2f}\n\n"
            f"🤖 AI:\n{explanation}\n\n"
            f"⏰ {datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')} UTC"
        )

        return msg

    # -------------------------------
    # Main run
    # -------------------------------
    def run(self):
        signal = self.analyze()
        if signal:
            self.send_message(signal)
