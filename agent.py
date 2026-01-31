import os
import requests
import time
import pandas as pd
import pandas_ta as ta
from openai import OpenAI

# --- КОНФИГУРАЦИЯ ---
OKX_URL = "https://www.okx.com/api/v5/market/candles"

# 1. 🚜 АГРЕССИВНЫЙ СПИСОК (Добавили волатильности)
FUTURES_SYMBOLS = {
    "BTC":    {"id": "BTC-USDT-SWAP",    "lev": 20},
    "ETH":    {"id": "ETH-USDT-SWAP",    "lev": 20},
    "SOL":    {"id": "SOL-USDT-SWAP",    "lev": 10}, # SOL очень техничный
    "DOGE":   {"id": "DOGE-USDT-SWAP",    "lev": 10}, # Для частых сигналов
    "PEPE":   {"id": "PEPE-USDT-SWAP",   "lev": 5},  # Самый активный
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
        self.client = OpenAI(api_key=openai_key, base_url="https://api.deepseek.com")
        self.positions = {name: None for name in FUTURES_SYMBOLS}
        self.spot_positions = {name: None for name in SPOT_SYMBOLS}
        
        print("🚀 AGGRESSIVE SCALPER ACTIVATED")
        self.test_connection()

    def test_connection(self):
        try:
            self.client.chat.completions.create(
                model="deepseek-chat",
                messages=[{"role": "user", "content": "."}],
                max_tokens=1
            )
            print("✅ AI Online")
        except Exception:
            print("⚠️ AI Offline/No Funds (Will use Tech-Only Mode)")

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

    # 🔥 ПРОМПТ "HUNGRY TRADER" (ГОЛОДНЫЙ ТРЕЙДЕР)
    def ask_ai(self, mode, symbol, price, rsi, bb_pos, direction):
        strategy_name = "BB_BREAKOUT"
        
        json_template = '{"Verdict": "BUY" or "SELL", "Reason": "Short trigger"}'
        
        # Мы говорим AI: "Действуй, не жди". Убрали вариант WAIT из промпта.
        system_prompt = (
            f"Ты — Агрессивный Скальпер. Рынок быстрый.\n"
            f"СТРАТЕГИЯ: Торговля от границ Боллинджера (Mean Reversion).\n"
            f"АКТИВ: {symbol}. ЦЕНА: {price}.\n"
            f"ТЕХНИКА: RSI={rsi}, BB_Position={bb_pos} (Lower/Upper Band).\n\n"
            f"ТВОЯ ЗАДАЧА: Найти точку входа. Если цена у границы — ЭТО СИГНАЛ.\n"
            f"НЕ ПИШИ 'WAIT', если есть хоть малейший шанс.\n"
            f"Если RSI < 45 и цена у нижней границы -> BUY.\n"
            f"Если RSI > 55 и цена у верхней границы -> SELL.\n"
            f"JSON ONLY: {json_template}"
        )
        
        user_prompt = f"Price hit {bb_pos} band. RSI is {rsi}. Execute trade?"

        for i in range(2):
            try:
                response = self.client.chat.completions.create(
                    model="deepseek-chat",
                    messages=[
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": user_prompt}
                    ],
                    max_tokens=120,
                    temperature=0.4 # Повысили температуру для смелости
                )
                content = response.choices[0].message.content
                content = content.replace("```json", "").replace("```", "").strip()
                return content, strategy_name
            except Exception:
                # Если AI сломался, возвращаем "BUY/SELL" на основе техники
                return ("BUY" if "Lower" in bb_pos else "SELL") + " (AI Bypass)", "TECH_FORCE"
        
        return "Skip", strategy_name

    def check_futures(self):
        print("\n--- ⚡ Scanning for Volatility (5m) ---")
        timeframes = ["5m"] # Только 5 минут для скорости
        
        for name, info in FUTURES_SYMBOLS.items():
            symbol = info["id"]
            lev = info["lev"]
            
            # Разрешаем повторные входы, если сигнал изменился, поэтому не проверяем жестко self.positions
            
            for tf in timeframes:
                time.sleep(0.15)
                df = self.get_candles(symbol, tf, limit=50)
                if df is None: continue

                # РАСЧЕТ ИНДИКАТОРОВ
                df["rsi"] = ta.rsi(df["c"], length=14)
                df["atr"] = ta.atr(df["h"], df["l"], df["c"], length=14)
                
                # Полосы Боллинджера (20, 2)
                bb = ta.bbands(df["c"], length=20, std=2.0)
                if bb is None: continue
                
                # Достаем значения (Lower, Middle, Upper)
                lower = bb[f"BBL_20_2.0"].iloc[-1]
                upper = bb[f"BBU_20_2.0"].iloc[-1]
                
                curr = df.iloc[-1]
                rsi_val = curr["rsi"]
                price = curr["c"]

                print(f"📊 {name}: Price={price} | BB_Low={round(lower,4)} | BB_Up={round(upper,4)} | RSI={round(rsi_val,1)}")

                signal_type = None
                bb_status = ""
                
                # --- АГРЕССИВНАЯ ЛОГИКА ---
                
                # 1. LONG: Цена пробила или коснулась нижней линии + RSI не перегрет (<55)
                # Мы расширили зону RSI до 45-50, чтобы брать больше сделок
                if price <= (lower * 1.001) and rsi_val < 50:
                    signal_type = "LONG_BB_BOUNCE"
                    bb_status = "Lower Band Touch"

                # 2. SHORT: Цена у верхней линии + RSI не на дне (>45)
                elif price >= (upper * 0.999) and rsi_val > 50:
                    signal_type = "SHORT_BB_REJECT"
                    bb_status = "Upper Band Touch"

                if signal_type:
                    print(f"🔥 Signal: {signal_type}. Engaging AI...")
                    
                    ai_verdict, strategy_used = self.ask_ai(
                        "FUTURES", name, price, round(rsi_val,1), bb_status, signal_type
                    )
                    
                    # Фильтр только на жесткий отказ. Если AI пишет что-то невнятное - торгуем.
                    verdict_up = str(ai_verdict).upper()
                    if "WAIT" in verdict_up or "HOLD" in verdict_up:
                        print("⛔ AI asked to Wait.")
                        continue

                    # Короткие цели (Скальпинг)
                    atr_mult = 1.5 # Быстрый тейк
                    
                    if "LONG" in signal_type:
                        tp = price + (curr["atr"] * atr_mult)
                        sl = price - (curr["atr"] * 1.2)
                        emoji = "🟢"
                    else:
                        tp = price - (curr["atr"] * atr_mult)
                        sl = price + (curr["atr"] * 1.2)
                        emoji = "🔴"

                    msg = (
                        f"⚡ **ACTIVE SCALP** {emoji}\n"
                        f"#{name} — {tf}\n"
                        f"🌊 Setup: **{bb_status}**\n"
                        f"📊 RSI: {round(rsi_val,1)}\n"
                        f"💰 Entry: {price}\n"
                        f"🎯 TP: {round(tp,4)}\n🛑 SL: {round(sl,4)}\n"
                        f"🤖 AI: {ai_verdict}"
                    )
                    self.send(msg)
                    self.positions[name] = signal_type 
                    time.sleep(2)
                    break 

    def check_spot(self):
        pass

    def analyze(self):
        self.check_futures()
        self.check_spot()
