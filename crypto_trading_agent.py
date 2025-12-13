import time
import requests
from datetime import datetime


class CryptoTradingAgent:
    def __init__(self, telegram_bot_token, telegram_chat_id):
        self.bot_token = telegram_bot_token
        self.chat_id = telegram_chat_id

        self.api_url = "https://api.coingecko.com/api/v3/coins/ethereum/market_chart"
        self.session = requests.Session()

    # --------------------------------------------------
    # Получаем исторические цены (1 день, 5-мин свечи)
    # --------------------------------------------------
    def get_prices(self):
        params = {
            "vs_currency": "usd",
            "days": "1",
            "interval": "minutely"
        }
        r = self.session.get(self.api_url, params=params, timeout=10)
        r.raise_for_status()
        prices = [p[1] for p in r.json()["prices"]]
        return prices

    # --------------------------------------------------
    # Индикаторы
    # --------------------------------------------------
    def ema(self, prices, period=20):
        k = 2 / (period + 1)
        ema = prices[0]
        for p in prices[1:]:
            ema = p * k + ema * (1 - k)
        return ema

    def rsi(self, prices, period=14):
        gains, losses = [], []
        for i in range(1, period + 1):
            diff = prices[i] - prices[i - 1]
            if diff >= 0:
                gains.append(diff)
            else:
                losses.append(abs(diff))

        avg_gain = sum(gains) / period
        avg_loss = sum(losses) / period if losses else 0.0001
        rs = avg_gain / avg_loss
        return 100 - (100 / (1 + rs))

    # --------------------------------------------------
    # Стратегия
    # --------------------------------------------------
    def analyze(self):
        prices = self.get_prices()
        price = prices[-1]

        ema20 = self.ema(prices, 20)
        ema50 = self.ema(prices, 50)
        rsi14 = self.rsi(prices)

        # BUY
        if price > ema20 > ema50 and rsi14 < 65:
            action = "🟢 BUY"
        # SELL
        elif price < ema20 < ema50 and rsi14 > 35:
            action = "🔴 SELL"
        else:
            return None  # фильтр: ничего не слать

        # TP / SL
        if action == "🟢 BUY":
            tp = price * 1.03
            sl = price * 0.97
        else:
            tp = price * 0.97
            sl = price * 1.03

        # AI explanation
        explanation = (
            f"Цена {'выше' if price > ema20 else 'ниже'} EMA20 и EMA50, "
            f"RSI={rsi14:.1f}. "
            f"Рынок {'бычий' if action == '🟢 BUY' else 'медвежий'}, "
            f"ожидается продолжение движения."
        )

        return {
            "price": price,
            "ema20": ema20,
            "ema50": ema50,
            "rsi": rsi14,
            "action": action,
            "tp": tp,
            "sl": sl,
            "explanation": explanation,
            "time": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        }

    # --------------------------------------------------
    # Telegram
    # --------------------------------------------------
    def send(self, text):
        url = f"https://api.telegram.org/bot{self.bot_token}/sendMessage"
        self.session.post(url, data={
            "chat_id": self.chat_id,
            "text": text
        })

    # --------------------------------------------------
    # Запуск анализа
    # --------------------------------------------------
    def run(self):
        signal = self.analyze()
        if not signal:
            return

        msg = (
            f"📊 ETH SIGNAL\n\n"
            f"💵 Price: ${signal['price']:.2f}\n"
            f"📉 RSI: {signal['rsi']:.1f}\n"
            f"📈 EMA20 / EMA50\n\n"
            f"{signal['action']}\n\n"
            f"🎯 TP: ${signal['tp']:.2f}\n"
            f"🛑 SL: ${signal['sl']:.2f}\n\n"
            f"🧠 AI:\n{signal['explanation']}\n\n"
            f"⏰ {signal['time']}"
        )

        self.send(msg)
