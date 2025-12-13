import requests
import time
from datetime import datetime

class CryptoTradingAgent:
    def __init__(self, telegram_bot_token, telegram_chat_id):
        self.telegram_bot_token = telegram_bot_token
        self.telegram_chat_id = telegram_chat_id
        self.base_url = "https://api.coingecko.com/api/v3/coins/markets"

    def get_market_data(self, cryptos):
        ids = ",".join(cryptos)
        params = {
            "vs_currency": "usd",
            "ids": ids,
            "order": "market_cap_desc",
            "per_page": len(cryptos),
            "page": 1,
            "sparkline": "false",
            "price_change_percentage": "24h"
        }

        try:
            r = requests.get(self.base_url, params=params, timeout=10)
            if r.status_code == 429:
                print("⏳ CoinGecko rate limit. Sleeping 60s...")
                time.sleep(60)
                return self.get_market_data(cryptos)

            r.raise_for_status()
            return r.json()

        except Exception as e:
            print("❌ CoinGecko error:", e)
            return []

    def send_message(self, text):
        url = f"https://api.telegram.org/bot{self.telegram_bot_token}/sendMessage"
        data = {"chat_id": self.telegram_chat_id, "text": text}
        requests.post(url, data=data)

    def analyze(self, coin):
        change = coin.get("price_change_percentage_24h", 0)

        if change > 5:
            action = "🟢 BUY"
        elif change < -5:
            action = "🔴 SELL"
        else:
            action = "⚪ HOLD"

        return f"""
🤖 Crypto Signal (CoinGecko)

💰 Монета: {coin['name'].upper()}
💵 Цена: ${coin['current_price']}
📊 24ч: {change:.2f}%
📈 Объём: {coin['total_volume']}

👉 {action}
⏰ {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
""".strip()

    def run_analysis(self, cryptos):
        print("🚀 CoinGecko analysis started:", cryptos)

        data = self.get_market_data(cryptos)

        for coin in data:
            msg = self.analyze(coin)
            self.send_message(msg)
            time.sleep(2)  # ⬅️ ОБЯЗАТЕЛЬНО
