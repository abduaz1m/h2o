import requests
import time
from datetime import datetime

OKX_CANDLES = "https://www.okx.com/api/v5/market/candles"


class TradingAgent:
    def __init__(self):
        self.symbol = "ETH-USDT-SWAP"
        self.timeframe = "15m"
        self.limit = 200

    def get_candles(self):
        params = {
            "instId": self.symbol,
            "bar": self.timeframe,
            "limit": self.limit
        }
        r = requests.get(OKX_CANDLES, params=params, timeout=10)
        r.raise_for_status()
        return r.json()["data"]

    def ema(self, prices, period):
        k = 2 / (period + 1)
        ema = prices[0]
        for p in prices[1:]:
            ema = p * k + ema * (1 - k)
        return ema

    def rsi(self, prices, period=14):
        gains, losses = [], []
        for i in range(1, period + 1):
            diff = prices[i] - prices[i - 1]
            gains.append(max(diff, 0))
            losses.append(max(-diff, 0))
        avg_gain = sum(gains) / period
        avg_loss = sum(losses) / period
        if avg_loss == 0:
            return 100
        rs = avg_gain / avg_loss
        return 100 - (100 / (1 + rs))

    def analyze(self):
        candles = self.get_candles()
        closes = [float(c[4]) for c in reversed(candles)]

        price = closes[-1]
        ema50 = self.ema(closes[-50:], 50)
        ema200 = self.ema(closes[-200:], 200)
        rsi = self.rsi(closes)

        signal = None
        if ema50 > ema200 and rsi < 70:
            signal = "BUY"
        elif ema50 < ema200 and rsi > 30:
            signal = "SELL"

        if not signal:
            return None

        leverage = 10
        if signal == "BUY":
            tp = price * 1.01
            sl = price * 0.995
        else:
            tp = price * 0.99
            sl = price * 1.005

        return {
            "signal": signal,
            "price": price,
            "ema50": ema50,
            "ema200": ema200,
            "rsi": rsi,
            "tp": tp,
            "sl": sl,
            "leverage": leverage,
            "time": datetime.utcnow().strftime("%Y-%m-%d %H:%M UTC")
        }
