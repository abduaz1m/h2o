import time
import requests
from datetime import datetime


class CryptoTradingAgent:
    """
    Crypto Trading Agent using CoinGecko API
    """

    def __init__(self, telegram_bot_token, telegram_chat_id):
        self.telegram_bot_token = telegram_bot_token
        self.telegram_chat_id = telegram_chat_id

        self.coingecko_url = "https://api.coingecko.com/api/v3/simple/price"

        # соответствие символов CoinGecko
        self.coin_map = {
            "BTC": "bitcoin",
            "ETH": "ethereum",
            "SOL": "solana",
            "BNB": "binancecoin",
            "XRP": "ripple"
        }

    # --------------------------------------------------
    # Получение данных CoinGecko
    # --------------------------------------------------
    def get_price_data(self, symbol):
        coin_id = self.coin_map.get(symbol)
        if not coin_id:
            print(f"❌ Монета {symbol} не поддерживается")
            return None

        params = {
            "ids": coin_id,
            "vs_currencies": "usd",
            "include_24hr_change": "true"
        }

        try:
            r = requests.get(self.coingecko_url, params=params, timeout=10)
            r.raise_for_status()
            data = r.json()
            return data.get(coin_id)

        except Exception as e:
            print("❌ CoinGecko error:", e)
            return None

    # --------------------------------------------------
    # Анализ сигнала
    # --------------------------------------------------
    def analyze_signal(self, symbol):
        data = self.get_price_data(symbol)
        if not data:
            return None

        price = data["usd"]
        change_24h = data["usd_24h_change"]

        signal = {
            "crypto": symbol,
            "price": price,
            "change_24h": change_24h,
            "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        }

        if change_24h > 5:
            signal["action"] = "🟢 BUY"
            signal["reason"] = f"Рост +{change_24h:.2f}%"
        elif change_24h < -5:
            signal["action"] = "🔴 SELL"
            signal["reason"] = f"Падение {change_24h:.2f}%"
        else:
            signal["action"] = "⚪ HOLD"
            signal["reason"] = f"Боковик ({change_24h:+.2f}%)"

        return signal

    # --------------------------------------------------
    # Формат сообщения
    # --------------------------------------------------
    def format_message(self, s):
        return f"""
📊 <b>CRYPTO SIGNAL</b>

💰 Монета: {s['crypto']}
💵 Цена: ${s['price']}
📊 24h: {s['change_24h']:+.2f}%

{s['action']}
📝 {s['reason']}

⏰ {s['timestamp']}
""".strip()

    # --------------------------------------------------
    # Отправка Telegram
    # --------------------------------------------------
    def send_telegram(self, text):
        try:
            url = f"https://api.telegram.org/bot{self.telegram_bot_token}/sendMessage"
            data = {
                "chat_id": self.telegram_chat_id,
                "text": text,
                "parse_mode": "HTML"
            }
            requests.post(url, data=data)
        except Exception as e:
            print("❌ Telegram error:", e)

    # --------------------------------------------------
    # Запуск анализа
    # --------------------------------------------------
    def run_analysis(self, symbols):
        print("🚀 CoinGecko analysis started:", symbols)

        for s in symbols:
            signal = self.analyze_signal(s)
            if signal:
                msg = self.format_message(signal)
                self.send_telegram(msg)
                time.sleep(1)

    # --------------------------------------------------
    # Команда /check
    # --------------------------------------------------
    def handle_command(self, text, symbols):
        if text == "/check":
            self.send_telegram("🔍 Выполняю анализ (CoinGecko)...")
            self.run_analysis(symbols)
            return True
        return False
