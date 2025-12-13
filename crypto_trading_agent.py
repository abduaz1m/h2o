import os
import time
import json
import requests
from datetime import datetime


class CryptoTradingAgent:
    """
    Агент анализа крипты через Binance API
    """

    def __init__(self, telegram_bot_token, telegram_chat_id):
        self.telegram_bot_token = telegram_bot_token
        self.telegram_chat_id = telegram_chat_id
        self.base_url = "https://api.binance.com/api/v3/ticker/24hr"

    def get_crypto_data(self, symbol="BTCUSDT"):
        """ Получение данных по монете с Binance """
        try:
            url = f"{self.base_url}?symbol={symbol}"
            r = requests.get(url)
            r.raise_for_status()
            return r.json()
        except Exception as e:
            print(f"❌ Ошибка запроса Binance API: {e}")
            return None

    def analyze_signal(self, crypto):
        """ Логика анализа монеты """
        symbol = crypto.upper() + "USDT"
        data = self.get_crypto_data(symbol)

        if not data:
            return None

        price = float(data["lastPrice"])
        change_24h = float(data["priceChangePercent"])
        volume = float(data["volume"])

        signal = {
            "crypto": crypto,
            "price": price,
            "change_24h": change_24h,
            "volume": volume,
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
            signal["reason"] = f"Изменение {change_24h:.2f}%"

        return signal

    def format_signal(self, sig):
        return (
f"""📈 CRYPTO SIGNAL

Монета: {sig['crypto'].upper()}
Цена: ${sig['price']:.4f}
Изм. 24ч: {sig['change_24h']}%
Объём: {sig['volume']}

Решение: {sig['action']}
Причина: {sig['reason']}

⏱ {sig['timestamp']}
"""
        )

    def send_telegram(self, text):
        """ Отправка в Telegram """
        try:
            url = f"https://api.telegram.org/bot{self.telegram_bot_token}/sendMessage"
            data = {
                "chat_id": self.telegram_chat_id,
                "text": text
            }
            r = requests.post(url, data=data)
            r.raise_for_status()
            print("📨 Сообщение отправлено!")
        except Exception as e:
            print(f"❌ Ошибка Telegram API: {e}")

    def run_analysis(self, cryptos):
        """ Анализ всех монет """
        print("🚀 START ANALYSIS...")

        for c in cryptos:
            print(f"▶ Анализ {c}...")
            sig = self.analyze_signal(c)

            if sig:
                msg = self.format_signal(sig)
                print(msg)

                # сохраняем
                name = f"signal_{c}_{int(time.time())}.json"
                with open(name, "w", encoding="utf-8") as f:
                    json.dump(sig, f, indent=2, ensure_ascii=False)

                # отправляем
                self.send_telegram(msg)

            time.sleep(1)

        print("✅ АНАЛИЗ ЗАВЕРШЁН\n")
