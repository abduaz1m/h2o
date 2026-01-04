import os
import requests
import time
import pandas as pd
import pandas_ta as ta
from openai import OpenAI

# --- КОНФИГУРАЦИЯ ---
OKX_URL = "https://www.okx.com/api/v5/market/candles"

# 1. 🚜 СПИСОК ФЬЮЧЕРСОВ
FUTURES_SYMBOLS = {
    "BTC":    {"id": "BTC-USDT-SWAP",    "lev": 10},
    "ETH":    {"id": "ETH-USDT-SWAP",    "lev": 10},
    "SOL":    {"id": "SOL-USDT-SWAP",    "lev": 10},
    "BNB":    {"id": "BNB-USDT-SWAP",    "lev": 10},
    "TON":    {"id": "TON-USDT-SWAP",    "lev": 7},
    "AVAX":   {"id": "AVAX-USDT-SWAP",   "lev": 7},
    "SUI":    {"id": "SUI-USDT-SWAP",    "lev": 7},
    "APT":    {"id": "APT-USDT-SWAP",    "lev": 7},
    "LINK":   {"id": "LINK-USDT-SWAP",   "lev": 7},
    "ARB":    {"id": "ARB-USDT-SWAP",    "lev": 7},
    "OP":     {"id": "OP-USDT-SWAP",     "lev": 7},
    "TIA":    {"id": "TIA-USDT-SWAP",    "lev": 7},
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
        # Подключение к DeepSeek
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
        except Exception:
            pass

    def get_candles(self, symbol, bar, limit=100):
        try:
            r = requests.get(OKX_URL, params={"instId": symbol, "bar": bar, "limit": limit}, timeout=10)
            data = r.json().get("data", [])
            if not data: return None
            df = pd.DataFrame(data, columns=["ts", "o", "h", "l", "c", "v", "volCcy", "volCcyQuote", "confirm"])
            df = df.iloc[::-1].reset_index(drop=True)
            df[["o", "h", "l", "c", "v"]] = df[["o", "h", "l", "c", "v"]].astype(float)
            return df
        except Exception:
            return None

    # 🔥 AI: СТРАТЕГИЯ "EARLY ENTRY" (РАННИЙ ВХОД)
    def ask_ai(self, mode, symbol, price, rsi, adx, trend, direction):
        strategy_name = "VETERAN_EARLY_ENTRY"
        
        print(f"🧠 Checking Early Entry for {symbol} ({direction})...")

        json_template = '{"Risk": int, "Verdict": "BUY" or "SELL" or "WAIT", "Reason": "text"}'
        
        if direction == "LONG":
            objective = "Catch the start of the pump (Breakout or Reversal)."
            warning = "DO NOT BUY if RSI > 70 (Too late)."
        else:
            objective = "Catch the start of the dump."
            warning = "DO NOT SHORT if RSI < 30 (Too late)."

        system_prompt = (
            f"Ты — скальпер-профессионал. Твоя задача — найти точку входа В НАЧАЛЕ движения.\n"
            f"НАПРАВЛЕНИЕ: {direction}\n"
            f"ЦЕЛЬ: {objective}\n"
            f"ВАЖНО: {warning}\n"
            f"ПРАВИЛА:\n"
            f"1. Если цена уже улетела далеко от средних — WAIT (поздно).\n"
            f"2. Если ADX < 15 — флэт, опасно, WAIT.\n"
            f"3. Твой вердикт должен быть жестким. Если есть сомнения — WAIT.\n"
            f"ФОРМАТ ОТВЕТА (JSON): {json_template}"
        )

        user_prompt = (
            f"Asset: {symbol}\n"
            f"Price: {price}\n"
            f"RSI (14): {rsi}\n"
            f"ADX: {adx}\n"
            f"Structure: {trend}\n"
            f"Setup: Price crossed EMA aggressive.\n"
        )

        for i in range(2):
            try:
                response = self.client.chat.completions.create(
                    model="deepseek-chat",
                    messages=[
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": user_prompt}
                    ],
                    max_tokens=200,
                    temperature=0.2
                )
                content = response.choices[0].message.content
                content = content.replace("```json", "").replace("```", "").strip()
                return content, strategy_name
            except Exception:
                time.sleep(1)
                continue
        
        return "Skip", strategy_name

    # --- ФЬЮЧЕРСЫ (15m, 30m, 1H) ---
    def check_futures(self):
        print("--- 🚀 Checking Futures (Smart Price Action) ---")
        timeframes = ["15m", "30m", "1H"]
        
        for name, info in FUTURES_SYMBOLS.items():
            symbol = info["id"]
            lev = info["lev"]
            
            if self.positions[name] is not None:
                continue

            for tf in timeframes:
                time.sleep(0.15)
                # Берем чуть больше свечей для EMA 50
                df = self.get_candles(symbol, tf, limit=100)
                if df is None or len(df) < 60: continue

                # ИНДИКАТОРЫ
                df["ema_fast"] = ta.ema(df["c"], length=9)   # Быстрая линия (Триггер)
                df["ema_trend"] = ta.ema(df["c"], length=50) # Глобальный тренд (Фильтр)
                df["rsi"] = ta.rsi(df["c"], length=14)
                df["atr"] = ta.atr(df["h"], df["l"], df["c"], length=14)
                try:
                    df["adx"] = ta.adx(df["h"], df["l"], df["c"], length=14)["ADX_14"]
                except: continue
                
                # Текущая и предыдущая свеча
                curr = df.iloc[-1] # Текущая (закрытая или последняя обновленная)
                prev = df.iloc[-2] # Предыдущая (для проверки пересечения)

                adx_val = curr["adx"]
                rsi_val = curr["rsi"]
                price = curr["c"]

                if pd.isna(curr["ema_trend"]) or pd.isna(rsi_val): continue

                signal_type = None
                
                # --- НОВАЯ ЛОГИКА (БЕЗ ЗАПАЗДЫВАНИЯ) ---
                
                # 1. LONG SETUP:
                # Глобальный тренд вверх (Цена > EMA 50)
                # Локальный откат закончился: Цена пересекла EMA 9 снизу вверх
                if (price > curr["ema_trend"] and          # Тренд UP
                    prev["c"] < prev["ema_fast"] and       # Вчера были ниже EMA 9
                    curr["c"] > curr["ema_fast"] and       # Сегодня пробили EMA 9 вверх
                    40 < rsi_val < 68 and                  # RSI здоровый (не перекуплен > 70)
                    adx_val > 15):                         # Есть хоть какая-то волатильность
                    signal_type = "LONG"

                # 2. SHORT SETUP:
                # Глобальный тренд вниз (Цена < EMA 50)
                # Локальный отскок закончился: Цена пересекла EMA 9 сверху вниз
                elif (price < curr["ema_trend"] and        # Тренд DOWN
                      prev["c"] > prev["ema_fast"] and     # Вчера были выше EMA 9
                      curr["c"] < curr["ema_fast"] and     # Сегодня пробили EMA 9 вниз
                      32 < rsi_val < 60 and                # RSI здоровый (не перепродан < 30)
                      adx_val > 15):
                    signal_type = "SHORT"

                if signal_type:
                    # AI Filter
                    ai_verdict, strategy_used = self.ask_ai("FUTURES", name, price, round(rsi_val,1), round(adx_val,1), f"{tf} Trend Breakout", signal_type)
                    
                    if "WAIT" in str(ai_verdict).upper(): continue

                    # Умные стопы (короче, чем раньше)
                    atr_mult_sl = 1.5 # Короткий стоп
                    atr_mult_tp = 6.0 # Длинный тейк
                    
                    if signal_type == "LONG":
                        tp = price + (curr["atr"] * atr_mult_tp)
                        sl = price - (curr["atr"] * atr_mult_sl)
                        emoji = "🟢"
                        title = "FAST LONG"
                    else:
                        tp = price - (curr["atr"] * atr_mult_tp)
                        sl = price + (curr["atr"] * atr_mult_sl)
                        emoji = "🔴"
                        title = "FAST SHORT"

                    msg = (
                        f"⚡ **{title}** {emoji}\n"
                        f"#{name} — {tf}\n"
                        f"🧠 Strat: **{strategy_used}**\n"
                        f"⚙️ Lev: {lev}x\n"
                        f"📊 RSI: {round(rsi_val,1)} (OK zone)\n"
                        f"💰 Entry: {price}\n🎯 TP: {round(tp,4)}\n🛑 SL: {round(sl,4)}\n"
                        f"💬 AI: {ai_verdict}"
                    )
                    self.send(msg)
                    self.positions[name] = signal_type 
                    time.sleep(2)
                    break 

    # --- СПОТ (1D, 3D, 1W) ---
    def check_spot(self):
        print("--- 🏦 Checking Spot (Dip Hunting) ---")
        timeframes = ["1D", "3D", "1W"]
        
        for name, symbol in SPOT_SYMBOLS.items():
            if self.spot_positions[name] == "BUY": continue

            for tf in timeframes:
                time.sleep(0.1)
                df = self.get_candles(symbol, tf, limit=300)
                if df is None or len(df) < 205: continue

                try:
                    rsi = ta.rsi(df["c"], length=14).iloc[-1]
                    ema200 = ta.ema(df["c"], length=200).iloc[-1]
                    price = df["c"].iloc[-1]
                    if pd.isna(ema200): continue
                except: continue

                is_dip = False
                setup = ""

                # Спот логика остается "покупкой дна", тут спешка не нужна
                if price > ema200 and rsi < 40:
                    is_dip = True
                    setup = f"Trend Pullback ({tf})"
                elif rsi < 30:
                    is_dip = True
                    setup = f"Oversold Bounce ({tf})"

                if is_dip:
                    ai_verdict, strategy_used = self.ask_ai("SPOT", name, price, round(rsi,1), 0, setup, "LONG")
                    
                    msg = (
                        f"💎 **SPOT INVEST**\n#{name} — {tf} 🔵\n"
                        f"📉 RSI: {round(rsi, 1)}\n"
                        f"🧠 Strat: {strategy_used}\n"
                        f"💰 Price: {price}\n"
                        f"💬 AI: {ai_verdict}"
                    )
                    self.send(msg)
                    self.spot_positions[name] = "BUY"
                    time.sleep(2)
                    break 
            
            if self.spot_positions[name] == "BUY":
                 pass 

    def analyze(self):
        self.check_futures()
        self.check_spot()
