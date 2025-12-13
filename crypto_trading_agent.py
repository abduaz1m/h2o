import os
import time
import requests
from datetime import datetime
import json

class CryptoTradingAgent:
    """
    AI агент на BingX API
    """

    def __init__(self, telegram_bot_token=None, telegram_chat_id=None):
        self.telegram_bot_token = telegram_bot_token
        self.telegram_chat_id = telegram_chat_id
        self.base_url = "https://api-swap-rest.bingx.com/openApi/quote/v1/ticker/24hr"

    # ----------------------------------------------------------
    # Получение данных с BingX
    # ----------------------------------------------------------
    def get_crypto_data(self, symbol="BTC-USDT"):
        try:
            url = f"{self.base_url}?symbol={symbol}"
            print(f"🌐 Запрос к BingX: {url}")
            r = requests.get(url, timeout=5)

            print(f"📥 Статус ответа BingX: {r.status_code}")
            print(f"📄 Ответ: {r.text[:200]}")

            r.raise_for_status()
            return r.json().get("data")

        except Exception as e:
            print(f"❌ BingX API Error: {e}")
            return None

    # ----------------------------------------------------------
    # Анализ монеты
    # ----------------------------------------------------------
    def analyze_signal(self, crypto):
        symbol = crypto.upper() + "-USDT"
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
🤖 ТОРГОВЫЙ СИГНАЛ (BingX)

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
        print("🚀 Запуск анализа монет (BingX)...")
        print("Список:", cryptos)

        for crypto in cryptos:
            print(f"➡ Анализ {crypto}...")
            signal = self.analyze_signal(crypto)

            if signal:
                msg = self.format_signal_message(signal)
                self.send_telegram_message(msg)
                time.sleep(1)
            else:
                print(f"⚠ Нет данных для {crypto}")

    # ----------------------------------------------------------
    # Обработка команды /check
    # ----------------------------------------------------------
    def handle_command(self, text, cryptos):
        if text == "/check":
            self.send_telegram_message("🔍 Выполняю быстрый анализ (BingX)...")
            self.run_analysis(cryptos)
            return True
        return False
