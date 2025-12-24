import ccxt
import time
import pandas as pd
import pandas_ta as ta
from datetime import datetime
from openai import OpenAI

# --- 🔐 НАСТРОЙКИ API OKX ---
# Впишите сюда ваши ключи от биржи
API_KEY = "ВАШ_OKX_API_KEY"
API_SECRET = "ВАШ_OKX_SECRET_KEY"
API_PASSWORD = "ВАШ_OKX_PASSPHRASE"

# ⚙️ РЕЖИМ РАБОТЫ
# True = Демо счет (деньги не тратятся)
# False = Реальные деньги!
SANDBOX_MODE = False  

# Настройки торговли
MAX_POSITIONS = 3     # Максимум сделок одновременно
ORDER_AMOUNT_USD = 50 # Размер входа в сделку в $

# СПИСОК МОНЕТ (Фьючерсы)
FUTURES_SYMBOLS = {
    "BTC/USDT:USDT": {"lev": 10},
    "ETH/USDT:USDT": {"lev": 10},
    "SOL/USDT:USDT": {"lev": 10},
    "TON/USDT:USDT": {"lev": 5},
    "ARB/USDT:USDT": {"lev": 5},
    "DOGE/USDT:USDT": {"lev": 5},
    "PEPE/USDT:USDT": {"lev": 3},
}

class TradingAgent:
    def __init__(self, bot_token, chat_id, deepseek_key):
        self.bot_token = bot_token
        self.chat_id = chat_id
        
        # 👇 ИЗМЕНЕНИЕ 1: Подключение к DeepSeek
        self.client = OpenAI(
            api_key=deepseek_key, 
            base_url="https://api.deepseek.com" # Указываем адрес DeepSeek
        )
        
        # Подключение к бирже OKX
        try:
            self.exchange = ccxt.okx({
                'apiKey': API_KEY,
                'secret': API_SECRET,
                'password': API_PASSWORD,
                'enableRateLimit': True,
                'options': {'defaultType': 'swap'} # Фьючерсы
            })
            if SANDBOX_MODE:
                self.exchange.set_sandbox_mode(True)
        except Exception as e:
            print(f"❌ Ошибка подключения к бирже: {e}")

        self.positions = {name: None for name in FUTURES_SYMBOLS}

    # --- ТЕЛЕГРАМ ---
    def send(self, text):
        import requests
        try:
            requests.post(
                f"https://api.telegram.org/bot{self.bot_token}/sendMessage", 
                json={"chat_id": self.chat_id, "text": text, "parse_mode": "Markdown"}, timeout=5
            )
        except: pass

    # --- БИРЖА: ДАННЫЕ ---
    def get_candles(self, symbol, limit=100):
        try:
            ohlcv = self.exchange.fetch_ohlcv(symbol, '15m', limit=limit)
            df = pd.DataFrame(ohlcv, columns=['ts', 'o', 'h', 'l', 'c', 'v'])
            return df
        except Exception as e:
            return None

    # --- БИРЖА: ОРДЕРА ---
    def open_order(self, symbol, side, leverage):
        try:
            # 1. Ставим плечо
            try:
                self.exchange.set_leverage(leverage, symbol)
            except: pass # Иногда плечо уже стоит

            # 2. Считаем объем (Сколько монет купить на 50$)
            ticker = self.exchange.fetch_ticker(symbol)
            price = ticker['last']
            amount = ORDER_AMOUNT_USD / price 
            
            # 3. Открываем (Market Order)
            order = self.exchange.create_order(symbol, 'market', side, amount)
            return True, order['id']
        except Exception as e:
            return False, str(e)

    # --- 🧠 DEEPSEEK АНАЛИЗ ---
    def ask_ai(self, symbol, price, rsi, adx):
        print(f"🧠 Asking DeepSeek about {symbol}...")
        
        # Промпт адаптирован под DeepSeek (он любит четкость)
        prompt = f"""
        Ты профессиональный трейдер.
        Актив: {symbol}
        Цена: {price}
        RSI (14): {rsi}
        ADX (14): {adx}
        
        Стратегия: Вход только по тренду.
        1. Если ADX < 20, рынок спит -> WAIT.
        2. Если RSI > 70, перекуплен -> WAIT.
        3. Если RSI 50-70 и ADX > 25 -> BUY.
        
        Дай ответ в формате JSON:
        Risk: [1-10]/10
        Verdict: [BUY / WAIT]
        Reason: [Коротко]
        """

        for i in range(2):
            try:
                response = self.client.chat.completions.create(
                    model="deepseek-chat", # 👇 ИЗМЕНЕНИЕ 2: Модель DeepSeek
                    messages=[{"role": "user", "content": prompt}],
                    max_tokens=100,
                    temperature=0.0 # Делаем ответы строгими
                )
                return response.choices[0].message.content
            except Exception as e:
                time.sleep(1)
        return "Skip"

    # --- ГЛАВНЫЙ ЦИКЛ ---
    def analyze(self):
        print(f"--- 🐋 DeepSeek Trader ({'DEMO' if SANDBOX_MODE else 'REAL'}) ---")
        
        for symbol, info in FUTURES_SYMBOLS.items():
            lev = info["lev"]
            time.sleep(1) # Лимиты биржи

            df = self.get_candles(symbol)
            if df is None: continue

            # Индикаторы
            df['ema9'] = ta.ema(df['c'], length=9)
            df['ema21'] = ta.ema(df['c'], length=21)
            df['rsi'] = ta.rsi(df['c'], length=14)
            df['adx'] = ta.adx(df['h'], df['l'], df['c'])['ADX_14']
            
            curr = df.iloc[-1]

            # 1. Технический фильтр (Python)
            # Пересечение EMA + Хороший RSI + Есть тренд
            tech_signal = False
            if (curr['ema9'] > curr['ema21'] and 
                50 < curr['rsi'] < 70 and 
                curr['adx'] > 25):
                tech_signal = True

            # Если есть тех. сигнал и мы не в позиции
            if tech_signal and self.positions[symbol] != "BUY":
                
                # 2. Мнение DeepSeek
                ai_verdict = self.ask_ai(symbol, curr['c'], round(curr['rsi'],1), round(curr['adx'],1))
                
                if "WAIT" in ai_verdict.upper():
                    print(f"🚫 DeepSeek отменил вход по {symbol}: {ai_verdict}")
                    continue

                # 3. Вход в сделку
                print(f"🚀 Входим в {symbol}!")
                success, msg = self.open_order(symbol, 'buy', lev)
                
                if success:
                    self.send(
                        f"🐋 **DEEPSEEK SIGNAL**\n"
                        f"#{symbol} — BUY OPEN\n"
                        f"💰 Amount: ${ORDER_AMOUNT_USD}\n"
                        f"⚙️ Lev: {lev}x\n"
                        f"🧠 AI: {ai_verdict}"
                    )
                    self.positions[symbol] = "BUY"
                else:
                    self.send(f"⚠️ Ошибка ордера {symbol}: {msg}")
