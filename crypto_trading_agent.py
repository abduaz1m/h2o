import time
import requests
import math
from datetime import datetime


class CryptoTradingAgent:
    def __init__(self, telegram_bot_token, telegram_chat_id, coingecko_api_key):
        self.bot_token = telegram_bot_token
        self.chat_id = telegram_chat_id
        self.cg_key = coingecko_api_key

        self.headers = {
            "x-cg-pro-api-key": self.cg_key
        }

    # -----------------------------
    # Получаем цены ETH (часовые)
    # -----------------------------
    def get_prices(self):
        url = "https://api.coingecko.com/api/v3/coins/ethereum/market_chart"
        params = {
            "vs_currency": "usd",
            "days": 1,
            "interval": "hourly"
        }

        r = requests.get(url, headers=self.headers, params=params)
        r.raise_for_status()

        prices = [p[1] for p in r.json()["prices"]]
        return prices

    # -----------------------------
    # Индикаторы
    # -----------------------------
    def ema(self, prices, period):
        k = 2 / (period + 1)
        ema = prices[0]
        for price in prices[1:]:
            ema = price * k + ema * (1 - k)
        return ema

    def rsi(self, prices, period=14):
        gains, losses = [], []
        for i in range(1, period + 1):
            diff = prices[-i] - prices[-i - 1]
            if diff >= 0:
                gains.append(diff)
            else:
                losses.append(abs(diff))

        avg_gain = sum(gains) / period if gains else 0.0001
        avg_loss = sum(losses) / period if losses else 0.0001

        rs = avg_gain / avg_loss
        return 100 - (100 / (1 + rs))

    # -----------------------------
    # Анализ
    # -----------------------------
    def analyze(self):
        prices = self.get_prices()

        last = prices[-1]
        ema_fast = self.ema(prices[-20:], 20)
        ema_slow = self.ema(prices[-50:], 50)
        rsi_val = self.rsi(prices)

        signal = None

        if ema_fast > ema_slow and rsi_val < 70:
            signal = "BUY"
        elif ema_fast < ema_slow and rsi_val > 30:
            signal = "SELL"

        if not signal:
            return None

        tp = last * (1.03 if signal == "BUY" else 0.97)
        sl = last * (0.97 if signal == "BUY" else 1.03)

        explanation = (
            f"EMA20 {'>' if ema_fast > ema_slow else '<'} EMA50\n"
            f"RSI={rsi_val:.1f}\n"
            f"Trend confirmation"
        )

        return {
            "signal": signal,
            "price": last,
            "tp": tp,
            "sl": sl,
            "explanation": explanation
        }

    # -----------------------------
    # Telegram
    # -----------------------------
    def send(self, text):
        url = f"https://api.telegram.org/bot{self.bot_token}/sendMessage"
        requests.post(url, data={"chat_id": self.chat_id, "text": text})

    # -----------------------------
    # RUN
    # -----------------------------
    def run(self):
        result = self.analyze()
        if not result:
            print("⏸ No signal")
            return

        msg = (
            f"🤖 ETH SIGNAL\n\n"
            f"📌 {result['signal']}\n"
            f"💰 Price: ${result['price']:.2f}\n"
            f"🎯 TP: ${result['tp']:.2f}\n"
            f"🛑 SL: ${result['sl']:.2f}\n\n"
            f"🧠 AI explanation:\n{result['explanation']}\n\n"
            f"⏰ {datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')} UTC"
        )

        self.send(msg)
        print("✅ Signal sent")
