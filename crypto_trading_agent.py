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
        # Подставляем токен и чат из bot_runner.py
        self.telegram_bot_token = telegram_bot_token
        self.telegram_chat_id = telegram_chat_id
        self.base_url = "https://api.binance.com/api/v3/ticker/24hr"

    # ----------------------------------------------------------
    # Получение данных с Binance
    # ----------------------------------------------------------
    def get_crypto_data(self, symbol="BTCUSDT"):
        try:
            url = f"{self.base_url}?symbol={symbol}"
            response = requests.get(url)
            response.raise_for_status()
            return response.json()
        except Exception as e:
            print(f"❌ Binance API Error: {e}")
            return None

    # ----------------------------------------------------------
    # Анализ монеты
    # ----------------------------------------------------------
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
            signal['action'] = '🟢 BUY'
            signal['reason'] = f'Сильный рост +{change_24h:.2f}%'
        elif change_24h < -5:
            signal['action'] = '🔴 SELL'
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

    # ----------------------------------------------------------
    # Форматирование сообщения Telegram
    # ----------------------------------------------------------
    def format_signal_message(self, signal):
        return f"""
🤖 ТОРГОВЫЙ СИГНАЛ (Binance)

💰 Монета: {signal['crypto']}
💵 Цена: ${signal['price']:,.4f}
📊 24h изменение: {signal['change_24h']:+.2f}%
📈 24h объем: {signal['volume_24h']:,.0f}

{signal['action']}
📝 {signal['reason']}

⏰ Время: {signal['timestamp']}
""".strip()

    # ----------------------------------------------------------
    # Отправка сообщения Telegram
    # ----------------------------------------------------------
    def send_telegram_message(self, message):
        try:
            url = f"https://api.telegram.org/bot{self.telegram_bot_token}/sendMessage"
            data = {
                'chat_id': self.telegram_chat_id,
                'text': message,
                'parse_mode': 'HTML'
            }
            requests.post(url, data=data)
        except Exception as e:
            print(f"❌ Telegram API Error: {e}")

    # ----------------------------------------------------------
    # Запуск анализа нескольких монет
    # ----------------------------------------------------------
    def run_analysis(self, cryptos):
        for crypto in cryptos:
            signal = self.analyze_signal(crypto)
            if signal:
                msg = self.format_signal_message(signal)
                self.send_telegram_message(msg)
                time.sleep(1)

    # ----------------------------------------------------------
    # ОБРАБОТКА КОМАНД (добавлено)
    # ----------------------------------------------------------
    def handle_command(self, text, cryptos):
        if text == "/check":
            self.send_telegram_message("🔍 Выполняю быстрый анализ...")
            self.run_analysis(cryptos)
            return True
        return False
