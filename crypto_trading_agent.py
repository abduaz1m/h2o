import time
import requests
from datetime import datetime

class CryptoTradingAgent:

    def __init__(self, telegram_bot_token, telegram_chat_id):
        self.telegram_bot_token = telegram_bot_token
        self.telegram_chat_id = telegram_chat_id
        self.base_url = "https://api.binance.com/api/v3/ticker/24hr"

    # ===================== BINANCE DATA =====================

    def get_crypto_data(self, symbol):
        try:
            url = f"{self.base_url}?symbol={symbol}"
            r = requests.get(url, timeout=5)
            r.raise_for_status()
            return r.json()
        except Exception as e:
            print(f"❌ Binance API ERROR for {symbol}: {e}")
            return None

    # ===================== ANALYSIS ======================

    def analyze_signal(self, crypto):
        symbol = crypto.upper() + "USDT"
        data = self.get_crypto_data(symbol)

        if not data:
            print(f"⚠ Нет данных по {symbol}")
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

        if change_24h > 5:
            signal["action"] = "🟢 BUY"
            signal["reason"] = f"Рост +{change_24h:.2f}%"
        elif change_24h < -5:
            signal["action"] = "🔴 SELL"
            signal["reason"] = f"Падение {change_24h:.2f}%"
        else:
            signal["action"] = "⚪ HOLD"
            signal["reason"] = f"Изменение {change_24h:+.2f}%"

        return signal

    # =================== MESSAGE FORMAT ====================

    def format_signal_message(self, s):
        return f"""
🔔 *Сигнал по {s['crypto']}*

💵 Цена: ${s['price']:.4f}
📊 Изм. 24h: {s['change_24h']:+.2f}%
📈 Объем: {s['volume_24h']}

{ s['action'] }
📝 { s['reason'] }

⏰ {s['timestamp']}
""".strip()

    # ===================== SEND TO TELEGRAM =====================

    def send_telegram_message(self, text):
        try:
            url = f"https://api.telegram.org/bot{self.telegram_bot_token}/sendMessage"
            data = {
                "chat_id": self.telegram_chat_id,
                "text": text,
                "parse_mode": "Markdown"
            }
            requests.post(url, data=data)
            print("📤 Отправлено в Telegram")
        except Exception as e:
            print(f"❌ Telegram ERROR: {e}")

    # ===================== RUN ANALYSIS ======================

    def run_analysis(self, cryptos):

        print("🔎 Запуск анализа монет...")
        print("Список:", cryptos)

        for crypto in cryptos:
            print(f"➡ Анализ {crypto}...")
            signal = self.analyze_signal(crypto)

            if not signal:
                print(f"⚠ Сигнал отсутствует для {crypto}")
                continue

            msg = self.format_signal_message(signal)
            print("📘 Сигнал:", msg)   # ЛОГ В КОНСОЛИ!

            self.send_telegram_message(msg)
            time.sleep(1)

        print("✅ Анализ завершён")

    # ===================== COMMAND HANDLER ======================

    def handle_command(self, text, cryptos):
        if text == "/check":
            self.send_telegram_message("🔍 Запускаю анализ...")
            self.run_analysis(cryptos)
            return True
        return False
