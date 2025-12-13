import os
import time
import requests
from datetime import datetime
import json

class CryptoTradingAgent:
    """
    AI агент на Binance API
    """

    def __init__(self, telegram_bot_token=None, telegram_chat_id=None):
        self.telegram_bot_token = telegram_bot_token
        self.telegram_chat_id = telegram_chat_id
        self.base_url = "https://api.binance.com/api/v3/ticker/24hr"

    def get_crypto_data(self, symbol="BTCUSDT"):
        try:
            url = f"{self.base_url}?symbol={symbol}"
            response = requests.get(url)
            response.raise_for_status()
            return response.json()
        except Exception as e:
            print(f"❌ Ошибка Binance API: {e}")
            return None

    def analyze_signal(self, crypto):
        symbol = crypto.upper() + "USDT"
        data = self.get_crypto_data(symbol)

        if not data:
            return None

        price = float(data["lastPrice"])
        change_24h = float(data["priceChangePercent"])
        volume_24h = float(data["volume"])

        signal = {
            "crypto": crypto.upper(),
            "price": price,
            "change_24h": change_24h,
            "volume_24h": volume_24h,
            "timestamp": datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        }

        # Логика сигналов
        if change_24h > 5:
            signal['action'] = '🟢 ПОКУПАТЬ (BUY)'
            signal['reason'] = f'Сильный рост +{change_24h:.2f}%'
        elif change_24h < -5:
            signal['action'] = '🔴 ПРОДАВАТЬ (SELL)'
            signal['reason'] = f'Сильное падение {change_24h:.2f}%'
        elif change_24h > 2:
            signal['action'] = '🟡 HOLD/BUY'
            signal['reason'] = f'Умеренный рост +{change_24h:.2f}%'
        elif change_24h < -2:
            signal['action'] = '🟠 HOLD/SELL'
            signal['reason'] = f'Умеренное падение {change_24h:.2f}%'
        else:
            signal['action'] = '⚪ HOLD'
            signal['reason'] = f'Стабильная цена ({change_24h:+.2f}%)'

        return signal

    def format_signal_message(self, signal):
        message = f"""
🤖 ТОРГОВЫЙ СИГНАЛ (Binance)

💰 Монета: {signal['crypto']}
💵 Цена: ${signal['price']:,.4f}
📊 24h изменение: {signal['change_24h']:+.2f}%
📈 24h объем: {signal['volume_24h']:,.0f}

{signal['action']}
📝 {signal['reason']}

⏰ Время: {signal['timestamp']}
"""
        return message.strip()

    def send_telegram_message(self, message):
        try:
            url = f"https://api.telegram.org/bot{self.telegram_bot_token}/sendMessage"
            data = {'chat_id': self.telegram_chat_id, 'text': message}
            requests.post(url, data=data)
        except Exception as e:
            print(f"❌ Ошибка Telegram API: {e}")

    def run_analysis(self, cryptos):
        print("=" * 60)
        print("🚀 ЗАПУСК CRYPTO TRADING AGENT (Binance API)")
        print("=" * 60)

        for crypto in cryptos:
            print(f"\n📊 Анализ {crypto.upper()}...")
            signal = self.analyze_signal(crypto)

            if signal:
                message = self.format_signal_message(signal)
                print(message)

                with open(f"signal_{crypto}_{int(time.time())}.json", "w", encoding="utf-8") as f:
                    json.dump(signal, f, ensure_ascii=False, indent=2)

                self.send_telegram_message(message)

            time.sleep(1)

        print("\n✅ АНАЛИЗ ЗАВЕРШЕН\n")
