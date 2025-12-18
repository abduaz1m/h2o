import os
import requests
import time
import pandas as pd
import pandas_ta as ta
from datetime import datetime
from openai import OpenAI

# --- КОНФИГУРАЦИЯ ---
OKX_URL = "https://www.okx.com/api/v5/market/candles"
MAX_POSITIONS = 23  # ⛔ Максимум 5 активных сделок на фьючерсах одновременно

# 1. 🚜 СПИСОК ФЬЮЧЕРСОВ (Разбиты по секторам для диверсификации)
FUTURES_SYMBOLS = {
    # --- 👑 KINGS (Low Risk, Lev 10x) ---
    "BTC":    {"id": "BTC-USDT-SWAP",    "lev": 10},
    "ETH":    {"id": "ETH-USDT-SWAP",    "lev": 10},
    "SOL":    {"id": "SOL-USDT-SWAP",    "lev": 10},
    "BNB":    {"id": "BNB-USDT-SWAP",    "lev": 10},

    # --- 🏗 L1 BLOCKCHAINS (Med Risk, Lev 7x) ---
    "TON":    {"id": "TON-USDT-SWAP",    "lev": 7},
    "AVAX":   {"id": "AVAX-USDT-SWAP",   "lev": 7}, # Avalanche
    "ADA":    {"id": "ADA-USDT-SWAP",    "lev": 7}, # Cardano
    "NEAR":   {"id": "NEAR-USDT-SWAP",   "lev": 7},
    "SUI":    {"id": "SUI-USDT-SWAP",    "lev": 7},
    "APT":    {"id": "APT-USDT-SWAP",    "lev": 7},
    "DOT":    {"id": "DOT-USDT-SWAP",    "lev": 7}, # Polkadot

    # --- 🔗 DEFI & INFRA (Med Risk, Lev 7x) ---
    "LINK":   {"id": "LINK-USDT-SWAP",   "lev": 7}, # Oracle
    "UNI":    {"id": "UNI-USDT-SWAP",    "lev": 7},
    "ARB":    {"id": "ARB-USDT-SWAP",    "lev": 7},
    "OP":     {"id": "OP-USDT-SWAP",     "lev": 7},
    "TIA":    {"id": "TIA-USDT-SWAP",    "lev": 7},

    # --- 🤖 AI & RWA (Trend Risk, Lev 5x) ---
    "FET":    {"id": "FET-USDT-SWAP",    "lev": 5}, # AI Leader
    "RENDER": {"id": "RENDER-USDT-SWAP", "lev": 5}, # AI GPU
    "WLD":    {"id": "WLD-USDT-SWAP",    "lev": 5}, # Worldcoin (Volatile)
    "ONDO":   {"id": "ONDO-USDT-SWAP",   "lev": 5}, # RWA Leader

    # --- 🚀 TOP MEMES (High Risk, Lev 3x-5x) ---
    "DOGE":   {"id": "DOGE-USDT-SWAP",   "lev": 5}, # King Meme
    "PEPE":   {"id": "PEPE-USDT-SWAP",   "lev": 3}, # Осторожно!
    "WIF":    {"id": "WIF-USDT-SWAP",    "lev": 3}, # Solana Meme
}

# 2. 🏦 СПИСОК СПОТА (Инвестиции в фундамент)
SPOT_SYMBOLS = {
    "BTC": "BTC-USDT",
    "ETH": "ETH-USDT",
    "SOL": "SOL-USDT",
    "SUI": "SUI-USDT",
    "ASTR": "ASTR-USDT", # Astar
    "TON": "TON-USDT",
}

class TradingAgent:
    def __init__(self, bot_token, chat_id, openai_key):
        self.bot_token = bot_token
        self.chat_id = chat_id
        self.client = OpenAI(api_key=openai_key)
        
        # Память сигналов
        self.positions = {name: None for name in FUTURES_SYMBOLS}
        self.spot_positions = {name: None for name in SPOT_SYMBOLS}
        
        # Счетчик активных сделок (упрощенная модель)
        self.active_trade_count = 0

    # --- ОТПРАВКА ---
    def send(self, text):
        url = f"https://api.telegram.org/bot{self.bot_token}/sendMessage"
        try:
            requests.post(url, json={"chat_id": self.chat_id, "text": text, "parse_mode": "Markdown"}, timeout=5)
        except: pass

    # --- ПОЛУЧЕНИЕ СВЕЧЕЙ ---
    def get_candles(self, symbol, bar, limit=100):
        try:
            r = requests.get(OKX_URL, params={"instId": symbol, "bar": bar, "limit": limit}, timeout=10)
            data = r.json().get("data", [])
            if not data: return None
            df = pd.DataFrame(data, columns=["ts", "o", "h", "l", "c", "v", "volCcy", "volCcyQuote", "confirm"])
            df = df.iloc[::-1].reset_index(drop=True)
            df[["o", "h", "l", "c", "v"]] = df[["o", "h", "l", "c", "v"]].astype(float)
            return df
        except: return None

    # --- AI АНАЛИЗАТОР ---
    def ask_ai(self, mode, symbol, price, rsi, trend, extra_info=""):
        print(f"🧠 AI analyzing {symbol} ({mode})...")
        
        if mode == "FUTURES":
            role = "Трейдер. Стратегия: ONLY LONG. Ищи сильный моментум."
            task = "Оцени силу бычьего импульса."
        else:
            role = "Инвестор. Стратегия: Buy the Dip."
            task = "Оцени, достаточно ли актив дешев для покупки."

        prompt = f"""
        Роль: {role}
        Актив: {symbol}
        Цена: {price}
        RSI: {rsi}
        Тренд: {trend}
        Инфо: {extra_info}
        
        Ответ JSON текст:
        Risk: [1-10]/10
        Verdict: [BUY / WAIT]
        Reason: [Макс 10 слов]
        """
        for i in range(2): # Уменьшил попытки до 2 для скорости
            try:
                response = self.client.chat.completions.create(
                    model="gpt-4o-mini",
                    messages=[{"role": "user", "content": prompt}],
                    max_tokens=100
                )
                return response.choices[0].message.content
            except Exception as e:
                if "429" in str(e): time.sleep(2); continue
                return "AI Error"
        return "Skip"

    # ==========================================
    # 🚀 ЛОГИКА 1: ФЬЮЧЕРСЫ (15m)
    # ==========================================
    def check_futures(self):
        print(f"--- 🚀 Checking {len(FUTURES_SYMBOLS)} Futures ---")
        
        # Сброс счетчика (в реальном боте нужно проверять баланс биржи, тут эмуляция)
        # Мы просто не даем спамить сигналами в один цикл
        cycle_signals = 0 

        for name, info in FUTURES_SYMBOLS.items():
            if cycle_signals >= 3: # Не более 3 сигналов за один проход цикла
                break

            symbol = info["id"]
            lev = info["lev"]
            time.sleep(0.15) # Чуть увеличили задержку (много монет)

            df = self.get_candles(symbol, "15m")
            if df is None: continue

            # Индикаторы
            df["ema_f"] = ta.ema(df["c"], length=9)
            df["ema_s"] = ta.ema(df["c"], length=21)
            df["rsi"] = ta.rsi(df["c"], length=14)
            df["atr"] = ta.atr(df["h"], df["l"], df["c"], length=14)
            df["adx"] = ta.adx(df["h"], df["l"], df["c"], length=14)["ADX_14"]
            
            curr = df.iloc[-2]

            # LONG ONLY STRATEGY
            signal = None
            # 1. Быстрое пересечение вверх
            # 2. RSI в рабочей зоне (не перегрет)
            # 3. ADX > 20 (есть тренд)
            if (curr["ema_f"] > curr["ema_s"] and 
                50 < curr["rsi"] < 70 and 
                curr["adx"] > 20):
                signal = "BUY"

            if signal and self.positions[name] != signal:
                
                # Фильтр Дневки (1D)
                d_df = self.get_candles(symbol, "1D", limit=50)
                if d_df is not None:
                    ema20_d = ta.ema(d_df["c"], length=20).iloc[-1]
                    if curr["c"] < ema20_d: continue # Цена ниже средней за месяц -> ТРЕНД НИСХОДЯЩИЙ -> SKIP

                # AI Check
                ai_verdict = self.ask_ai("FUTURES", name, curr["c"], round(curr["rsi"],1), "UP (15m)", f"ADX: {round(curr['adx'],1)}")
                if "WAIT" in ai_verdict.upper(): continue

                # TP/SL Setup
                tp = curr["c"] + (curr["atr"] * 3.5)
                sl = curr["c"] - (curr["atr"] * 2.0)

                self.send(
                    f"🚀 **LONG SIGNAL**\n#{name} — BUY 🟢\n⚙️ Lev: {lev}x\n"
                    f"💰 Entry: {curr['c']}\n🎯 TP: {round(tp,4)}\n🛑 SL: {round(sl,4)}\n"
                    f"📊 ADX: {round(curr['adx'],1)}\n"
                    f"🧠 AI: {ai_verdict}"
                )
                self.positions[name] = signal
                cycle_signals += 1
                time.sleep(2)

    # ==========================================
    # 🏦 ЛОГИКА 2: СПОТ (4H)
    # ==========================================
    def check_spot(self):
        print(f"--- 🏦 Checking Spot ---")
        for name, symbol in SPOT_SYMBOLS.items():
            time.sleep(0.1)
            df = self.get_candles(symbol, "4H", limit=200)
            if df is None: continue

            rsi = ta.rsi(df["c"], length=14).iloc[-1]
            ema200 = ta.ema(df["c"], length=200).iloc[-1]
            price = df["c"].iloc[-1]

            # Ловим просадки на растущем рынке
            is_dip = False
            setup = ""

            if price > ema200 and rsi < 40:
                is_dip = True
                setup = "Trend Pullback"
            elif rsi < 30:
                is_dip = True
                setup = "Oversold Bounce"

            if is_dip and self.spot_positions[name] != "BUY":
                ai_verdict = self.ask_ai("SPOT", name, price, round(rsi,1), setup, "4H Timeframe")
                
                self.send(
                    f"💎 **SPOT INVEST**\n#{name} — ACCUMULATE 🔵\n"
                    f"📉 RSI: {round(rsi, 1)}\n📊 Setup: {setup}\n"
                    f"💰 Price: {price}\n"
                    f"🧠 AI: {ai_verdict}"
                )
                self.spot_positions[name] = "BUY"
                time.sleep(2)
            
            elif rsi > 55:
                self.spot_positions[name] = None

    # MAIN LOOP
    def analyze(self):
        self.check_futures()
        self.check_spot()
