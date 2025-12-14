import requests
import time
import math

BINANCE_KLINES = "https://api.binance.com/api/v3/klines"


class CryptoTradingAgent:
    def __init__(self, bot_token: str, chat_id: str):
        self.bot_token = bot_token
        self.chat_id = chat_id
        self.symbol = "ETHUSDT"
        self.interval = "15m"
        self.limit = 200

    # ---------- TELEGRAM ----------
    def send_message(self, text: str):
        url = f"https://api.telegram.org/bot{self.bot_token}/sendMessage"
        requests.post(url, json={
            "chat_id": self.chat_id,
            "text": text
        })

    # ---------- BINANCE ----------
    def get_prices(self):
        r = requests.get(BINANCE_KLINES, params={
            "symbol": self.symbol,
            "interval": self.interval,
            "limit": self.limit
        })
        r.raise_for_status()
        candles = r.json()
        return [float(c[4]) for c in candles]  # close prices

    # ---------- INDICATORS ----------
    def ema(self, prices, period):
        k = 2 / (period + 1)
        ema = prices[0]
        for p in prices[1:]:
            ema = p * k + ema * (1 - k)
        return ema

    def rsi(self, prices, period=14):
        gains, losses = [], []
        for i in range(1, period + 1):
            delta = prices[-i] - prices[-i - 1]
            if delta >= 0:
                gains.append(delta)
            else:
                losses.append(abs(delta))

        avg_gain = sum(gains) / period
        avg_loss = sum(losses) / period or 0.0001
        rs = avg_gain / avg_loss
        return 100 - (100 / (1 + rs))

    # ---------- STRATEGY ----------
    def analyze(self):
        prices = self.get_prices()
        price = prices[-1]

        ema50 = self.ema(prices[-60:], 50)
        ema200 = self.ema(prices[-210:], 200)
        rsi = self.rsi(prices)

        # BUY
        if ema50 > ema200 and rsi < 35:
            tp = price * 1.03
            sl = price * 0.97
            return self.format_signal("BUY", price, rsi, ema50, ema200, tp, sl)

        # SELL
        if ema50 < ema200 and rsi > 65:
            tp = price * 0.97
            sl = price * 1.03
            return self.format_signal("SELL", price, rsi, ema50, ema200, tp, sl)

        return None  # HOLD → не отправляем

    def format_signal(self, side, price, rsi, ema50, ema200, tp, sl):
        emoji = "🟢" if side == "BUY" else "🔴"
        explanation = (
            f"EMA50 {'>' if ema50 > ema200 else '<'} EMA200\n"
            f"RSI = {rsi:.1f}\n"
            f"Тренд подтверждён"
        )

        return (
            f"{emoji} *ETH {side}*\n\n"
            f"💰 Цена: {price:.2f}\n"
            f"📈 RSI: {rsi:.1f}\n"
            f"📊 EMA50 / EMA200\n\n"
            f"🎯 TP: {tp:.2f}\n"
            f"🛑 SL: {sl:.2f}\n\n"
            f"🤖 AI-объяснение:\n{explanation}"
        )

    # ---------- RUN ----------
    def run_once(self):
        signal = self.analyze()
        if signal:
            self.send_message(signal)
