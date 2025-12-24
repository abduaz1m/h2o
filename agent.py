import os
import requests
import time
import pandas as pd
import pandas_ta as ta
from datetime import datetime
from openai import OpenAI

# --- КОНФИГУРАЦИЯ ---
OKX_URL = "https://www.okx.com/api/v5/market/candles"
MAX_POSITIONS = 23

# 1. 🚜 СПИСОК ФЬЮЧЕРСОВ (Разбиты по секторам)
FUTURES_SYMBOLS = {
    # 👑 KINGS (Lev 10x)
    "BTC":    {"id": "BTC-USDT-SWAP",    "lev": 10},
    "ETH":    {"id": "ETH-USDT-SWAP",    "lev": 10},
    "SOL":    {"id": "SOL-USDT-SWAP",    "lev": 10},
    "BNB":    {"id": "BNB-USDT-SWAP",    "lev": 10},
    "LTC":    {"id": "LTC-USDT-SWAP",    "lev": 10},
    "XRP":    {"id": "XRP-USDT-SWAP",    "lev": 10},



    # 🏗 L1 (Lev 7x)
    "TON":    {"id": "TON-USDT-SWAP",    "lev": 7},
    "AVAX":   {"id": "AVAX-USDT-SWAP",   "lev": 7},
    "SUI":    {"id": "SUI-USDT-SWAP",    "lev": 7},
    "APT":    {"id": "APT-USDT-SWAP",    "lev": 7},

    # 🔗 DEFI (Lev 7x)
    "LINK":   {"id": "LINK-USDT-SWAP",   "lev": 7},
    "ARB":    {"id": "ARB-USDT-SWAP",    "lev": 7},
    "OP":     {"id": "OP-USDT-SWAP",     "lev": 7},
    "TIA":    {"id": "TIA-USDT-SWAP",    "lev": 7},

    # 🤖 AI & MEME (Lev 3x-5x)
    "FET":    {"id": "FET-USDT-SWAP",    "lev": 5},
    "WLD":    {"id": "WLD-USDT-SWAP",    "lev": 5},
    "PEPE":   {"id": "PEPE-USDT-SWAP",   "lev": 3},
    "WIF":    {"id": "WIF-USDT-SWAP",    "lev": 3},
    "DOGE":   {"id": "DOGE-USDT-SWAP",    "lev": 3},
    "STRK":   {"id": "STRK-USDT-SWAP",    "lev": 3},
}

# 2. 🏦 СПИСОК СПОТА
SPOT_SYMBOLS = {
    "BTC": "BTC-USDT",
    "ETH": "ETH-USDT",
    "SOL": "SOL-USDT",
    "TON": "TON-USDT",
    "SUI": "SUI-USDT",
    "BNB": "BNB-USDT",
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

    def send(self, text):
        try:
            requests.post(
                f"https://api.telegram.org/bot{self.bot_token}/sendMessage", 
                json={"chat_id": self.chat_id, "text": text, "parse_mode": "Markdown"}, 
                timeout=5
            )
        except: pass

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

    # 🔥 ДИНАМИЧЕСКИЙ AI МОЗГ
    def ask_ai(self, mode, symbol, price, rsi, news, adx, trend, extra_info=""):
        
        # 1. ОПРЕДЕЛЕНИЕ СТРАТЕГИИ ПО СИЛЕ ТРЕНДА (ADX)
        if mode == "SPOT":
            strategy_name = "INVESTOR (Buy the Dip)"
            system_prompt = "Ты Инвестор. Твоя цель — накопление фундаментальных активов на просадках. Ищи перепроданность."
        else:
            # Логика переключения для Фьючерсов
            if adx < 25:
                strategy_name = "🛡️ SNIPER (Conservative)"
                system_prompt = """
                Ты — Консервативный Риск-Менеджер (Strategy: SNIPER).
                Рынок слабый (ADX < 25). Твоя задача — отсеять шум.
                ПРАВИЛА:
                1. Если RSI > 65, ЗАПРЕТИ сделку (слишком рискованно во флэте).
                2. Требуй идеального подтверждения. Любое сомнение = WAIT.
                """
            elif adx > 40:
                strategy_name = "🚀 MOMENTUM (Aggressive)"
                system_prompt = """
                Ты — Агрессивный Трейдер (Strategy: MOMENTUM).
                Рынок очень сильный (ADX > 40). Игнорируй перекупленность!
                ПРАВИЛА:
                1. Если RSI высокий (даже 75), это нормально для пампа. РАЗРЕШАЙ сделку.
                2. Главное — не упустить ракету.
                """
            else:
                strategy_name = "⚖️ SMART MONEY (Balanced)"
                system_prompt = """
                Ты — Аналитик VSA (Strategy: SMART MONEY).
                Рынок в норме. Следи за объемами.
                ПРАВИЛА:
                1. Если цена растет без объема — это ловушка.
                2. Ищи баланс между риском и прибылью.
                """

        print(f"🧠 Asking DeepSeek about {symbol}...")
        
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

    # --- ФЬЮЧЕРСЫ (15m) ---
    def check_futures(self):
        print(f"--- 🚀 Checking Futures ---")
        cycle_signals = 0
        
        for name, info in FUTURES_SYMBOLS.items():
            if cycle_signals >= 3: break
            
            symbol = info["id"]
            lev = info["lev"]
            time.sleep(0.15)

            df = self.get_candles(symbol, "15m")
            if df is None: continue

            df["ema_f"] = ta.ema(df["c"], length=9)
            df["ema_s"] = ta.ema(df["c"], length=21)
            df["rsi"] = ta.rsi(df["c"], length=14)
            df["atr"] = ta.atr(df["h"], df["l"], df["c"], length=14)
            df["adx"] = ta.adx(df["h"], df["l"], df["c"], length=14)["ADX_14"]
            
            curr = df.iloc[-2]
            adx_val = curr["adx"]

            # Базовый тех. сигнал (Cross)
            # В "MOMENTUM" режиме мы допускаем более высокий RSI для входа
            rsi_limit = 75 if adx_val > 40 else 70

            signal = None
            if (curr["ema_f"] > curr["ema_s"] and 
                50 < curr["rsi"] < rsi_limit and 
                adx_val > 20):
                signal = "BUY"

            if signal and self.positions[name] != signal:
                
                # Фильтр 1D
                d_df = self.get_candles(symbol, "1D", limit=50)
                if d_df is not None:
                    ema20_d = ta.ema(d_df["c"], length=20).iloc[-1]
                    if curr["c"] < ema20_d: continue 

                # AI Check (Dynamic)
                ai_verdict, strategy_used = self.ask_ai("FUTURES", name, curr["c"], round(curr["rsi"],1), round(adx_val,1), "UP (15m)")
                
                if "WAIT" in ai_verdict.upper(): continue

                tp = curr["c"] + (curr["atr"] * 3.5)
                sl = curr["c"] - (curr["atr"] * 2.0)

                self.send(
                    f"🚀 **LONG SIGNAL**\n#{name} — BUY 🟢\n"
                    f"🧠 Strat: **{strategy_used}**\n"
                    f"⚙️ Lev: {lev}x\n"
                    f"📊 ADX: {round(adx_val,1)}\n"
                    f"💰 Entry: {curr['c']}\n🎯 TP: {round(tp,4)}\n🛑 SL: {round(sl,4)}\n"
                    f"🤖 AI: {ai_verdict}"
                )
                self.positions[name] = signal
                cycle_signals += 1
                time.sleep(2)

    # --- СПОТ (4H) ---
    def check_spot(self):
        print(f"--- 🏦 Checking Spot ---")
        for name, symbol in SPOT_SYMBOLS.items():
            time.sleep(0.1)
            df = self.get_candles(symbol, "4H", limit=200)
            if df is None: continue

            rsi = ta.rsi(df["c"], length=14).iloc[-1]
            ema200 = ta.ema(df["c"], length=200).iloc[-1]
            price = df["c"].iloc[-1]

            is_dip = False
            setup = ""

            if price > ema200 and rsi < 40:
                is_dip = True
                setup = "Trend Pullback"
            elif rsi < 30:
                is_dip = True
                setup = "Oversold Bounce"

            if is_dip and self.spot_positions[name] != "BUY":
                # Для спота ADX не так важен, передаем 0
                ai_verdict, strategy_used = self.ask_ai("SPOT", name, price, round(rsi,1), 0, setup)
                
                self.send(
                    f"💎 **SPOT INVEST**\n#{name} — ACCUMULATE 🔵\n"
                    f"📉 RSI: {round(rsi, 1)}\n"
                    f"🧠 Strat: {strategy_used}\n"
                    f"💰 Price: {price}\n"
                    f"🤖 AI: {ai_verdict}"
                )
                self.spot_positions[name] = "BUY"
                time.sleep(2)
            
            elif rsi > 55:
                self.spot_positions[name] = None

    def analyze(self):
        self.check_futures()
        self.check_spot()
