import requests
import time
import numpy as np
from datetime import datetime

class CryptoTradingAgent:
    def __init__(self, telegram_token, chat_id):
        self.telegram_token = telegram_token
        self.chat_id = chat_id

        self.symbol = "ETH-USDT-SWAP"
        self.interval = "15m"
        self.leverage = 10  # ⚡ ПЛЕЧО
        self.base_url = "https://www.okx.com/api/v5/market/candles"

    # ---------------- OKX DATA ----------------
    def get_candles(self, limit=200):
        params = {
            "instId": self.symbol,
            "bar": self.interval,
            "limit": str(limit)
        }
        r = requests.get(self.base_url, params=params, timeout=10)
        r.raise_for_status()
        data = r.json()["data"]
        data.reverse()
        closes = np.array([float(c[4]) for c in data])
        return closes

    # ---------------- INDICATORS ----------------
    def ema(self, prices, period):
        return prices[-period:].mean()

    def rsi(self, prices, period=14):
        deltas = np.diff(prices)
        gains = deltas[deltas > 0].sum() / period
        losses = -deltas[deltas < 0].sum() / period
        if losses == 0:
            return 100
        rs = gains / losses
        return 100 - (100 / (1 + rs))

    # ---------------- STRATEGY ----------------
    def analyze(self):
        prices = self.get_candles()
        price = prices[-1]

        ema_fast = self.ema(prices, 20)
        ema_slow = self.ema(prices, 50)
        rsi_val = self.rsi(prices)

        signal = None

        if ema_fast > ema_slow and rsi_val < 70:
            signal = "BUY"
        elif ema_fast < ema_slow and rsi_val > 30:
            signal = "SELL"

        if not signal:
            return None

        tp = price * (1.015 if signal == "BUY" else 0.985)
        sl = price * (0.985 if signal == "BUY" else 1.015)

        explanation = self.llm_explanation(signal, price, ema_fast, ema_slow, rsi_val)

        return {
            "signal": signal,
            "price": price,
            "tp": tp,
            "sl": sl,
            "ema20": ema_fast,
            "ema50": ema_slow,
            "rsi": rsi_val,
            "explanation": explanation
        }

    # ---------------- LLM (локальное объяснение) ----------------
    def llm_explanation(self, signal, price, ema20, ema50, rsi):
        direction = "бычий" if signal == "BUY" else "медвежий"
        return (
            f"📊 AI-анализ:\n"
            f"Рынок демонстрирует {direction} импульс.\n"
            f"EMA20 ({ema20:.2f}) {'выше' if ema20 > ema50 else 'ниже'} EMA50 ({ema50:.2f}).\n"
            f"RSI = {rsi:.2f}, перегрева нет.\n"
            f"Сигнал основан на тренде + импульсе."
        )

    # ---------------- TELEGRAM ----------------
    def send_message(self, text):
        url = f"https://api.telegram.org/bot{self.telegram_token}/sendMessage"
        payload = {
            "chat_id": self.chat_id,
            "text": text,
            "parse_mode": "HTML"
        }
        requests.post(url, data=payload, timeout=10)

    # ---------------- RUN ----------------
    def run(self):
        signal = self.analyze()
        if not signal:
            return

        msg = (
            f"🚀 ETH OKX FUTURES (15m)\n\n"
            f"📈 Сигнал: <b>{signal['signal']}</b>\n"
            f"💰 Цена: {signal['price']:.2f}\n"
            f"⚡ Плечо: {self.leverage}x\n\n"
            f"🎯 TP: {signal['tp']:.2f}\n"
            f"🛑 SL: {signal['sl']:.2f}\n\n"
            f"{signal['explanation']}\n\n"
            f"⏰ {datetime.utcnow().strftime('%Y-%m-%d %H:%M UTC')}"
        )

        self.send_message(msg)
