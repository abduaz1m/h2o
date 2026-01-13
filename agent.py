import os
import requests
import time
import pandas as pd
import pandas_ta as ta
from openai import OpenAI

# --- КОНФИГУРАЦИЯ ---
OKX_URL = "https://www.okx.com/api/v5/market/candles"

# 1. 🚜 СПИСОК ФЬЮЧЕРСОВ (Только Ликвидные Мажоры для Скальпинга)
FUTURES_SYMBOLS = {
    "BTC":    {"id": "BTC-USDT-SWAP",    "lev": 20}, # Плечо 20x
    "ETH":    {"id": "ETH-USDT-SWAP",    "lev": 20},
    "SOL":    {"id": "SOL-USDT-SWAP",    "lev": 20},
    "AVAX":   {"id": "AVAX-USDT-SWAP",   "lev": 20},
    "TON":    {"id": "TON-USDT-SWAP",    "lev": 20},
    "BNB":    {"id": "BNB-USDT-SWAP",    "lev": 20},
    "SUI":    {"id": "SUI-USDT-SWAP",    "lev": 20},
    "WLD":    {"id": "WLD-USDT-SWAP",    "lev": 20},
    "RENDER": {"id": "RENDER-USDT-SWAP", "lev": 20},
    "LIT":    {"id": "LIT-USDT-SWAP",    "lev": 20},
    "ZEC":    {"id": "ZEC-USDT-SWAP",    "lev": 20},
    "LAB":    {"id": "LAB-USDT-SWAP",    "lev": 20},# Плечо 20x
}

# 2. 🏦 СПИСОК СПОТА
SPOT_SYMBOLS = {
    "BTC": "BTC-USDT",
    "ETH": "ETH-USDT",
}

class TradingAgent:
    def __init__(self, bot_token, chat_id, openai_key):
        self.bot_token = bot_token
        self.chat_id = chat_id
        # Подключаем DeepSeek
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

    # 🔥 ПРОМПТ ДЛЯ СКАЛЬПИНГА (SCALPING AGENT)
    def ask_ai(self, mode, symbol, price, rsi, adx, trend, direction):
        strategy_name = "SCALP_ALGO_V1"
        
        print(f"⚡ Scalper analyzing {symbol} ({direction})...")

        # Формат ответа строго JSON
        json_template = '{"Confidence": int (0-100), "Verdict": "BUY" or "SELL" or "WAIT", "Reason": "Brief trigger explanation"}'
        
        # СИСТЕМНЫЙ ПРОМПТ
        system_prompt = (
            f"Ты — Высокочастотный Скальпинг-Алгоритм (HFT Scalper).\n"
            f"Твоя цель: Забирать короткие движения (0.5% - 1.5%) с высокой точностью.\n"
            f"Твой враг: Сомнения и передерживание позиций.\n\n"
            f"РЫНОЧНЫЕ УСЛОВИЯ:\n"
            f"- Актив: {symbol}\n"
            f"- Паттерн: {direction}\n"
            f"- RSI (14): {rsi}\n"
            f"- ADX (14): {adx} (Сила тренда)\n\n"
            f"ПРАВИЛА ПРИНЯТИЯ РЕШЕНИЙ:\n"
            f"1. ИМПУЛЬС (Momentum): Если ADX > 25, тренд сильный. Игнорируй перекупленность RSI (до 80), торгуй ПО тренду.\n"
            f"2. ОТСКОК (Reversion): Если RSI < 25 (экстремально низко) -> Входи в LONG на отскок.\n"
            f"3. ПРОБОЙ (Breakout): Если цена пробила EMA на объеме (Trend UP) -> BUY.\n"
            f"4. ФИЛЬТР: Если ADX < 15 (рынок спит) -> WAIT.\n"
            f"ФОРМАТ ОТВЕТА (JSON): {json_template}"
        )

        user_prompt = (
            f"Setup Detected: {direction}\n"
            f"Current Price: {price}\n"
            f"Action required immediately."
        )

        for i in range(2):
            try:
                response = self.client.chat.completions.create(
                    model="deepseek-chat",
                    messages=[
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": user_prompt}
                    ],
                    max_tokens=150,
                    temperature=0.1 # Минимум фантазии, максимум логики
                )
                content = response.choices[0].message.content
                content = content.replace("```json", "").replace("```", "").strip()
                return content, strategy_name
            except Exception:
                time.sleep(1)
                continue
        
        return "Skip", strategy_name

    # --- ФЬЮЧЕРСЫ (15m и 5m для скальпинга) ---
    def check_futures(self):
        print("--- ⚡ Checking Futures (Scalping Mode) ---")
        # Скальперы смотрят 15m для фона и 5m для входа (но API OKX лимитирован, оставим 15m как базу)
        timeframes = ["15m"] 
        
        for name, info in FUTURES_SYMBOLS.items():
            symbol = info["id"]
            lev = info["lev"]
            
            if self.positions[name] is not None:
                continue

            for tf in timeframes:
                time.sleep(0.15)
                df = self.get_candles(symbol, tf, limit=100)
                if df is None or len(df) < 50: continue

                df["ema_f"] = ta.ema(df["c"], length=9)
                df["ema_s"] = ta.ema(df["c"], length=21)
                df["rsi"] = ta.rsi(df["c"], length=14)
                df["atr"] = ta.atr(df["h"], df["l"], df["c"], length=14)
                try:
                    df["adx"] = ta.adx(df["h"], df["l"], df["c"], length=14)["ADX_14"]
                except: continue
                
                curr = df.iloc[-1]
                adx_val = curr["adx"]
                rsi_val = curr["rsi"]
                price = curr["c"]

                if pd.isna(rsi_val): continue

                signal_type = None
                
                # --- СКАЛЬПИНГ СЕТАПЫ ---
                
                # 1. SCALP LONG (Тренд)
                # Быстрая средняя выше медленной, RSI не перегрет (>85)
                if (curr["ema_f"] > curr["ema_s"] and rsi_val < 82):
                    signal_type = "SCALP_LONG"
                
                # 2. SCALP REVERSAL (Отскок от дна)
                # RSI упал ниже 28 - ловим нож
                elif (rsi_val < 28): 
                    signal_type = "KNIFE_CATCH_LONG"

                # 3. SCALP SHORT (Тренд вниз)
                elif (curr["ema_f"] < curr["ema_s"] and rsi_val > 18):
                    signal_type = "SCALP_SHORT"

                if signal_type:
                    ai_verdict, strategy_used = self.ask_ai(
                        "FUTURES", name, price, round(rsi_val,1), round(adx_val,1), 
                        f"{tf} timeframe", signal_type
                    )
                    
                    verdict_up = str(ai_verdict).upper()
                    if "WAIT" in verdict_up or "SKIP" in verdict_up: 
                        continue

                    # ТЕЙКИ И СТОПЫ (Короткие, скальперские)
                    # TP: 2.5 ATR (быстрый профит)
                    # SL: 1.5 ATR (жесткий стоп)
                    atr_mult_tp = 2.5 
                    atr_mult_sl = 1.5
                    
                    if "LONG" in signal_type:
                        tp = price + (curr["atr"] * atr_mult_tp)
                        sl = price - (curr["atr"] * atr_mult_sl)
                        emoji = "🟢"
                    else:
                        tp = price - (curr["atr"] * atr_mult_tp)
                        sl = price + (curr["atr"] * atr_mult_sl)
                        emoji = "🔴"

                    msg = (
                        f"⚡ **SCALP SIGNAL: {signal_type}** {emoji}\n"
                        f"#{name} — {tf}\n"
                        f"🧠 AI: **{strategy_used}**\n"
                        f"⚙️ Lev: {lev}x\n"
                        f"📊 RSI: {round(rsi_val,1)} | ADX: {round(adx_val,1)}\n"
                        f"💰 Entry: {price}\n🎯 TP: {round(tp,2)}\n🛑 SL: {round(sl,2)}\n"
                        f"📝 Verdict: {ai_verdict}"
                    )
                    self.send(msg)
                    self.positions[name] = signal_type 
                    time.sleep(2)
                    break 

    # --- СПОТ (Только накопление) ---
    def check_spot(self):
        print("--- 🏦 Spot Check ---")
        for name, symbol in SPOT_SYMBOLS.items():
            if self.spot_positions[name] == "BUY": continue
            time.sleep(0.1)
            df = self.get_candles(symbol, "4H", limit=100)
            if df is None: continue
            rsi = ta.rsi(df["c"], length=14).iloc[-1]
            price = df["c"].iloc[-1]

            if rsi < 35: # Только сильные просадки
                ai_verdict, _ = self.ask_ai("SPOT", name, price, round(rsi,1), 0, "DIP", "ACCUMULATE")
                if "BUY" in str(ai_verdict).upper():
                    self.send(f"🏦 **SPOT BUY**\n#{name} @ {price}\n📉 RSI: {rsi}")
                    self.spot_positions[name] = "BUY"
                    time.sleep(2)

    def analyze(self):
        self.check_futures()
        self.check_spot()
