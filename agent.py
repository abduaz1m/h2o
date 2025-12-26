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

    # 🔥 AI МОЗГ: ОПЫТНЫЙ ТРЕЙДЕР (LONG & SHORT)
    def ask_ai(self, mode, symbol, price, rsi, adx, trend, direction):
        
        strategy_name = "CRYPTO_VETERAN_V2"
        print(f"🧠 Veteran Analyzing {symbol} ({direction})...")

        json_template = '{"Risk": int, "Verdict": "BUY" or "SELL" or "WAIT", "Reason": "text"}'
        
        # Логика для промпта в зависимости от направления
        if direction == "LONG":
            risk_context = "RSI > 70 is OVERBOUGHT (Risk). RSI < 30 is OVERSOLD (Good for bounce)."
            objective = "Find strong bullish momentum."
        else: # SHORT
            risk_context = "RSI < 30 is OVERSOLD (Risk for short). RSI > 70 is OVERBOUGHT (Good for dump)."
            objective = "Find breakdown and weakness."

        system_prompt = (
            f"Ты — опытный крипто-трейдер. Твой стиль: Price Action + VSA.\n"
            f"ЗАДАЧА: Оценить вход в {direction} позицию.\n"
            f"КОНТЕКСТ РИСКА: {risk_context}\n"
            f"ЦЕЛЬ: {objective}\n"
            f"ПРАВИЛА:\n"
            f"1. Если тренд противоречит позиции — WAIT.\n"
            f"2. Если ADX < 20 — рынок спит, WAIT.\n"
            f"3. Для LONG: опасайся сопротивлений. Для SHORT: опасайся поддержек.\n"
            f"ФОРМАТ ОТВЕТА (JSON): {json_template}"
        )

        user_prompt = (
            f"Asset: {symbol}\n"
            f"Price: {price}\n"
            f"RSI (14): {rsi}\n"
            f"ADX: {adx}\n"
            f"Trend Context: {trend}\n"
            f"Requested Setup: {direction} Signal\n"
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
                    temperature=0.3
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
        print("--- 🚀 Checking Futures (15m, 30m, 1H) ---")
        # Таймфреймы для проверки
        timeframes = ["15m", "30m", "1H"]
        
        for name, info in FUTURES_SYMBOLS.items():
            symbol = info["id"]
            lev = info["lev"]
            
            # Если уже есть позиция, пропускаем, чтобы не спамить
            if self.positions[name] is not None:
                continue

            for tf in timeframes:
                time.sleep(0.15)
                df = self.get_candles(symbol, tf)
                if df is None: continue

                df["ema_f"] = ta.ema(df["c"], length=9)
                df["ema_s"] = ta.ema(df["c"], length=21)
                df["rsi"] = ta.rsi(df["c"], length=14)
                df["atr"] = ta.atr(df["h"], df["l"], df["c"], length=14)
                df["adx"] = ta.adx(df["h"], df["l"], df["c"], length=14)["ADX_14"]
                
                curr = df.iloc[-2]
                adx_val = curr["adx"]
                rsi_val = curr["rsi"]
                price = curr["c"]

                # --- ЛОГИКА СИГНАЛОВ ---
                signal_type = None
                
                # 1. LONG SETUP
                # EMA 9 выше EMA 21, RSI в здоровой зоне (не перекуплен сильно)
                if (curr["ema_f"] > curr["ema_s"] and 
                    50 < rsi_val < 75 and 
                    adx_val > 20):
                    signal_type = "LONG"

                # 2. SHORT SETUP
                # EMA 9 ниже EMA 21, RSI в зоне для падения (не перепродан)
                elif (curr["ema_f"] < curr["ema_s"] and 
                      25 < rsi_val < 50 and 
                      adx_val > 20):
                    signal_type = "SHORT"

                if signal_type:
                    # AI подтверждение
                    ai_verdict, strategy_used = self.ask_ai("FUTURES", name, price, round(rsi_val,1), round(adx_val,1), f"{tf} Trend", signal_type)
                    
                    if "WAIT" in str(ai_verdict).upper(): continue

                    # Расчет TP/SL
                    atr_mult_sl = 2.0
                    atr_mult_tp = 3.5
                    
                    if signal_type == "LONG":
                        tp = price + (curr["atr"] * atr_mult_tp)
                        sl = price - (curr["atr"] * atr_mult_sl)
                        emoji = "🟢"
                        title = "LONG SIGNAL"
                    else:
                        tp = price - (curr["atr"] * atr_mult_tp)
                        sl = price + (curr["atr"] * atr_mult_sl)
                        emoji = "🔴"
                        title = "SHORT SIGNAL"

                    msg = (
                        f"🚀 **{title}** {emoji}\n"
                        f"#{name} — {tf}\n"
                        f"🧠 Analyst: **{strategy_used}**\n"
                        f"⚙️ Lev: {lev}x\n"
                        f"📊 ADX: {round(adx_val,1)} | RSI: {round(rsi_val,1)}\n"
                        f"💰 Entry: {price}\n🎯 TP: {round(tp,4)}\n🛑 SL: {round(sl,4)}\n"
                        f"💬 Verdict: {ai_verdict}"
                    )
                    self.send(msg)
                    self.positions[name] = signal_type # Запоминаем, что вошли
                    time.sleep(2)
                    break # Если нашли сигнал на одном ТФ, переходим к следующей монете

    # --- СПОТ (1D, 3D, 1W) ---
    def check_spot(self):
        print("--- 🏦 Checking Spot (1D, 3D, 1W) ---")
        timeframes = ["1D", "3D", "1W"]
        
        for name, symbol in SPOT_SYMBOLS.items():
            if self.spot_positions[name] == "BUY": continue

            for tf in timeframes:
                time.sleep(0.1)
                df = self.get_candles(symbol, tf, limit=100)
                if df is None: continue

                rsi = ta.rsi(df["c"], length=14).iloc[-1]
                ema200 = ta.ema(df["c"], length=200).iloc[-1]
                price = df["c"].iloc[-1]

                is_dip = False
                setup = ""

                # Логика "Купи дно"
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
                        f"🧠 Analyst: {strategy_used}\n"
                        f"💰 Price: {price}\n"
                        f"💬 Verdict: {ai_verdict}"
                    )
                    self.send(msg)
                    self.spot_positions[name] = "BUY"
                    time.sleep(2)
                    break # Нашли вход - выходим из цикла ТФ
            
            # Сброс позиции если RSI восстановился (проверяем по 1D)
            if self.spot_positions[name] == "BUY":
                 # Простая проверка для сброса флага (не продажа, просто разрешение искать новый вход)
                 pass 

    def analyze(self):
        self.check_futures()
        self.check_spot()
