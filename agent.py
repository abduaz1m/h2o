import os
import requests
import time
import pandas as pd
import pandas_ta as ta
from openai import OpenAI

# --- КОНФИГУРАЦИЯ ---
OKX_URL = "https://www.okx.com/api/v5/market/candles"

# 1. 🚜 СПИСОК ФЬЮЧЕРСОВ (Только Kings)
FUTURES_SYMBOLS = {
    "BTC":    {"id": "BTC-USDT-SWAP",    "lev": 20}, # Плечо 20x для BTC
    "ETH":    {"id": "ETH-USDT-SWAP",    "lev": 20}, # Плечо 20x для ETH
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

    # 🔥 СПЕЦИАЛИЗИРОВАННЫЙ ПРОМПТ (BTC/ETH EXPERT)
    def ask_ai(self, mode, symbol, price, rsi, adx, trend, direction):
        strategy_name = "MARKET_MAKER_LOGIC"
        
        print(f"🧠 Checking {symbol} ({direction})...")

        json_template = '{"Confidence": int (0-100), "Verdict": "BUY" or "SELL" or "WAIT", "Reason": "Max 10 words"}'
        
        # Промпт заточен под поведение Биткоина и Эфира
        system_prompt = (
            f"Ты — Эксперт по BTC и ETH. Ты торгуешь только главными активами.\n"
            f"Твоя философия: 'Биткоин диктует тренд'.\n\n"
            f"ВХОДНЫЕ ДАННЫЕ:\n"
            f"- Актив: {symbol}\n"
            f"- Паттерн: {direction}\n"
            f"- Индикаторы: RSI={rsi}, ADX={adx}\n\n"
            f"ПРАВИЛА ПРИНЯТИЯ РЕШЕНИЙ:\n"
            f"1. BTC/ETH редко делают ложные движения на сильном импульсе (ADX > 25). Верь тренду.\n"
            f"2. Если RSI > 75 — это кульминация покупок. Будь осторожен с Лонгами (лучше WAIT или SHORT скальп).\n"
            f"3. Если RSI < 25 — это паническая распродажа. Ищи вход в LONG (отскок).\n"
            f"4. Для BTC важен пробой уровня. Если сигнал подтвержден объемами или ADX — ВХОДИ.\n"
            f"ФОРМАТ ОТВЕТА (JSON): {json_template}"
        )

        user_prompt = (
            f"Market Update: {symbol} is showing a {direction} setup.\n"
            f"Price: {price}\n"
            f"Make a professional decision."
        )

        for i in range(2):
            try:
                response = self.client.chat.completions.create(
                    model="deepseek-chat",
                    messages=[
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": user_prompt}
                    ],
                    max_tokens=180,
                    temperature=0.2 # Низкая температура для строгости
                )
                content = response.choices[0].message.content
                content = content.replace("```json", "").replace("```", "").strip()
                return content, strategy_name
            except Exception:
                time.sleep(1)
                continue
        
        return "Skip", strategy_name

    # --- ФЬЮЧЕРСЫ (15m, 1H) ---
    def check_futures(self):
        print("--- 🚀 Futures: BTC & ETH Strategy ---")
        timeframes = ["15m", "1H"]
        
        for name, info in FUTURES_SYMBOLS.items():
            symbol = info["id"]
            lev = info["lev"]
            
            if self.positions[name] is not None:
                continue

            for tf in timeframes:
                time.sleep(0.15)
                df = self.get_candles(symbol, tf, limit=100)
                if df is None or len(df) < 50: continue

                # Классический набор индикаторов для BTC
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
                
                # --- ЛОГИКА ДЛЯ MAJOR PAIRS ---
                
                # 1. LONG:
                # BTC любит тренды. Если EMA пересеклись + RSI не на потолке
                if (curr["ema_f"] > curr["ema_s"] and rsi_val < 80):
                    signal_type = "LONG_TREND"
                # Ловля "Сквизов" (резких падений)
                elif (rsi_val < 28): 
                    signal_type = "LONG_DIP_SNIPER"

                # 2. SHORT:
                elif (curr["ema_f"] < curr["ema_s"] and rsi_val > 20):
                    signal_type = "SHORT_TREND"
                # Ловля вершин
                elif (rsi_val > 82): 
                    signal_type = "SHORT_TOP_SNIPER"

                if signal_type:
                    ai_verdict, strategy_used = self.ask_ai(
                        "FUTURES", name, price, round(rsi_val,1), round(adx_val,1), 
                        f"{tf}", signal_type
                    )
                    
                    verdict_up = str(ai_verdict).upper()
                    if "WAIT" in verdict_up or "SKIP" in verdict_up: 
                        continue

                    # Настройки TP/SL для BTC/ETH (чуть шире, чем для альтов)
                    atr_mult = 3.5 
                    
                    if "LONG" in signal_type:
                        tp = price + (curr["atr"] * atr_mult)
                        sl = price - (curr["atr"] * 2.0)
                        emoji = "🟢"
                    else:
                        tp = price - (curr["atr"] * atr_mult)
                        sl = price + (curr["atr"] * 2.0)
                        emoji = "🔴"

                    msg = (
                        f"👑 **MAJOR SIGNAL: {signal_type}** {emoji}\n"
                        f"#{name} — {tf}\n"
                        f"🧠 AI: **{strategy_used}**\n"
                        f"⚙️ Lev: {lev}x\n"
                        f"📊 RSI: {round(rsi_val,1)} | ADX: {round(adx_val,1)}\n"
                        f"💰 Price: {price}\n"
                        f"🎯 TP: {round(tp,2)}\n🛑 SL: {round(sl,2)}\n"
                        f"📝 Verdict: {ai_verdict}"
                    )
                    self.send(msg)
                    self.positions[name] = signal_type 
                    time.sleep(2)
                    break 

    # --- СПОТ (4H) ---
    def check_spot(self):
        print("--- 🏦 Spot: Accumulation ---")
        for name, symbol in SPOT_SYMBOLS.items():
            if self.spot_positions[name] == "BUY": continue
            
            time.sleep(0.1)
            df = self.get_candles(symbol, "4H", limit=100)
            if df is None: continue

            rsi = ta.rsi(df["c"], length=14).iloc[-1]
            price = df["c"].iloc[-1]

            # Для Спота BTC/ETH берем только хорошие просадки
            if rsi < 35:
                ai_verdict, strategy_used = self.ask_ai("SPOT", name, price, round(rsi,1), 0, "DIP", "ACCUMULATE")
                
                if "BUY" in str(ai_verdict).upper():
                    self.send(
                        f"🏦 **WHALE ACCUMULATION**\n#{name}\n"
                        f"📉 RSI: {round(rsi, 1)} (Oversold)\n"
                        f"💰 Price: {price}\n"
                        f"🤖 AI: {ai_verdict}"
                    )
                    self.spot_positions[name] = "BUY"
                    time.sleep(2)

    def analyze(self):
        self.check_futures()
        self.check_spot()
