import time
import requests
from datetime import datetime

class CryptoTradingAgent:
    def __init__(self, telegram_bot_token, telegram_chat_id):
        self.bot_token = telegram_bot_token
        self.chat_id = telegram_chat_id

        # CoinGecko API
        self.api_url = "https://api.coingecko.com/api/v3/coins/markets"

        # Жёстко оставляем ТОЛЬКО ETH
        self.coin_id = "ethereum"

    # ================================
    # Получение данных (БЕЗ 429)
    # ================================
    def get_eth_data(self):
        params = {
            "vs_currency": "usd",
            "ids": self.coin_id,
            "order": "market_cap_desc",
            "per_page": 1,
            "page": 1,
            "sparkline": "false",
            "price_change_percentage": "24h"
        }

        response = requests.get(
            self.api_url,
            params=params,
            timeout=15,
            headers={
                "Accept": "application/json",
                "User-Agent": "RenderBot/1.0"
            }
        )

        response.raise_for_status()
        data = response.json()
        return data[0]

    # ================================
    # Анализ ETH
    # ================================
    def analyze(self):
        data = self.get_eth_data()

        price = data["current_price"]
        change_24h = data["price_change_percentage_24h"]
        volume = data["total_volume"]

        if change_24h > 2:
            action = "🟢 BUY"
        elif change_24h < -2:
            action = "🔴 SELL"
        else:
            action = "⚪ HOLD"

        message = f"""
🤖 Crypto Signal (CoinGecko)

💰 Монета: ETHEREUM
💵 Цена: ${price:,.2f}
📊 24h: {change_24h:+.2f}%
📈 Объем: {volume:,}

👉 {action}
⏰ {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
""".strip()

        return message

    # ================================
    # Отправка в Telegram
    # ================================
    def send_message(self, text):
        url = f"https://api.telegram.org/bot{self.bot_token}/sendMessage"
        payload = {
            "chat_id": self.chat_id,
            "text": text
        }
        requests.post(url, data=payload, timeout=10)

    # ================================
    # Запуск анализа
    # ================================
    def run_analysis(self):
        message = self.analyze()
        self.send_message(message)

        # 🔥 КРИТИЧНО: защита от 429
        time.sleep(30)

    # ================================
    # Команды
    # ================================
    def handle_command(self, text):
        if text == "/check":
            self.send_message("🔍 Анализ ETH запущен...")
            self.run_analysis()

        elif text == "/status":
            self.send_message("✅ Бот активен\n📡 Источник: CoinGecko\n⏱ Интервал: 10 минут\n💰 Монета: ETH")
