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
    def __init__(self, bot_token, chat_id, openai_key):
        self.bot_token = bot_token
        self.chat_id = chat_id
        # Подключение к DeepSeek (или OpenAI с совместимым endpoint)
        self.client = OpenAI(api_key=openai_key, base_url="https://api.deepseek.com")
        self.positions = {name: None for name in FUTURES_SYMBOLS}
        self.spot_positions = {name: None for name in SPOT_SYMBOLS}

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

    # 🔥 АДАПТИРОВАННЫЙ ПОД DEEPSEEK МОЗГ
    def ask_ai(self, mode, symbol, price, rsi, adx, trend, extra_info=""):
        
        # 1. СТРУКТУРИРОВАННАЯ ЛОГИКА (БЕЗ ЛИШНЕЙ "ПРОЗЫ")
        if mode == "SPOT":
            strategy_name = "INVESTOR_DIP"
            rules_block = """
            - GOAL: Accumulate assets during oversold conditions.
            - RSI < 30: STRONG BUY signal.
            - RSI < 40 + Uptrend: MODERATE BUY.
            - RSI > 50: WAIT (No signal).
            """
        else:
            # Futures Logic
            if adx < 25:
                strategy_name = "SNIPER_CONSERVATIVE"
                rules_block = """
                - MARKET STATE: Choppy / Weak Trend (ADX < 25).
                - CONSTRAINT: FALSE SIGNALS HIGH.
                - RULE 1: IF RSI > 65 THEN VERDICT = WAIT (Risk of reversal).
                - RULE 2: STRICTLY FILTER NOISE. Confirm entry only if indicators align perfectly.
                """
            elif adx > 40:
                strategy_name = "MOMENTUM_AGGRESSIVE"
                rules_block = """
                - MARKET STATE: Strong Trend / Pump (ADX > 40).
                - CONSTRAINT: IGNORE OVERSOLD/OVERBOUGHT.
                - RULE 1: High RSI (70-80) is ACCEPTABLE for continuation.
                - RULE 2: DO NOT counter-trend. Follow the momentum.
                """
            else:
                strategy_name = "SMART_MONEY_BALANCED"
                rules_block = """
                - MARKET STATE: Normal Volatility.
                - ANALYSIS: Check Volume Spread Analysis logic implicitly.
                - RULE 1: Avoid buying into resistance.
                - RULE 2: Balance Risk/Reward ratio.
                """

        print(f"🧠 DeepSeek analyzing {symbol} [{strategy_name}]...")

        # 2. ПРОМПТ В СТИЛЕ "DATA ANALYST"
        system_prompt = f"""### ROLE
Senior Quantitative Analyst.

### OBJECTIVE
Analyze the provided market data and output a trading decision based on strict algorithmic rules.

### STRATEGY PARAMETERS: {strategy_name}
{rules_block}

### OUTPUT FORMAT
Provide the response in strict JSON format ONLY:
{{
  "Risk": int, // Risk level 1-10 (1=Safe, 10=Extreme Risk)
  "Verdict": "BUY" or "WAIT",
  "Reason": "Concise technical explanation (max 15 words)"
}}
"""

        user_prompt = f"""
        ### MARKET DATA
        Asset: {symbol}
        Price: {price}
        RSI (14): {rsi}
        ADX (14): {adx}
        Trend Context: {trend}
        Additional Setup: {extra_info}

        ### INSTRUCTION
        Evaluate data against the Strategy Parameters. Return JSON.
        """

        for i in range(2):
            try:
                response = self.client.chat.completions.create(
                    model="deepseek-chat",
                    messages=[
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": user_prompt}
                    ],
                    max_tokens=200, # DeepSeek может быть чуть многословнее в рассуждениях, даем запас
                    temperature=0.2 # Снижаем температуру для четкости
                )
                
                content = response.choices[0].message.content
                # Очистка от возможных markdown блоков ```json ... ```
                content = content.replace("```json", "").replace("```", "").strip()
                
                return content, strategy_name
            except Exception as e:
                if "429" in str(e) or "500" in str(e): 
                    time.sleep(2); continue
                return "AI Error", strategy_name
        return "Skip", strategy_name

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

            rsi_limit = 75 if adx_val > 40 else 70

            signal = None
            if (curr["ema_f"] > curr["ema_s"] and 
                50 < curr["rsi"] < rsi_limit and 
                adx_val > 20):
                signal = "BUY"

            if signal and self.positions[name] != signal:
                
                d_df = self.get_candles(symbol, "1D", limit=50)
                if d_df is not None:
                    ema20_d = ta.ema(d_df["c"], length=20).iloc[-1]
                    if curr["c"] < ema20_d: continue 

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
