import requests
import pandas as pd
import numpy as np
from datetime import datetime
import openai
import os

OKX_CANDLES_URL = "https://www.okx.com/api/v5/market/candles"

class CryptoTradingAgent:
    def __init__(self, bot_token, chat_id):
        self.bot_token = bot_token
        self.chat_id = chat_id

        self.symbol = "ETH-USDT-SWAP"
        self.timeframe = "15m"

        # LLM (опционально)
        self.openai_key = os.getenv("OPENAI_API_KEY")
        if self.openai_key:
            openai.api_key = self.openai_key

    # --------------------------------------------------
    # Получение свечей OKX
    # --------------------------------------------------
    def fetch_candles(self, limit=200):
        params = {
            "instId": self.symbol,
            "bar": self.timeframe,
            "limit": limit
        }
        r = requests.get(OKX_CANDLES_URL, params=params, timeout=10)
        r.raise_for_status()

        data = r.json()["data"]
        df = pd.DataFrame(data, columns=[
            "ts", "open", "high", "low", "close",
            "volume", "volCcy", "volCcyQuote", "confirm"
        ])
        df["close"] = df["close"].astype(float)
        return df[::-1]

    # --------------------------------------------------
    # Индикаторы
    # --------------------------------------------------
    def add_indicators(self, df):
        df["ema20"] = df["close"].ewm(span=20).mean()
        df["ema50"] = df["close"].ewm(span=50).mean()

        delta = df["close"].diff()
        gain = np.where(delta > 0, delta, 0)
        loss = np.where(delta < 0, -delta, 0)

        avg_gain = pd.Series(gain).rolling(14).mean()
        avg_loss = pd.Series(loss).rolling(14).mean()
        rs = avg_gain / avg_loss
        df["rsi"] = 100 - (100 / (1 + rs))

        return df

    # --------------------------------------------------
    # Стратегия
    # --------------------------------------------------
    def generate_signal(self, df):
        last = df.iloc[-1]

        price = last["close"]
        rsi = last["rsi"]
        ema20 = last["ema20"]
        ema50 = last["ema50"]

        # BUY
        if ema20 > ema50 and rsi < 65:
            side = "BUY"
        # SELL
        elif ema20 < ema50 and rsi > 35:
            side = "SELL"
        else:
            return None

        # Динамическое плечо
        if rsi < 30 or rsi > 70:
            leverage = 3
        elif rsi < 40 or rsi > 60:
            leverage = 5
        else:
            leverage = 8

        # TP / SL
        if side == "BUY":
            tp = price * 1.01
            sl = price * 0.995
        else:
            tp = price * 0.99
            sl = price * 1.005

        return {
            "side": side,
            "price": price,
            "rsi": rsi,
            "ema20": ema20,
            "ema50": ema50,
            "tp": tp,
            "sl": sl,
            "leverage": leverage
        }

    # --------------------------------------------------
    # LLM объяснение
    # --------------------------------------------------
    def ai_explanation(self, signal):
        if not self.openai_key:
            return "LLM не подключён."

        prompt = (
            f"Объясни торговый сигнал для ETH фьючерсов:\n"
            f"Сторона: {signal['side']}\n"
            f"RSI: {signal['rsi']:.2f}\n"
            f"EMA20: {signal['ema20']:.2f}\n"
            f"EMA50: {signal['ema50']:.2f}\n"
            f"Плечо: {signal['leverage']}x\n"
            f"TP: {signal['tp']:.2f}\n"
            f"SL: {signal['sl']:.2f}\n"
            f"Кратко и по делу."
        )

        try:
            resp = openai.ChatCompletion.create(
                model="gpt-4o-mini",
                messages=[{"role": "user", "content": prompt}],
                max_tokens=120
            )
            return resp.choices[0].message.content.strip()
        except Exception:
            return "Ошибка LLM."

    # --------------------------------------------------
    # Telegram
    # --------------------------------------------------
    def send_telegram(self, text):
        url = f"https://api.telegram.org/bot{self.bot_token}/sendMessage"
        requests.post(url, data={
            "chat_id": self.chat_id,
            "text": text
        })

    # --------------------------------------------------
    # Запуск
    # --------------------------------------------------
    def run(self):
        df = self.fetch_candles()
        df = self.add_indicators(df)

        signal = self.generate_signal(df)
        if not signal:
            return  # НИЧЕГО НЕ ОТПРАВЛЯЕМ

        explanation = self.ai_explanation(signal)

        msg = (
            f"🚨 ETH FUTURES SIGNAL (OKX · 15m)\n\n"
            f"📌 Side: {signal['side']}\n"
            f"💵 Price: {signal['price']:.2f}\n"
            f"📊 RSI: {signal['rsi']:.2f}\n"
            f"⚖ EMA20 / EMA50: {signal['ema20']:.2f} / {signal['ema50']:.2f}\n\n"
            f"🎯 TP: {signal['tp']:.2f}\n"
            f"🛑 SL: {signal['sl']:.2f}\n"
            f"⚡ Leverage: {signal['leverage']}x\n\n"
            f"🧠 AI:\n{explanation}\n\n"
            f"⏰ {datetime.utcnow().strftime('%Y-%m-%d %H:%M UTC')}"
        )

        self.send_telegram(msg)
