import requests
import time
from datetime import datetime

class CryptoTradingAgent:
    def __init__(self, telegram_bot_token, telegram_chat_id):
        self.telegram_bot_token = telegram_bot_token
        self.telegram_chat_id = telegram_chat_id
        self.base_url = "https://api.coingecko.com/api/v3"

    # ---------- CoinGecko ----------
    def get_price(self, coin_id: str):
        url = f"{self.base_url}/simple/price"
        params = {
            "ids": coin_id,
            "vs_currencies": "usd",
            "include_24hr_change": "true",
            "include_24hr_vol": "true"
        }

        r = requests.get(url, params=params, timeout=10)
        r.raise_for_status()

        if coin_id not in r.json():
            return None

        data = r.json()[coin_id]
        return {
            "price": data["usd"],
            "change": data.get("usd_24h_change", 0),
            "volume": data.get("usd_24h_vol", 0)
        }

    # ---------- Анализ ----------
    def analyze_coin(self, coin: str):
        data = self.get_price(coin)
        if not data:
            return None

        change = data["change"]

        if change > 5:
            action = "🟢 BUY"
        elif change < -5:
            action = "🔴 SELL"
        else:
            action = "⚪ HOLD"

        return f"""
🤖 Crypto Signal (CoinGecko)

💰 Монета: {coin.upper()}
💵 Цена: ${data['price']:.4f}
📊 24h: {change:+.2f}%
📈 Объем: {data['volume']:.0f}

👉 {action}
⏰ {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
""".strip()

    # ---------- Telegram ----------
    def send_message(self, text: str):
        url = f"https://api.telegram.org/bot{self.bot_token}/sendMessage"
        requests.post(url, data={
            "chat_id": self.chat_id,
            "text": text
        })

    # ---------- Запуск анализа ----------
    def run_analysis(self, coins: list[str]):
        for coin in coins:
            msg = self.analyze_coin(coin)
            if msg:
                self.send_message(msg)
            time.sleep(1)
