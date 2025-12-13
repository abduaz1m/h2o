import requests
import time
from datetime import datetime

class CryptoTradingAgent:
    def __init__(self, bot_token: str, chat_id: str):
        self.bot_token = bot_token
        self.chat_id = chat_id
        self.base_url = "https://api.coingecko.com/api/v3"

    # --------------------------------------------------
    # Получение данных из CoinGecko
    # --------------------------------------------------
    def get_coin_data(self, coin_id: str):
        url = f"{self.base_url}/coins/markets"
        params = {
            "vs_currency": "usd",
            "ids": coin_id,
            "order": "market_cap_desc",
            "per_page": 1,
            "page": 1,
            "sparkline": "false",
            "price_change_percentage": "24h"
        }

        r = requests.get(url, params=params, timeout=10)
        r.raise_for_status()
        data = r.json()

        if not data:
            return None

        return data[0]

    # --------------------------------------------------
    # Анализ монеты
    # --------------------------------------------------
    def analyze_coin(self, coin_id: str):
        data = self.get_coin_data(coin_id)
        if not data:
            return None

        change = data.get("price_change_percentage_24h", 0)

        if change > 3:
            action = "🟢 BUY"
        elif change < -3:
            action = "🔴 SELL"
        else:
            action = "⚪ HOLD"

        return {
            "coin": data["name"].upper(),
            "price": data["current_price"],
            "change": change,
            "volume": data["total_volume"],
            "action": action,
            "time": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        }

    # --------------------------------------------------
    # Отправка сообщения в Telegram
    # --------------------------------------------------
    def send_message(self, text: str):
        url = f"https://api.telegram.org/bot{self.bot_token}/sendMessage"
        payload = {
            "chat_id": self.chat_id,
            "text": text
        }
        requests.post(url, data=payload, timeout=10)

    # --------------------------------------------------
    # Запуск анализа
    # --------------------------------------------------
    def run_analysis(self, coins: list[str]):
        for coin in coins:
            result = self.analyze_coin(coin)
            if not result:
                continue

            message = (
                f"🤖 Crypto Signal (CoinGecko)\n\n"
                f"💰 Монета: {result['coin']}\n"
                f"💵 Цена: ${result['price']}\n"
                f"📊 24h: {result['change']:.2f}%\n"
                f"📈 Объём: {result['volume']}\n\n"
                f"👉 {result['action']}\n"
                f"⏰ {result['time']}"
            )

            self.send_message(message)
            time.sleep(1)
