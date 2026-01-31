import os
from lumibot.brokers import Ccxt
from lumibot.traders import Trader
from strategy import DeepSeekScalper

# --- НАСТРОЙКИ ---
BOT_TOKEN = os.getenv("BOT_TOKEN")
CHAT_ID = os.getenv("CHAT_ID")
DEEPSEEK_KEY = os.getenv("DEEPSEEK_API_KEY")

# API Ключи от Биржи (OKX)
# Вам нужно добавить их в .env файл!
API_KEY = os.getenv("OKX_API_KEY")
API_SECRET = os.getenv("OKX_SECRET_KEY")
API_PASSWORD = os.getenv("OKX_PASSWORD") # OKX требует Passphrase

# Настройка Брокера (OKX Swap)
broker_config = {
    "exchange_id": "okx",
    "apiKey": API_KEY,
    "secret": API_SECRET,
    "password": API_PASSWORD,
    "options": {"defaultType": "swap"} # Важно: торгуем фьючерсами (свопами)
}

broker = Ccxt(broker_config)

# Настройка Стратегии
strategy_params = {
    "symbol": "BTC/USDT:USDT", # Формат символа для CCXT OKX Swap
    "timeframe": "5m",
    "deepseek_key": DEEPSEEK_KEY,
    "telegram_token": BOT_TOKEN,
    "chat_id": CHAT_ID
}

# Создаем стратегию
strategy = DeepSeekScalper(
    broker=broker, 
    parameters=strategy_params
)

# Запускаем трейдера
trader = Trader()
trader.add_strategy(strategy)
trader.run_all()
