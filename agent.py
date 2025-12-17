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

# 🔥 УМНЫЙ СПИСОК МОНЕТ (ТИКЕР + ПЛЕЧО)
# "id": тикер на бирже
# "lev": рекомендуемое плечо (Risk Management)
SYMBOLS = {
    # 🐢 Фундаментал (Низкий риск -> Плечо 10x)
    "BTC":  {"id": "BTC-USDT-SWAP", "lev": 10},
    "ETH":  {"id": "ETH-USDT-SWAP", "lev": 10},
    "BNB":  {"id": "BNB-USDT-SWAP", "lev": 10},
    
    # 🚗 Альткоины (Средний риск -> Плечо 5x-7x)
    "SOL":  {"id": "SOL-USDT-SWAP", "lev": 7},
    "XRP":  {"id": "XRP-USDT-SWAP", "lev": 7},
    "LTC":  {"id": "LTC-USDT-SWAP", "lev": 7},
    "TON":  {"id": "TON-USDT-SWAP", "lev": 5},
    "ARB":  {"id": "ARB-USDT-SWAP", "lev": 5},
    "OP":   {"id": "OP-USDT-SWAP",  "lev": 5},
    "SUI":  {"id": "SUI-USDT-SWAP", "lev": 5},
    "APT":  {"id": "APT-USDT-SWAP", "lev": 5},
    "TIA":  {"id": "TIA-USDT-SWAP", "lev": 5},
    
    # 🚀 Мемы и AI (Высочайший риск -> Плечо 3x)
    "DOGE": {"id": "DOGE-USDT-SWAP", "lev": 5}, # Доги чуть стабильнее
    "PEPE": {"id": "PEPE-USDT-SWAP", "lev": 3},
    "WIF":  {"id": "WIF-USDT-SWAP",  "lev": 3},
    "FET":  {"id": "FET-USDT-SWAP",  "lev": 3},
}

class TradingAgent:
    def __init__(self, bot_token, chat_id, openai_key):
        self.bot_token = bot_token
        self.chat_id = chat_id
        self.client = OpenAI(api_key=openai_key)
        # Память позиций
        self.positions = {name: None for name in SYMBOLS}

    # 1. ОТПРАВКА
    def send(self, text):
        url = f"https://api.telegram.org/bot{self.bot_token}/sendMessage"
        try:
            requests.post(url, json={"chat_id": self.chat_id, "text": text, "parse_mode": "Markdown"}, timeout=5)
        except: pass

    # 2. ПОЛУЧЕНИЕ ДАННЫХ
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

    # 3. ГЛОБАЛЬНЫЙ ТРЕНД (4H)
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

    # 4. AI АНАЛИЗ
    def ask_ai(self, symbol, side, leverage, price, rsi, adx, vol_ratio, global_trend):
        print(f"🧠 AI analyzing {symbol}...")
        prompt = f"""
        Ты Риск-менеджер.
        
        ДАННЫЕ:
        - Тикер: {symbol} (Реком. плечо: {leverage}x)
        - Сигнал: {side}
        - Тренд 4H: {global_trend}
        - ADX (Сила): {adx} (>25 = Тренд)
        - Volume Ratio: {vol_ratio}
        - RSI: {rsi}
        
        ЗАДАЧА:
        Оцени риск сделки (1-10). Если ADX < 20, рекомендуй пропустить.
        Верни ТОЛЬКО текст:
        Risk: [1-10]/10
        Verdict: [ENTER / SKIP]
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
        print(f"--- 🔍 Smart Analysis {datetime.now().strftime('%H:%M')} ---")
        
        # ⚠️ ИЗМЕНЕНИЕ: Распаковываем словарь с настройками
        for name, info in SYMBOLS.items():
            symbol = info["id"]
            leverage = info["lev"]
            
            time.sleep(0.1) # Анти-спам биржи
            df = self.get_data(symbol)
            if df is None: continue

            # --- ИНДИКАТОРЫ ---
            df["ema_fast"] = ta.ema(df["c"], length=9)
            df["ema_slow"] = ta.ema(df["c"], length=21)
            df["rsi"] = ta.rsi(df["c"], length=14)
            df["atr"] = ta.atr(df["h"], df["l"], df["c"], length=14)
            adx_df = ta.adx(df["h"], df["l"], df["c"], length=14)
            df["adx"] = adx_df["ADX_14"]
            df["vol_sma"] = ta.sma(df["v"], length=20)

            # Текущие значения
            curr = df.iloc[-2]
            price = curr["c"]
            atr = curr["atr"]
            adx = curr["adx"]
            vol_ratio = curr["v"] / curr["vol_sma"] if curr["vol_sma"] > 0 else 0

            # --- ЛОГИКА ---
            signal = None
            
            # Условия (Ужесточенные)
            # RSI 50-70 для BUY, 30-50 для SELL
            # ADX > 20 (фильтр флэта)
            if (curr["ema_fast"] > curr["ema_slow"] and 50 < curr["rsi"] < 70 and adx > 20):
                signal = "BUY"
            elif (curr["ema_fast"] < curr["ema_slow"] and 30 < curr["rsi"] < 50 and adx > 20):
                signal = "SELL"

            if signal and self.positions[name] != signal:
                
                # Фильтр Глобального тренда
                global_trend = self.get_trend_4h(symbol)
                if signal == "BUY" and global_trend == "DOWN": continue
                if signal == "SELL" and global_trend == "UP": continue

                # Фильтр Объема
                if vol_ratio < 0.6: continue

                # AI Проверка
                ai_verdict = self.ask_ai(name, signal, leverage, price, round(curr["rsi"],1), round(adx,1), round(vol_ratio,2), global_trend)
                
                # Динамические стопы на основе волатильности и плеча
                # Чем выше плечо, тем короче должен быть стоп в % движения цены, 
                # но ATR учитывает волатильность монеты.
                # Для мемов (3x) стоп будет широким (2 ATR), для BTC (10x) тоже 2 ATR.
                sl_dist = atr * 2
                tp_dist = atr * 3.5
                
                if signal == "BUY":
                    sl = price - sl_dist
                    tp = price + tp_dist
                else:
                    sl = price + sl_dist
                    tp = price - tp_dist

                msg = (
                    f"🔥 **SMART SIGNAL**\n"
                    f"#{name} — {signal}\n"
                    f"⚙️ **Lev: {leverage}x** (Risk Adjusted)\n"
                    f"📊 ADX: {round(adx, 1)} | Vol: {round(vol_ratio, 2)}x\n"
                    f"🌍 4H Trend: {global_trend}\n\n"
                    f"💰 Entry: `{price}`\n"
                    f"🎯 TP: `{round(tp, 4)}`\n"
                    f"🛑 SL: `{round(sl, 4)}`\n"
                    f"🤖 AI: {ai_verdict}"
                )
                self.send(msg)
                self.positions[name] = signal
                time.sleep(3)
