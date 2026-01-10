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
        # Подключение к DeepSeek (совместим с OpenAI SDK)
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

    # 🔥 УЛУЧШЕННЫЙ ПРОМПТ ДЛЯ DEEPSEEK
    def ask_ai(self, mode, symbol, price, rsi, adx, trend, direction):
        strategy_name = "DEEPSEEK_ALPHA"
        
        print(f"🧠 AI Analyzing {symbol} ({direction})...")

        # Более строгий JSON формат
        json_template = '{"Confidence": int (0-100), "Verdict": "BUY" or "SELL" or "WAIT", "Reason": "Short phrase"}'
        
        # Инструкция: Быть решительным, не бояться волатильности
        system_prompt = (
            f"Ты — Агрессивный Крипто-Трейдер. Твоя цель — МАКСИМИЗАЦИЯ ПРИБЫЛИ.\n"
            f"Рынок волатилен, и это ХОРОШО. Не бойся рисковать.\n\n"
            f"ВХОДНЫЕ ДАННЫЕ:\n"
            f"- Актив: {symbol}\n"
            f"- Направление: {direction}\n"
            f"- RSI: {rsi} (30-70 = Норма, >70 = Памп, <30 = Дно)\n"
            f"- ADX: {adx} (Сила тренда)\n\n"
            f"ПРАВИЛА:\n"
            f"1. Если RSI > 70, но тренд сильный (ADX > 30) — ЭТО BUY (Памп).\n"
            f"2. Если RSI < 30 — ЭТО BUY (Отскок).\n"
            f"3. Если индикаторы противоречат, но тренд явный — ВЕРЬ ТРЕНДУ.\n"
            f"4. Не пиши WAIT, если есть хоть малейший шанс заработать.\n"
            f"ФОРМАТ ОТВЕТА (JSON): {json_template}"
        )

        user_prompt = (
            f"Current Price: {price}\n"
            f"Technical Setup: {direction} Signal detected via EMA Cross.\n"
            f"Make a decision."
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
                    temperature=0.3 # Немного креативности, но в рамках правил
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
        print("--- 🚀 Checking Futures ---")
        timeframes = ["15m", "1H"] # Проверяем два таймфрейма
        
        for name, info in FUTURES_SYMBOLS.items():
            symbol = info["id"]
            lev = info["lev"]
            
            # Если позиция уже есть, не спамим (но можно доработать для докупки)
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
                prev = df.iloc[-2]

                adx_val = curr["adx"]
                rsi_val = curr["rsi"]
                price = curr["c"]

                if pd.isna(rsi_val): continue

                signal_type = None
                
                # --- ЛОГИКА СИГНАЛОВ (Расширенная) ---
                
                # 1. LONG (EMA Cross UP или Отскок от дна)
                # Условие: Быстрая EMA выше медленной ИЛИ RSI перепродан (<35)
                # Фильтр: RSI не должен быть экстремально перекуплен (>85), кроме супер-пампов
                if (curr["ema_f"] > curr["ema_s"] and rsi_val < 85):
                    signal_type = "LONG"
                elif (rsi_val < 30): # Ловля ножей (агрессивно)
                    signal_type = "LONG_DIP"

                # 2. SHORT (EMA Cross DOWN или Вершина)
                elif (curr["ema_f"] < curr["ema_s"] and rsi_val > 15):
                    signal_type = "SHORT"
                elif (rsi_val > 80): # Продажа на хаях
                    signal_type = "SHORT_TOP"

                # Если есть хоть какой-то намек на сигнал — зовем AI
                if signal_type:
                    ai_verdict, strategy_used = self.ask_ai(
                        "FUTURES", name, price, round(rsi_val,1), round(adx_val,1), 
                        f"{tf} Trend", signal_type
                    )
                    
                    # Фильтр ответов AI
                    verdict_up = str(ai_verdict).upper()
                    if "WAIT" in verdict_up or "SKIP" in verdict_up: 
                        continue

                    atr_mult = 3.0
                    
                    if "LONG" in signal_type:
                        tp = price + (curr["atr"] * atr_mult)
                        sl = price - (curr["atr"] * 2.0)
                        emoji = "🟢"
                    else:
                        tp = price - (curr["atr"] * atr_mult)
                        sl = price + (curr["atr"] * 2.0)
                        emoji = "🔴"

                    msg = (
                        f"⚡ **SIGNAL: {signal_type}** {emoji}\n"
                        f"#{name} — {tf}\n"
                        f"🧠 AI: **{strategy_used}**\n"
                        f"📊 RSI: {round(rsi_val,1)} | ADX: {round(adx_val,1)}\n"
                        f"💰 Price: {price}\n"
                        f"🎯 TP: {round(tp,4)}\n🛑 SL: {round(sl,4)}\n"
                        f"📝 Verdict: {ai_verdict}"
                    )
                    self.send(msg)
                    self.positions[name] = signal_type 
                    time.sleep(2)
                    break # Если нашли сигнал на одном ТФ, идем к следующей монете

    # --- СПОТ (4H) ---
    def check_spot(self):
        print("--- 🏦 Checking Spot ---")
        for name, symbol in SPOT_SYMBOLS.items():
            if self.spot_positions[name] == "BUY": continue
            
            time.sleep(0.1)
            df = self.get_candles(symbol, "4H", limit=100)
            if df is None: continue

            rsi = ta.rsi(df["c"], length=14).iloc[-1]
            price = df["c"].iloc[-1]

            # Упрощенная логика для спота: просто покупаем на просадках
            if rsi < 40:
                ai_verdict, strategy_used = self.ask_ai("SPOT", name, price, round(rsi,1), 0, "Oversold", "LONG")
                
                if "BUY" in str(ai_verdict).upper():
                    self.send(
                        f"💎 **SPOT INVEST**\n#{name}\n"
                        f"📉 RSI: {round(rsi, 1)}\n"
                        f"💰 Price: {price}\n"
                        f"🤖 AI: {ai_verdict}"
                    )
                    self.spot_positions[name] = "BUY"
                    time.sleep(2)

    def analyze(self):
        self.check_futures()
        self.check_spot()
