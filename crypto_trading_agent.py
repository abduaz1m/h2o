
# BEGIN: user added these matplotlib lines to ensure any plots do not pop-up in their UI
import matplotlib
matplotlib.use('Agg')  # Set the backend to non-interactive
import matplotlib.pyplot as plt
plt.ioff()
import os
os.environ['TERM'] = 'dumb'
# END: user added these matplotlib lines to ensure any plots do not pop-up in their UI
# filename: crypto_trading_agent.py
# execution: true

import os
import time
import requests
from datetime import datetime
import json

class CryptoTradingAgent:
    """
    AI агент для криптотрейдинга с отправкой сигналов в Telegram
    """
    
    def __init__(self, telegram_bot_token=None, telegram_chat_id=None):
        """
        Инициализация агента
        
        Args:
            telegram_bot_token: Токен Telegram бота
            telegram_chat_id: ID чата для отправки сообщений
        """
        self.telegram_bot_token = telegram_bot_token or "YOUR_BOT_TOKEN"
        self.telegram_chat_id = telegram_chat_id or "YOUR_CHAT_ID"
        self.base_url = "https://api.coingecko.com/api/v3"
        
    def get_crypto_data(self, crypto_id="bitcoin", vs_currency="usd"):
        """
        Получение данных о криптовалюте
        """
        try:
            url = f"{self.base_url}/simple/price"
            params = {
                'ids': crypto_id,
                'vs_currencies': vs_currency,
                'include_24hr_change': 'true',
                'include_24hr_vol': 'true'
            }
            response = requests.get(url, params=params)
            response.raise_for_status()
            return response.json()
        except Exception as e:
            print(f"Ошибка получения данных: {e}")
            return None
    
    def get_market_data(self, crypto_id="bitcoin"):
        """
        Получение расширенных рыночных данных
        """
        try:
            url = f"{self.base_url}/coins/{crypto_id}"
            params = {
                'localization': 'false',
                'tickers': 'false',
                'community_data': 'false',
                'developer_data': 'false'
            }
            response = requests.get(url, params=params)
            response.raise_for_status()
            return response.json()
        except Exception as e:
            print(f"Ошибка получения рыночных данных: {e}")
            return None
    
    def analyze_signal(self, crypto_id="bitcoin"):
        """
        Анализ и генерация торгового сигнала
        """
        data = self.get_crypto_data(crypto_id)
        market_data = self.get_market_data(crypto_id)
        
        if not data or not market_data:
            return None
        
        crypto_data = data.get(crypto_id, {})
        price = crypto_data.get('usd', 0)
        change_24h = crypto_data.get('usd_24h_change', 0)
        volume_24h = crypto_data.get('usd_24h_vol', 0)
        
        # Простой анализ на основе изменения цены
        signal = {
            'crypto': crypto_id.upper(),
            'price': price,
            'change_24h': change_24h,
            'volume_24h': volume_24h,
            'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        }
        
        # Определение сигнала
        if change_24h > 5:
            signal['action'] = '🟢 ПОКУПАТЬ (BUY)'
            signal['reason'] = f'Сильный рост +{change_24h:.2f}% за 24ч'
        elif change_24h < -5:
            signal['action'] = '🔴 ПРОДАВАТЬ (SELL)'
            signal['reason'] = f'Сильное падение {change_24h:.2f}% за 24ч'
        elif change_24h > 2:
            signal['action'] = '🟡 ДЕРЖАТЬ/ПОКУПАТЬ (HOLD/BUY)'
            signal['reason'] = f'Умеренный рост +{change_24h:.2f}% за 24ч'
        elif change_24h < -2:
            signal['action'] = '🟠 ДЕРЖАТЬ/ПРОДАВАТЬ (HOLD/SELL)'
            signal['reason'] = f'Умеренное падение {change_24h:.2f}% за 24ч'
        else:
            signal['action'] = '⚪ ДЕРЖАТЬ (HOLD)'
            signal['reason'] = f'Стабильная цена ({change_24h:+.2f}% за 24ч)'
        
        return signal
    
    def format_signal_message(self, signal):
        """
        Форматирование сообщения с сигналом
        """
        message = f"""
🤖 ТОРГОВЫЙ СИГНАЛ

💰 Криптовалюта: {signal['crypto']}
💵 Цена: ${signal['price']:,.2f}
📊 Изменение 24ч: {signal['change_24h']:+.2f}%
📈 Объем 24ч: ${signal['volume_24h']:,.0f}

{signal['action']}
📝 {signal['reason']}

⏰ Время: {signal['timestamp']}
"""
        return message.strip()
    
    def send_telegram_message(self, message):
        """
        Отправка сообщения в Telegram
        """
        try:
            url = f"https://api.telegram.org/bot{self.telegram_bot_token}/sendMessage"
            data = {
                'chat_id': self.telegram_chat_id,
                'text': message,
                'parse_mode': 'HTML'
            }
            response = requests.post(url, data=data)
            response.raise_for_status()
            return True
        except Exception as e:
            print(f"Ошибка отправки в Telegram: {e}")
            return False
    
    def run_analysis(self, cryptos=['bitcoin', 'ethereum', 'cardano']):
        """
        Запуск анализа для списка криптовалют
        """
        print("=" * 60)
        print("🚀 ЗАПУСК CRYPTO TRADING AGENT")
        print("=" * 60)
        
        for crypto in cryptos:
            print(f"\n📊 Анализ {crypto.upper()}...")
            signal = self.analyze_signal(crypto)
            
            if signal:
                message = self.format_signal_message(signal)
                print(message)
                print("\n" + "-" * 60)
                
                # Сохранение сигнала в файл
                with open(f'signal_{crypto}_{int(time.time())}.json', 'w', encoding='utf-8') as f:
                    json.dump(signal, f, ensure_ascii=False, indent=2)
                
                # Если настроен Telegram, отправляем сообщение
                if self.telegram_bot_token != "YOUR_BOT_TOKEN":
                    if self.send_telegram_message(message):
                        print(f"✅ Сигнал отправлен в Telegram для {crypto}")
                    else:
                        print(f"❌ Не удалось отправить сигнал в Telegram для {crypto}")
                else:
                    print(f"ℹ️  Telegram не настроен. Сигнал сохранен локально.")
            
            time.sleep(1)  # Задержка между запросами
        
        print("\n" + "=" * 60)
        print("✅ АНАЛИЗ ЗАВЕРШЕН")
        print("=" * 60)

# Демонстрация работы агента
if __name__ == "__main__":
    # Создание агента (замените на свои данные для работы с Telegram)
    agent = CryptoTradingAgent(
        telegram_bot_token="YOUR_BOT_TOKEN",  # Замените на токен вашего бота
        telegram_chat_id="YOUR_CHAT_ID"       # Замените на ID вашего чата
    )
    
    # Список криптовалют для анализа
    cryptos_to_analyze = ['bitcoin', 'ethereum', 'cardano', 'solana', 'ripple']
    
    # Запуск анализа
    agent.run_analysis(cryptos_to_analyze)
    
    print("\n📝 ИНСТРУКЦИЯ ПО НАСТРОЙКЕ TELEGRAM:")
    print("1. Создайте бота через @BotFather в Telegram")
    print("2. Получите токен бота")
    print("3. Узнайте свой chat_id (можно через @userinfobot)")
    print("4. Замените YOUR_BOT_TOKEN и YOUR_CHAT_ID в коде")
    print("5. Запустите агента снова для отправки сигналов в Telegram")