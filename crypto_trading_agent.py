from llm_explainer import explain_signal
import requests
import time
from datetime import datetime

class CryptoTradingAgent:
    def __init__(self, telegram_bot_token: str, telegram_chat_id: str):
        self.bot_token = telegram_bot_token
        self.chat_id = telegram_chat_id

        # OKX public endpoint (НЕ требует API key)
        self.okx_url = "https://www.okx.com/api/v5/market/candles"

        self.symbol = "ETH-USDT"
        self.interval = "15m"

    # -----------------------------------------
    # Получение свечей
    # -----------------------------------------
    def get_candles(self, limit=100):
        params = {
            "instId": self.symbol,
            "bar": self.interval,
            "limit": limit
        }

        r = requests.get(self.okx_url, params=params, timeout=10)
        r.raise_for_status()
        data = r.json()

        if data.get("code") != "0":
            raise Exception(f"OKX error: {data}")

        return data["data"]

    # -----------------------------------------
    # EMA
    # -----------------------------------------
    def ema(self, prices, period):
        k = 2 / (period + 1)
        ema_val = prices[0]
        for p in prices[1:]:
            ema_val = p * k + ema_val * (1 - k)
        return ema_val

    # -----------------------------------------
    # RSI
    # -----------------------------------------
    def rsi(self, prices, period=14):
        gains, losses = [], []

        for i in range(1, period + 1):
            diff = prices[i] - prices[i - 1]
            if diff >= 0:
                gains.append(diff)
                losses.append(0)
            else:
                gains.append(0)
                losses.append(abs(diff))

        avg_gain = sum(gains) / period
        avg_loss = sum(losses) / period

        if avg_loss == 0:
            return 100

        rs = avg_gain / avg_loss
        return 100 - (100 / (1 + rs))

    # -----------------------------------------
    # Анализ
    # -----------------------------------------
    def analyze(self):
        candles = self.get_candles()
        closes = [float(c[4]) for c in candles][::-1]

        price = closes[-1]
        ema50 = self.ema(closes[-50:], 50)
        ema200 = self.ema(closes[-200:], 200)
        rsi14 = self.rsi(closes[-15:])

        signal = None

        if ema50 > ema200 and rsi14 < 65:
            signal = "BUY"
        elif ema50 < ema200 and rsi14 > 35:
            signal = "SELL"

        if not signal:
            return None

        tp = price * (1.02 if signal == "BUY" else 0.98)
        sl = price * (0.98 if signal == "BUY" else 1.02)

        explanation = (
            f"EMA50 {'>' if ema50 > ema200 else '<'} EMA200\n"
            f"RSI: {rsi14:.2f}\n"
            f"Тренд подтверждён"
        )

        return {
            "signal": signal,
            "price": price,
            "tp": tp,
            "sl": sl,
            "rsi": rsi14,
            "time": datetime.utcnow().strftime("%Y-%m-%d %H:%M UTC"),
            "explanation": explanation
        }
       ai_text = explain_signal({
            "price": price,
            "rsi": rsi,
            "ema20": ema20,
            "ema50": ema50,
            "signal": signal
})


    # -----------------------------------------
    # Telegram
    # -----------------------------------------
    def send_message(self, text):
        url = f"https://api.telegram.org/bot{self.bot_token}/sendMessage"
        payload = {
            "chat_id": self.chat_id,
            "text": text
        }
        requests.post(url, data=payload, timeout=10)

    # -----------------------------------------
    # Запуск
    # -----------------------------------------
    def run(self):
        signal = self.analyze()
        if not signal:
            return

        msg = (
            f"🚀 ETH OKX SIGNAL (15m)\n\n"
            f"📌 Сигнал: {signal['signal']}\n"
            f"💰 Цена: {signal['price']:.2f}\n"
            f"🎯 TP: {signal['tp']:.2f}\n"
            f"🛑 SL: {signal['sl']:.2f}\n"
            f"📊 RSI: {signal['rsi']:.2f}\n\n"
            f"🧠 AI:\n{signal['explanation']}\n\n"
            f"⏰ {signal['time']}"
            f"\n🧠 AI-анализ:\n{ai_text}"
        )

        self.send_message(msg)
