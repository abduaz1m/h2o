import time
import requests
from datetime import datetime


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
            print(f"📡 Запрос к BingX: {url}")
            r = requests.get(url)
            r.raise_for_status()

            data = r.json()
            if "data" not in data or data["data"] is None:
                print("⚠ Нет данных от BingX!")
                return None

            return data["data"]

        except Exception as e:
            print(f"❌ BingX API Error: {e}")
            return None

    # ----------------------------------------------------------
    # Анализ монеты
    # ----------------------------------------------------------
    def analyze_signal(self, symbol):
        data = self.get_crypto_data(symbol)

        if not data:
            return None

        price = float(data["lastPrice"])
        change_24h = float(data["priceChangePercent"])
        volume_24h = float(data["volume"])

        signal = {
            "crypto": symbol.replace("-USDT", ""),
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
            signal['reason'] = f'Стабильная зона ({change_24h:+.2f}%)'

        return signal

    # ----------------------------------------------------------
    # Форматирование Telegram сообщения
    # ----------------------------------------------------------
    def format_signal_message(self, signal):
        return f"""
🤖 СИГНАЛ (BingX)

💰 Монета: {signal['crypto']}
💵 Цена: ${signal['price']:,.4f}
📊 24h изменение: {signal['change_24h']:+.2f}%
📈 24h объем: {signal['volume_24h']:,.0f}

{signal['action']}
📝 {signal['reason']}

⏰ Время: {signal['timestamp']}
""".strip()

    # ----------------------------------------------------------
    # Отправка в Telegram
    # ----------------------------------------------------------
    def send_telegram_message(self, message):
        try:
            url = f"https://api.telegram.org/bot{self.telegram_bot_token}/sendMessage"
            data = {
                "chat_id": self.telegram_chat_id,
                "text": message,
                "parse_mode": "HTML"
            }
            requests.post(url, data=data)
        except Exception as e:
            print(f"❌ Telegram Error: {e}")

    # ----------------------------------------------------------
    # Анализ сразу нескольких монет
    # ----------------------------------------------------------
    def run_analysis(self, symbols):
        print("🚀 Запуск анализа монет BingX...")
        for sym in symbols:
            signal = self.analyze_signal(sym)
            if signal:
                msg = self.format_signal_message(signal)
                self.send_telegram_message(msg)
                time.sleep(1)

    # ----------------------------------------------------------
    # Обработка команды /check
    # ----------------------------------------------------------
    def handle_command(self, text, symbols):
        if text == "/check":
            self.send_telegram_message("🔍 Выполняю быстрый анализ (BingX)...")
            self.run_analysis(symbols)
            return True
        return False
