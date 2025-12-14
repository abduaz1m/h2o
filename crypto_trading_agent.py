import requests
import time
import math

class CryptoTradingAgent:
    def __init__(self, telegram_bot_token, telegram_chat_id):
        self.bot_token = telegram_bot_token
        self.chat_id = telegram_chat_id

        self.symbol = "ETH-USDT"
        self.okx_url = "https://www.okx.com/api/v5/market/candles"

    # ------------------ TELEGRAM ------------------
    def send_message(self, text):
        url = f"https://api.telegram.org/bot{self.bot_token}/sendMessage"
        payload = {
            "chat_id": self.chat_id,
            "text": text,
            "parse_mode": "HTML"
        }
        requests.post(url, data=payload, timeout=10)

    # ------------------ OKX DATA ------------------
    def get_candles(self, limit=200):
        params = {
            "instId": self.symbol,
            "bar": "15m",
            "limit": str(limit)
        }
        r = requests.get(self.okx_url, params=params, timeout=10)
        r.raise_for_status()
        data = r.json()["data"]
        closes = [float(c[4]) for c in reversed(data)]
        return closes

    # ------------------ INDICATORS ------------------
    def ema(self, prices, period):
        k = 2 / (period + 1)
        ema = prices[0]
        for p in prices[1:]:
            ema = p * k + ema * (1 - k)
        return ema

    def rsi(self, prices, period=14):
        gains, losses = 0, 0
        for i in range(-period, -1):
            diff = prices[i+1] - prices[i]
            if diff > 0:
                gains += diff
            else:
                losses -= diff
        if losses == 0:
            return 100
        rs = gains / losses
        return 100 - (100 / (1 + rs))

    # ------------------ LLM (локальное объяснение) ------------------
    def llm_explain(self, signal, rsi, ema_fast, ema_slow):
        if signal == "BUY":
            return (
                "Цена находится выше EMA200, EMA50 направлена вверх. "
                f"RSI={rsi:.1f} указывает на восходящий импульс. "
                "Вероятно продолжение роста."
            )
        else:
            return (
                "Цена ниже EMA200, EMA50 направлена вниз. "
                f"RSI={rsi:.1f} подтверждает давление продавцов. "
                "Вероятно продолжение снижения."
            )

    # ------------------ STRATEGY ------------------
    def analyze(self, prices):
        ema50 = self.ema(prices[-50:], 50)
        ema200 = self.ema(prices[-200:], 200)
        rsi_val = self.rsi(prices)

        price = prices[-1]

        if price > ema200 and ema50 > ema200 and rsi_val > 55:
            return "BUY", price, rsi_val, ema50, ema200

        if price < ema200 and ema50 < ema200 and rsi_val < 45:
            return "SELL", price, rsi_val, ema50, ema200

        return None, price, rsi_val, ema50, ema200

    # ------------------ MAIN RUN ------------------
    def run(self):
        prices = self.get_candles()
        signal, price, rsi_val, ema50, ema200 = self.analyze(prices)

        if signal is None:
            print("⏸ HOLD — сигнал не отправлен")
            return

        # TP / SL
        if signal == "BUY":
            tp = price * 1.02
            sl = price * 0.985
        else:
            tp = price * 0.98
            sl = price * 1.015

        explanation = self.llm_explain(signal, rsi_val, ema50, ema200)

        msg = (
            f"<b>🤖 ETH OKX SIGNAL (15m)</b>\n\n"
            f"<b>Сигнал:</b> {'🟢 BUY' if signal=='BUY' else '🔴 SELL'}\n"
            f"<b>Цена:</b> {price:.2f}\n"
            f"<b>RSI:</b> {rsi_val:.1f}\n"
            f"<b>EMA50 / EMA200:</b> {ema50:.2f} / {ema200:.2f}\n\n"
            f"<b>TP:</b> {tp:.2f}\n"
            f"<b>SL:</b> {sl:.2f}\n\n"
            f"<b>🧠 AI-объяснение:</b>\n{explanation}"
        )

        self.send_message(msg)
