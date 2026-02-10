import os
import requests
import time
import pandas as pd
import pandas_ta as ta
from openai import OpenAI

# --- КОНФИГУРАЦИЯ ---
OKX_URL = "https://www.okx.com/api/v5/market/candles"

# 🔥 СПИСОК ДЛЯ СКАЛЬПИНГА (Волатильность = Прибыль)
FUTURES_SYMBOLS = {
    "BTC":    {"id": "BTC-USDT-SWAP",    "lev": 20},
    "ETH":    {"id": "ETH-USDT-SWAP",    "lev": 20},
    "SOL":    {"id": "SOL-USDT-SWAP",    "lev": 10}, # Техничный
    "PEPE":   {"id": "PEPE-USDT-SWAP",   "lev": 5},  # Бешеный
    "DOGE":   {"id": "DOGE-USDT-SWAP",    "lev": 10}, # Хайповый
}

class TradingAgent:
    def __init__(self, bot_token, chat_id, openai_key):
        self.bot_token = bot_token
        self.chat_id = chat_id
        # Подключение к DeepSeek
        self.client = OpenAI(api_key=openai_key, base_url="https://api.deepseek.com")
        self.positions = {name: None for name in FUTURES_SYMBOLS}
        
        print("🚀 SCALP ANALYZER V3 STARTING...")
        self.check_connection()

    def check_connection(self):
        try:
            self.client.chat.completions.create(
                model="deepseek-chat",
                messages=[{"role": "user", "content": "."}],
                max_tokens=1
            )
            print("✅ DeepSeek AI: Connected")
        except Exception:
            print("⚠️ DeepSeek AI: Error/No Funds (Bot will use TECH-ONLY mode)")

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
            r = requests.get(OKX_URL, params={"instId": symbol, "bar": bar, "limit": limit}, timeout=5)
            data = r.json().get("data", [])
            if not data: return None
            df = pd.DataFrame(data, columns=["ts", "o", "h", "l", "c", "v", "volCcy", "volCcyQuote", "confirm"])
            df = df.iloc[::-1].reset_index(drop=True)
            df[["o", "h", "l", "c", "v"]] = df[["o", "h", "l", "c", "v"]].astype(float)
            return df
        except: return None

    # 🔥 МОЗГ СКАЛЬПЕРА
    def ask_ai(self, symbol, price, rsi, setup, direction):
        strategy_name = "SCALP_HFT"
        
        # Промпт: Жесткий, быстрый, без воды
        system_prompt = (
            f"You are a High-Frequency Scalper. Asset: {symbol}.\n"
            f"Pattern: {setup} ({direction}). Indicators: RSI={rsi}.\n"
            f"Task: Confirm entry. Keep it aggressive.\n"
            f"Output JSON: {{'Verdict': 'BUY/SELL', 'Reason': '3 words'}}"
        )
        
        try:
            response = self.client.chat.completions.create(
                model="deepseek-chat",
                messages=[{"role": "system", "content": system_prompt}],
                max_tokens=60,
                temperature=0.3
            )
            content = response.choices[0].message.content
            return content, strategy_name
        except Exception:
            # Если AI не отвечает - возвращаем технический сигнал
            return f"{{'Verdict': '{direction}', 'Reason': 'Tech Only'}}", "TECH_FAILSAFE"

    def analyze_market(self):
        print("\n--- ⚡ Scanning 5m Charts ---")
        timeframes = ["5m"] # Скальпинг только на 5 минутах
        
        for name, info in FUTURES_SYMBOLS.items():
            symbol = info["id"]
            lev = info["lev"]
            
            # Пропускаем, если уже дали сигнал (чтобы не спамить)
            # В реале можно добавить проверку: если цена ушла на 1%, сбрасываем флаг
            if self.positions[name] is not None:
                continue

            for tf in timeframes:
                time.sleep(0.15) # Анти-бан от OKX
                df = self.get_candles(symbol, tf, limit=50)
                if df is None: continue

                # --- ИНДИКАТОРЫ ---
                # 1. RSI (Индекс силы)
                df["rsi"] = ta.rsi(df["c"], length=14)
                
                # 2. Bollinger Bands (Канал волатильности)
                bb = ta.bbands(df["c"], length=20, std=2.0)
                if bb is None: continue
                lower = bb[f"BBL_20_2.0"].iloc[-1]
                upper = bb[f"BBU_20_2.0"].iloc[-1]
                
                # 3. ATR (Для расчета целей)
                df["atr"] = ta.atr(df["h"], df["l"], df["c"], length=14)

                curr = df.iloc[-1]
                rsi_val = round(curr["rsi"], 1)
                price = curr["c"]
                atr = curr["atr"]

                # Вывод в консоль для контроля
                print(f"🔎 {name}: RSI={rsi_val} | Price={price}")

                signal_type = None
                setup_name = ""
                
                # --- ЛОГИКА ВХОДА (SCALP LOGIC) ---
                
                # 1. ОТСКОК ОТ ДНА (Mean Reversion)
                # Цена коснулась нижней линии Боллинджера + RSI < 45 (не ждем 30, берем раньше)
                if price <= (lower * 1.001) and rsi_val < 45:
                    signal_type = "LONG"
                    setup_name = "Bollinger Bottom Bounce"

                # 2. ПРОБОЙ ПОТОЛКА (Short Squeeze)
                # Цена коснулась верха + RSI > 55
                elif price >= (upper * 0.999) and rsi_val > 55:
                    signal_type = "SHORT"
                    setup_name = "Bollinger Top Reject"
                
                # 3. ЭКСТРЕМАЛЬНЫЙ RSI (Ловля ножей)
                elif rsi_val < 25:
                    signal_type = "LONG"
                    setup_name = "Oversold Crash (RSI < 25)"
                elif rsi_val > 75:
                    signal_type = "SHORT"
                    setup_name = "Overbought Pump (RSI > 75)"

                # --- ЕСЛИ ЕСТЬ СИГНАЛ ---
                if signal_type:
                    print(f"🔥 Signal found: {setup_name}. Asking AI...")
                    
                    ai_resp, strat = self.ask_ai(name, price, rsi_val, setup_name, signal_type)
                    
                    # Проверка ответа AI
                    verdict_up = str(ai_resp).upper()
                    # Если AI говорит WAIT/HOLD - пропускаем
                    if "WAIT" in verdict_up or "HOLD" in verdict_up:
                        print("⛔ AI blocked trade.")
                        continue

                    # Расчет TP/SL (Скальпинг)
                    # Тейк = 1.5 ATR (быстро забрать)
                    # Стоп = 1.0 ATR (быстро выйти если не пошло)
                    atr_tp_mult = 1.5
                    atr_sl_mult = 1.2
                    
                    if signal_type == "LONG":
                        tp = price + (atr * atr_tp_mult)
                        sl = price - (atr * atr_sl_mult)
                        emoji = "🟢"
                    else:
                        tp = price - (atr * atr_tp_mult)
                        sl = price + (atr * atr_sl_mult)
                        emoji = "🔴"

                    # Формируем красивое сообщение
                    msg = (
                        f"⚡ **SCALP SIGNAL** {emoji}\n"
                        f"#{name} — 5m\n"
                        f"🌊 Setup: **{setup_name}**\n"
                        f"📊 RSI: {rsi_val}\n"
                        f"💰 Entry: {price}\n"
                        f"🎯 TP: {round(tp, 5)}\n🛑 SL: {round(sl, 5)}\n"
                        f"🤖 AI: {ai_resp}"
                    )
                    
                    self.send(msg)
                    self.positions[name] = signal_type # Блокируем повтор
                    print("✅ Signal sent to Telegram!")
                    time.sleep(1)

                # --- СБРОС БЛОКИРОВКИ ---
                # Если RSI вернулся в норму (45-55), разрешаем новый сигнал
                elif self.positions[name] is not None:
                    if 45 < rsi_val < 55:
                        self.positions[name] = None
                        print(f"♻️ {name} ready for new signals.")
