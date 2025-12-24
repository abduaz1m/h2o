import os
import ccxt
import time
import pandas as pd
import pandas_ta as ta
from datetime import datetime
from openai import OpenAI

# --- 🔐 НАСТРОЙКИ API OKX ---
API_KEY = "a1af4b19-b6c9-45d3-ae8f-e11247c6f222Y"
API_SECRET = "9E00FB5D0EA222DD54488B768AD20580"
API_PASSWORD = "Abduxalilov022$"

# ⚙️ РЕЖИМ РАБОТЫ
# False = Торгуем реальными деньгами
# True = Тестовый режим
SANDBOX_MODE = False  

# Настройки
MAX_POSITIONS = 10     # Максимум сделок
ORDER_AMOUNT_USD = 100000 # Размер входа ($)

# 🚜 ФЬЮЧЕРСЫ (Торгуем Long и Short)
FUTURES_SYMBOLS = {
    "BTC/USDT:USDT": {"lev": 10},
    "ETH/USDT:USDT": {"lev": 10},
    "SOL/USDT:USDT": {"lev": 10},
    "TON/USDT:USDT": {"lev": 5},
    "DOGE/USDT:USDT": {"lev": 5},
    "PEPE/USDT:USDT": {"lev": 3},
    "STRK/USDT:USDT": {"lev": 3},
    "WIF/USDT:USDT": {"lev": 3},
    "WLD/USDT:USDT": {"lev": 3},
    "FET/USDT:USDT": {"lev": 3},
    "TIA/USDT:USDT": {"lev": 3},
    "OP/USDT:USDT": {"lev": 3},
    "ARB/USDT:USDT": {"lev": 3},
    "LINK/USDT:USDT": {"lev": 3},
    "APT/USDT:USDT": {"lev": 3},
    "SUI/USDT:USDT": {"lev": 3},
    "AVAX/USDT:USDT": {"lev": 3},
    "XRP/USDT:USDT": {"lev": 3},
    "LTC/USDT:USDT": {"lev": 3},
    "BNB/USDT:USDT": {"lev": 3},
}

SPOT_SYMBOLS = [
    "BTC": "BTC-USDT",
    "ETH": "ETH-USDT",
    "SOL": "SOL-USDT",
    "TON": "TON-USDT",
    "SUI": "SUI-USDT",
    "BNB": "BNB-USDT",
]

class TradingAgent:
    def __init__(self, bot_token, chat_id, deepseek_key):
        self.bot_token = bot_token
        self.chat_id = chat_id
        
        # DeepSeek через клиент OpenAI
        self.client = OpenAI(
            api_key=deepseek_key, 
            base_url="https://api.deepseek.com"
        )
        
        # Подключение к OKX
        try:
            self.exchange = ccxt.okx({
                'apiKey': API_KEY,
                'secret': API_SECRET,
                'password': API_PASSWORD,
                'enableRateLimit': True,
                'options': {'defaultType': 'swap'} 
            })
            if SANDBOX_MODE:
                self.exchange.set_sandbox_mode(True)
        except Exception as e:
            print(f"❌ Connect Error: {e}")

        # Память позиций
        self.positions = {name: None for name in FUTURES_SYMBOLS}
        self.spot_status = {name: None for name in SPOT_SYMBOLS}

    def send(self, text):
        import requests
        try:
            requests.post(
                f"https://api.telegram.org/bot{self.bot_token}/sendMessage", 
                json={"chat_id": self.chat_id, "text": text, "parse_mode": "Markdown"}, timeout=5
            )
        except: pass

    # --- РАБОТА С БИРЖЕЙ ---
    def get_candles(self, symbol, timeframe='15m', limit=100):
        try:
            ohlcv = self.exchange.fetch_ohlcv(symbol, timeframe, limit=limit)
            df = pd.DataFrame(ohlcv, columns=['ts', 'o', 'h', 'l', 'c', 'v'])
            return df
        except: return None

    def open_order(self, symbol, side, leverage):
        try:
            # Плечо
            try: self.exchange.set_leverage(leverage, symbol)
            except: pass
            
            # Объем
            ticker = self.exchange.fetch_ticker(symbol)
            price = ticker['last']
            amount = ORDER_AMOUNT_USD / price 
            
            # Ордер
            order = self.exchange.create_order(symbol, 'market', side, amount)
            return True, order['id']
        except Exception as e:
            return False, str(e)

    # --- 🧠 DEEPSEEK АНАЛИЗ (LONG & SHORT) ---
    def ask_ai(self, symbol, price, rsi, adx, signal_type):
        print(f"🧠 Asking DeepSeek about {symbol} ({signal_type})...")
        
        prompt = f"""
        Ты трейдер. Актив: {symbol}, Цена: {price}.
        Технический сигнал: {signal_type}.
        RSI: {rsi}, ADX: {adx}.
        
        ПРАВИЛА:
        1. Если сигнал BUY: Подтверди, если тренд вверх и RSI < 70.
        2. Если сигнал SELL: Подтверди, если тренд вниз и RSI > 30.
        3. Если ADX < 20 (флэт) -> WAIT.
        
        Верни JSON:
        Risk: [1-10]/10
        Verdict: [YES / NO]
        Reason: [Кратко]
        """

        for i in range(2):
            try:
                response = self.client.chat.completions.create(
                    model="deepseek-chat",
                    messages=[{"role": "user", "content": prompt}],
                    max_tokens=100,
                    temperature=0.0
                )
                return response.choices[0].message.content
            except: time.sleep(1)
        return "Skip"

    # --- АНАЛИЗ ФЬЮЧЕРСОВ (15m) ---
    def check_futures(self):
        print(f"--- 🚀 Checking Futures (Long/Short) ---")
        
        for symbol, info in FUTURES_SYMBOLS.items():
            lev = info["lev"]
            time.sleep(1)

            df = self.get_candles(symbol, '15m')
            if df is None: continue

            df['ema9'] = ta.ema(df['c'], length=9)
            df['ema21'] = ta.ema(df['c'], length=21)
            df['rsi'] = ta.rsi(df['c'], length=14)
            df['adx'] = ta.adx(df['h'], df['l'], df['c'])['ADX_14']
            
            curr = df.iloc[-1]
            rsi = curr['rsi']
            adx = curr['adx']

            signal = None
            side = None

            # ✅ ЛОГИКА LONG (Покупка)
            if (curr['ema9'] > curr['ema21'] and 50 < rsi < 70 and adx > 25):
                signal = "LONG_SIGNAL"
                side = "buy"

            # 🔻 ЛОГИКА SHORT (Продажа/Шорт)
            elif (curr['ema9'] < curr['ema21'] and 30 < rsi < 50 and adx > 25):
                signal = "SHORT_SIGNAL"
                side = "sell"

            # Если есть сигнал и мы не в позиции
            if signal and self.positions[symbol] != side:
                
                # Спрашиваем DeepSeek
                ai_verdict = self.ask_ai(symbol, curr['c'], round(rsi,1), round(adx,1), signal)
                
                if "NO" in ai_verdict.upper():
                    print(f"✋ AI отменил {signal} по {symbol}")
                    continue

                # Открываем сделку
                print(f"⚡ Executing {side.upper()} {symbol}...")
                success, msg = self.open_order(symbol, side, lev)
                
                if success:
                    icon = "🟢" if side == "buy" else "🔴"
                    self.send(
                        f"{icon} **FUTURES ACTION**\n"
                        f"#{symbol} — {side.upper()}\n"
                        f"💰 Amount: ${ORDER_AMOUNT_USD}\n"
                        f"⚙️ Lev: {lev}x\n"
                        f"🧠 AI: {ai_verdict}"
                    )
                    self.positions[symbol] = side
                else:
                    self.send(f"⚠️ Order Error {symbol}: {msg}")

    # --- АНАЛИЗ СПОТА (4H) ---
    def check_spot(self):
        print(f"--- 🏦 Checking Spot (Signals) ---")
        
        for symbol in SPOT_SYMBOLS:
            time.sleep(1)
            df = self.get_candles(symbol, '4H', limit=50) # Таймфрейм 4 часа
            if df is None: continue

            curr = df.iloc[-1]
            rsi = ta.rsi(df['c'], length=14).iloc[-1]
            
            # 🔵 СИГНАЛ НА ПОКУПКУ (Buy the Dip)
            if rsi < 35 and self.spot_status[symbol] != "BUY":
                self.send(
                    f"💎 **SPOT BUY SIGNAL**\n#{symbol}\n"
                    f"📉 RSI is LOW ({round(rsi,1)}) - Good entry!\n"
                    f"💰 Price: {curr['c']}"
                )
                self.spot_status[symbol] = "BUY"
            
            # 🟠 СИГНАЛ НА ПРОДАЖУ (Take Profit)
            elif rsi > 75 and self.spot_status[symbol] != "SELL":
                self.send(
                    f"💰 **SPOT SELL SIGNAL**\n#{symbol}\n"
                    f"📈 RSI is HIGH ({round(rsi,1)}) - Consider Taking Profit!\n"
                    f"💵 Price: {curr['c']}"
                )
                self.spot_status[symbol] = "SELL"

    # --- ГЛАВНЫЙ МЕТОД ---
    def analyze(self):
        self.check_futures() # Торгует сам
        self.check_spot()    # Шлет сигналы
