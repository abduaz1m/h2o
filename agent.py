import requests
import time
import numpy as np
from llm_explainer import explain_signal

SYMBOL = "ETHUSDT"
INTERVAL = "15m"
LEVERAGE = 10

class TradingAgent:
    def __init__(self, bot_token, chat_id):
        self.bot_token = bot_token
        self.chat_id = chat_id

    def send(self, text):
        url = f"https://api.telegram.org/bot{self.bot_token}/sendMessage"
        requests.post(url, data={"chat_id": self.chat_id, "text": text})

    def get_klines(self):
        url = "https://api.binance.com/api/v3/klines"
        r = requests.get(url, params={
            "symbol": SYMBOL,
            "interval": INTERVAL,
            "limit": 200
        })
        r.raise_for_status()
        return r.json()

    def rsi(self, closes, period=14):
        deltas = np.diff(closes)
        gain = np.maximum(deltas, 0).mean()
        loss = abs(np.minimum(deltas, 0).mean())
        rs = gain / loss if loss else 0
        return 100 - (100 / (1 + rs))

    def analyze(self):
        klines = self.get_klines()
        closes = np.array([float(k[4]) for k in klines])

        rsi = self.rsi(closes)
        ema_fast = closes[-20:].mean()
        ema_slow = closes[-50:].mean()

        price = closes[-1]

        # ФИЛЬТР
        if rsi < 30 and ema_fast > ema_slow:
            side = "BUY"
        elif rsi > 70 and ema_fast < ema_slow:
            side = "SELL"
        else:
            return  # HOLD → молчим

        tp = price * (1.015 if side == "BUY" else 0.985)
        sl = price * (0.985 if side == "BUY" else 1.015)

        signal = {
            "side": side,
            "entry": round(price, 2),
            "tp": round(tp, 2),
            "sl": round(sl, 2),
            "rsi": round(rsi, 2),
            "trend": "UP" if ema_fast > ema_slow else "DOWN",
            "leverage": LEVERAGE
        }

        explanation = explain_signal(signal)

        msg = f"""
🚀 ETH SIGNAL ({INTERVAL})
Тип: {side}
Цена: {signal['entry']}
TP: {signal['tp']}
SL: {signal['sl']}
RSI: {signal['rsi']}
Плечо: {LEVERAGE}x

🧠 Объяснение:
{explanation}
"""
        self.send(msg)
