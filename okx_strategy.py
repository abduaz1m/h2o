import requests
import numpy as np

class OKXStrategy:
    BASE = "https://www.okx.com/api/v5/market/candles"

    def get_candles(self, symbol, limit=100):
        r = requests.get(self.BASE, params={
            "instId": symbol,
            "bar": "15m",
            "limit": limit
        }).json()

        return [float(c[4]) for c in r["data"]][::-1]

    def rsi(self, prices, period=14):
        deltas = np.diff(prices)
        gains = deltas.clip(min=0)
        losses = -deltas.clip(max=0)

        avg_gain = gains[-period:].mean()
        avg_loss = losses[-period:].mean()

        if avg_loss == 0:
            return 100

        rs = avg_gain / avg_loss
        return 100 - (100 / (1 + rs))

    def ema(self, prices, period):
        k = 2 / (period + 1)
        ema = prices[0]
        for p in prices[1:]:
            ema = p * k + ema * (1 - k)
        return ema

    def analyze(self, symbol):
        prices = self.get_candles(symbol)

        rsi = self.rsi(prices)
        ema_fast = self.ema(prices, 9)
        ema_slow = self.ema(prices, 21)
        price = prices[-1]

        action = "HOLD"
        if rsi < 30 and ema_fast > ema_slow:
            action = "BUY"
        elif rsi > 70 and ema_fast < ema_slow:
            action = "SELL"

        tp = round(price * (1.02 if action == "BUY" else 0.98), 4)
        sl = round(price * (0.98 if action == "BUY" else 1.02), 4)

        return {
            "symbol": symbol,
            "price": price,
            "rsi": round(rsi, 2),
            "ema_fast": round(ema_fast, 2),
            "ema_slow": round(ema_slow, 2),
            "action": action,
            "tp": tp,
            "sl": sl
        }
