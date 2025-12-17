import os
import requests
import time
import pandas as pd
import pandas_ta as ta
from datetime import datetime
from openai import OpenAI

# --- КОНФИГУРАЦИЯ ---
OKX_URL = "https://www.okx.com/api/v5/market/candles"
INTERVAL = "15m"

# Список монет
# Полный список (Сбалансированный портфель: Топ + L1 + Мемы + AI)
SYMBOLS = {
    # 💎 Фундаментальные (Тяжеловесы)
    "BTC": "BTC-USDT-SWAP",
    "ETH": "ETH-USDT-SWAP",
    "BNB": "BNB-USDT-SWAP",
    "SOL": "SOL-USDT-SWAP",
    
    # 🚀 Активные L1/L2 (Техничные движения)
    "ARB": "ARB-USDT-SWAP",
    "OP": "OP-USDT-SWAP",
    "SUI": "SUI-USDT-SWAP",
    "APT": "APT-USDT-SWAP",
    "TIA": "TIA-USDT-SWAP",  # <-- Добавлено
    "TON": "TON-USDT-SWAP",
    
    # 🐶 Мемы (Высокая волатильность - "топливо" для бота)
    "DOGE": "DOGE-USDT-SWAP", # <-- Добавлено
    "PEPE": "PEPE-USDT-SWAP", # <-- Добавлено
    "WIF": "WIF-USDT-SWAP",   # <-- Добавлено
    
    # 🤖 Трендовые сектора (AI / Старая школа)
    "FET": "FET-USDT-SWAP",   # <-- Добавлено (AI Сектор)
    "XRP": "XRP-USDT-SWAP",   # <-- Добавлено
    "LTC": "LTC-USDT-SWAP",
}

class TradingAgent:
    def __init__(self, bot_token, chat_id, openai_key):
        self.bot_token = bot_token
        self.chat_id = chat_id
        self.client = OpenAI(api_key=openai_key)
        self.positions = {symbol: None for symbol in SYMBOLS}

    # 1. ОТПРАВКА
    def send(self, text):
        url = f"https://api.telegram.org/bot{self.bot_token}/sendMessage"
        try:
            requests.post(url, json={"chat_id": self.chat_id, "text": text, "parse_mode": "Markdown"}, timeout=5)
        except: pass

    # 2. ДАННЫЕ
    def get_data(self, symbol):
        try:
            r = requests.get(OKX_URL, params={"instId": symbol, "bar": INTERVAL, "limit": 100}, timeout=10)
            if r.status_code != 200: return None
            data = r.json().get("data", [])
            if not data: return None
            
            df = pd.DataFrame(data, columns=["ts", "o", "h", "l", "c", "v", "volCcy", "volCcyQuote", "confirm"])
            df = df.iloc[::-1].reset_index(drop=True)
            df[["o", "h", "l", "c", "v"]] = df[["o", "h", "l", "c", "v"]].astype(float)
            return df
        except: return None

    # 3. ГЛОБАЛЬНЫЙ ТРЕНД
    def get_trend_4h(self, symbol):
        try:
            r = requests.get(OKX_URL, params={"instId": symbol, "bar": "4H", "limit": 100}, timeout=10)
            data = r.json().get("data", [])
            if not data: return "NEUTRAL"
            df = pd.DataFrame(data, columns=["ts", "o", "h", "l", "c", "v", "volCcy", "volCcyQuote", "confirm"])
            df = df.iloc[::-1].reset_index(drop=True)
            df["c"] = df["c"].astype(float)
            ema50 = ta.ema(df["c"], length=50).iloc[-1]
            ema200 = ta.ema(df["c"], length=200).iloc[-1]
            if ema50 > ema200: return "UP"
            if ema50 < ema200: return "DOWN"
            return "NEUTRAL"
        except: return "NEUTRAL"

    # 4. AI АНАЛИЗ (С учетом ADX и Объема)
    def ask_ai(self, symbol, side, price, rsi, adx, vol_ratio, global_trend):
        print(f"🧠 AI analyzing {symbol}...")
        prompt = f"""
        Ты Аналитик. Фильтруй сигналы.
        
        ДАННЫЕ:
        - Тикер: {symbol}
        - Сигнал: {side}
        - Тренд 4H: {global_trend}
        - ADX (Сила тренда): {adx} (Если < 25, рынок слабый/флэт)
        - Volume Ratio: {vol_ratio} (Если > 1.0, объем выше среднего)
        - RSI: {rsi}
        
        ТВОЯ СТРАТЕГИЯ:
        1. Если ADX < 20, это "шум". Отклоняй.
        2. Если Volume Ratio < 0.8, нет интереса покупателей. Будь осторожен.
        3. Идеальный вход: ADX > 25, Volume > 1.2, Тренд совпадает.
        
        Верни ТОЛЬКО текст:
        Risk: [1-10]/10
        Verdict: [ENTER или WAIT]
        Reason: [Кратко]
        """
        for i in range(3):
            try:
                response = self.client.chat.completions.create(
                    model="gpt-4o-mini",
                    messages=[{"role": "user", "content": prompt}],
                    max_tokens=150
                )
                return response.choices[0].message.content
            except Exception as e:
                if "429" in str(e): time.sleep((i+1)*2); continue
                return "AI Error"
        return "Skip"

    # 5. АНАЛИЗ
    def analyze(self):
        print(f"--- 🔍 Checking Market {datetime.now().strftime('%H:%M')} ---")
        
        for name, symbol in SYMBOLS.items():
            time.sleep(0.1)
            df = self.get_data(symbol)
            if df is None: continue

            # --- ИНДИКАТОРЫ ---
            # 1. EMA
            df["ema_fast"] = ta.ema(df["c"], length=9)  # Ускорил (было 21)
            df["ema_slow"] = ta.ema(df["c"], length=21) # Ускорил (было 50)
            
            # 2. RSI
            df["rsi"] = ta.rsi(df["c"], length=14)
            
            # 3. ATR (для стопов)
            df["atr"] = ta.atr(df["h"], df["l"], df["c"], length=14)
            
            # 4. ADX (Сила тренда) 🔥
            adx_df = ta.adx(df["h"], df["l"], df["c"], length=14)
            df["adx"] = adx_df["ADX_14"]
            
            # 5. Volume SMA (Средний объем) 🔥
            df["vol_sma"] = ta.sma(df["v"], length=20)

            # Берем данные закрытой свечи
            curr = df.iloc[-2]
            price = curr["c"]
            atr = curr["atr"]
            adx = curr["adx"]
            vol_ratio = curr["v"] / curr["vol_sma"] if curr["vol_sma"] > 0 else 0

            # --- ЛОГИКА СИГНАЛОВ (ЖЕСТКИЙ ФИЛЬТР) ---
            signal = None
            
            # Условия для BUY:
            # 1. EMA Fast > Slow
            # 2. RSI между 50 и 70 (есть импульс, но не пик)
            # 3. ADX > 20 (рынок не спит)
            if (curr["ema_fast"] > curr["ema_slow"] and 
                50 < curr["rsi"] < 70 and 
                adx > 20):
                signal = "BUY"

            # Условия для SELL:
            elif (curr["ema_fast"] < curr["ema_slow"] and 
                  30 < curr["rsi"] < 50 and 
                  adx > 20):
                signal = "SELL"

            if signal and self.positions[name] != signal:
                
                # Фильтр 1: Глобальный тренд
                global_trend = self.get_trend_4h(symbol)
                if signal == "BUY" and global_trend == "DOWN": continue
                if signal == "SELL" and global_trend == "UP": continue

                # Фильтр 2: Объем (Опционально, но полезно)
                # Если объем сильно ниже среднего (< 0.5), сигнал слабый
                if vol_ratio < 0.5: 
                    print(f"📉 {name} Skip: Low Volume ({round(vol_ratio, 2)})")
                    continue

                # AI Анализ
                ai_verdict = self.ask_ai(name, signal, price, round(curr["rsi"],1), round(adx,1), round(vol_ratio,2), global_trend)
                
                # Если AI сказал "WAIT" или Риск высокий — не шлем (можно раскомментить)
                # if "WAIT" in ai_verdict: continue 

                # Стопы
                sl_factor = 2.0
                tp_factor = 3.5 # Попробовать взять движение побольше
                
                if signal == "BUY":
                    sl = price - (atr * sl_factor)
                    tp = price + (atr * tp_factor)
                else:
                    sl = price + (atr * sl_factor)
                    tp = price - (atr * tp_factor)

                msg = (
                    f"🔥 **PREMIUM SIGNAL**\n"
                    f"#{name} — {signal}\n"
                    f"📊 ADX: {round(adx, 1)} (Trend Strength)\n"
                    f"🔊 Vol Ratio: {round(vol_ratio, 2)}x\n"
                    f"🌍 4H Trend: {global_trend}\n\n"
                    f"💰 Entry: `{price}`\n"
                    f"🎯 TP: `{round(tp, 4)}`\n"
                    f"🛑 SL: `{round(sl, 4)}`\n"
                    f"🤖 AI: {ai_verdict}"
                )
                self.send(msg)
                self.positions[name] = signal
                time.sleep(3)
