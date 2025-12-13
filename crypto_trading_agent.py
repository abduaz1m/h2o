import time
import requests
from datetime import datetime


class CryptoTradingAgent:
    def __init__(self, telegram_bot_token, telegram_chat_id):
        self.bot_token = telegram_bot_token
        self.chat_id = telegram_chat_id

        self.base_url = "https://api.coingecko.com/api/v3"
        self.coin_id = "ethereum"  # ⬅️ ТОЛЬКО ETH

    # --------------------------------------------------
    # Получаем OHLC данные (для RSI / EMA)
    # --------------------------------------------------
    def get_market_data(self):
        url = f"{self.base_url}/coins/{self.coin_id}/market_chart"
        params = {
            "vs_currency": "usd",
            "days": "1",
            "interval": "hourly"
        }

        r = requests.get(url, params=params, timeout=10)
        r.raise_for_status()
        return r.json()["prices"]

    # --------------------------------------------------
    # RSI
    # --------------------------------------------------
    def calculate_rsi(self, prices, period=14):
        gains, losses = [], []

        for i in range(1, len(prices)):
            diff = prices[i] - prices[i - 1]
            if diff >= 0:
                gains.append(diff)
            else:
                losses.append(abs(diff))

        avg_gain = sum(gains[-period:]) / period if gains else 0
        avg_loss = sum(losses[-period:]) / period if losses else 1

        rs = avg_gain / avg_loss if avg_loss != 0 else 0
        return 100 - (100 / (1 + rs))

    # --------------------------------------------------
    # EMA
    # --------------------------------------------------
    def calculate_ema(self, prices, period=20):
        k = 2 / (period + 1)
        ema = prices[0]

        for price in prices[1:]:
            ema = price * k + ema * (1 - k)

        return ema

    # --------------------------------------------------
    # Анализ ETH
    # --------------------------------------------------
    def analyze(self):
        data = self.get_market_data()
        prices = [p[1] for p in data]

        last_price = prices[-1]
        rsi = self.calculate_rsi(prices)
        ema = self.calculate_ema(prices)

        if rsi < 30 and last_price > ema:
            action = "🟢 BUY"
            reason = "RSI < 30 и цена выше EMA"
        elif rsi > 70 and last_price < ema:
            action = "🔴 SELL"
            reason = "RSI > 70 и цена ниже EMA"
        else:
            action = "⚪ HOLD"
            reason = "Нет сильного сигнала"

        return f"""
📊 <b>ETH SIGNAL</b>

💰 Цена: ${last_price:.2f}
📈 EMA: {ema:.2f}
📉 RSI: {rsi:.2f}

👉 {action}
📝 {reason}

⏰ {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
""".strip()

    # --------------------------------------------------
    # Telegram
    # --------------------------------------------------
    def send_message(self, text):
        url = f"https://api.telegram.org/bot{self.bot_token}/sendMessage"
        requests.post(url, data={
            "chat_id": self.chat_id,
            "text": text,
            "parse_mode": "HTML"
        })

    # --------------------------------------------------
    def run_analysis(self):
        msg = self.analyze()
        self.send_message(msg)
        time.sleep(2)  # ⬅️ ЗАЩИТА ОТ 429
