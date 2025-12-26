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
    "MON":   {"id": "MON-USDT-SWAP",    "lev": 3},
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
        # Используем словарь для хранения статусов по каждому таймфрейму (ключ: "SYMBOL_TF")
        self.spot_positions = {} 

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

    # 🔥 AI МОЗГ: ОПЫТНЫЙ ТРЕЙДЕР
    def ask_ai(self, mode, symbol, price, rsi, adx, trend, extra_info=""):
        
        strategy_name = "CRYPTO_VETERAN"
        print(f"🧠 Veteran Trader analyzing {symbol}...")

        json_template = '{"Risk": int, "Verdict": "BUY" or "WAIT", "Reason": "text"}'
        
        system_prompt = (
            f"Ты — опытный крипто-трейдер с 10-летним стажем.\n"
            f"Твой подход: Прагматичный Price Action + Технический анализ.\n"
            f"ПРАВИЛА:\n"
            f"1. Не верь хайпу. Верь цифрам (RSI, ADX, Trend).\n"
            f"2. Если RSI перегрет (>70) и тренд слабый — это риск. WAIT.\n"
            f"3. Если есть четкий сигнал на дне (RSI < 30) — заходи (BUY).\n"
            f"ФОРМАТ ОТВЕТА (СТРОГО JSON): {json_template}"
        )

        user_prompt = (
            f"Анализ актива: {symbol}\n"
            f"Режим: {mode}\n"
            f"Цена: {price}\n"
            f"RSI (14): {rsi}\n"
            f"ADX: {adx}\n"
            f"Тренд: {trend}\n"
            f"Инфо: {extra_info}\n"
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
            except Exception as e:
                time.sleep(1)
                continue
        
        return "Skip", strategy_name

    # --- ФЬЮЧЕРСЫ (15m) ---
    def check_futures(self):
        print("--- 🚀 Checking Futures ---")
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
            rsi_val = curr["rsi"]

            rsi_limit = 78 if adx_val > 35 else 70

            signal = None
            if (curr["ema_f"] > curr["ema_s"] and 
                50 < rsi_val < rsi_limit and 
                adx_val > 20):
                signal = "BUY"

            if signal and self.positions[name] != signal:
                
                d_df = self.get_candles(symbol, "1D", limit=50)
                if d_df is not None:
                    ema20_d = ta.ema(d_df["c"], length=20).iloc[-1]
                    if curr["c"] < ema20_d: continue 

                ai_verdict, strategy_used = self.ask_ai("FUTURES", name, curr["c"], round(rsi_val,1), round(adx_val,1), "UP (15m)")
                
                if "WAIT" in str(ai_verdict).upper(): continue

                tp = curr["c"] + (curr["atr"] * 3.5)
                sl = curr["c"] - (curr["atr"] * 2.0)

                msg = (
                    f"👨‍💻 **TRADER SIGNAL**\n#{name} — BUY 🟢\n"
                    f"🧠 Analyst: **{strategy_used}**\n"
                    f"⚙️ Lev: {lev}x\n"
                    f"📊 ADX: {round(adx_val,1)}\n"
                    f"💰 Entry: {curr['c']}\n🎯 TP: {round(tp,4)}\n🛑 SL: {round(sl,4)}\n"
                    f"💬 Verdict: {ai_verdict}"
                )
                self.send(msg)
                self.positions[name] = signal
                cycle_signals += 1
                time.sleep(2)

    # --- СПОТ (4H и 1D) ---
    def check_spot(self):
        print("--- 🏦 Checking Spot ---")
        # 🔥 Добавлен таймфрейм 1D
        timeframes = ["4H", "1D"] 
        
        for name, symbol in SPOT_SYMBOLS.items():
            for tf in timeframes:
                time.sleep(0.1)
                df = self.get_candles(symbol, tf, limit=200)
                if df is None: continue

                rsi = ta.rsi(df["c"], length=14).iloc[-1]
                ema200 = ta.ema(df["c"], length=200).iloc[-1]
                price = df["c"].iloc[-1]

                is_dip = False
                setup = ""

                # Логика поиска дна работает одинаково для обоих ТФ
                if price > ema200 and rsi < 40:
                    is_dip = True
                    setup = f"Trend Pullback ({tf})"
                elif rsi < 30:
                    is_dip = True
                    setup = f"Oversold Bounce ({tf})"

                # Уникальный ключ для отслеживания позиции: "BTC_4H" или "BTC_1D"
                pos_key = f"{name}_{tf}"
                current_status = self.spot_positions.get(pos_key)

                if is_dip and current_status != "BUY":
                    ai_verdict, strategy_used = self.ask_ai("SPOT", name, price, round(rsi,1), 0, setup)
                    
                    msg = (
                        f"💎 **SPOT INVEST ({tf})**\n#{name} — ACCUMULATE 🔵\n"
                        f"📉 RSI: {round(rsi, 1)}\n"
                        f"🧠 Analyst: {strategy_used}\n"
                        f"💰 Price: {price}\n"
                        f"💬 Verdict: {ai_verdict}"
                    )
                    self.send(msg)
                    self.spot_positions[pos_key] = "BUY"
                    time.sleep(2)
                
                elif rsi > 55:
                    self.spot_positions[pos_key] = None

    def analyze(self):
        self.check_futures()
        self.check_spot()

