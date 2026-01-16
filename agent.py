import os
import requests
import time
import pandas as pd
import pandas_ta as ta
from openai import OpenAI

# --- КОНФИГУРАЦИЯ ---
OKX_URL = "https://www.okx.com/api/v5/market/candles"
DEBUG_MODE = True  # Включили подробный лог

# 1. 🚜 СПИСОК ФЬЮЧЕРСОВ
FUTURES_SYMBOLS = {
    "BTC":    {"id": "BTC-USDT-SWAP",    "lev": 20},
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
    "LAB":    {"id": "LAB-USDT-SWAP",    "lev": 20},
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
        
        # 🔥 ПРОВЕРКА ПОДКЛЮЧЕНИЯ ПРИ СТАРТЕ
        self.test_connection()

    def test_connection(self):
        print("🔍 DIAGNOSTIC: Testing connections...")
        # 1. Проверка OKX
        try:
            r = requests.get(OKX_URL, params={"instId": "BTC-USDT-SWAP", "bar": "15m", "limit": 1}, timeout=5)
            if r.status_code == 200:
                print("✅ OKX API: Connected (Data received)")
            else:
                print(f"❌ OKX API: Error {r.status_code}")
        except Exception as e:
            print(f"❌ OKX API: Connection Failed ({e})")

        # 2. Проверка DeepSeek
        try:
            print("⏳ Testing DeepSeek AI...")
            response = self.client.chat.completions.create(
                model="deepseek-chat",
                messages=[{"role": "user", "content": "Say 'OK'"}],
                max_tokens=5
            )
            print(f"✅ DeepSeek API: Connected (Answer: {response.choices[0].message.content})")
        except Exception as e:
            print(f"❌ DeepSeek API: Error ({e}) - Check your API KEY!")

    def send(self, text):
        try:
            requests.post(
                f"https://api.telegram.org/bot{self.bot_token}/sendMessage", 
                json={"chat_id": self.chat_id, "text": text, "parse_mode": "Markdown"}, 
                timeout=5
            )
        except Exception as e:
            print(f"❌ Telegram Error: {e}")

    def get_candles(self, symbol, bar, limit=100):
        try:
            r = requests.get(OKX_URL, params={"instId": symbol, "bar": bar, "limit": limit}, timeout=10)
            data = r.json().get("data", [])
            if not data: 
                print(f"⚠️ No data for {symbol}")
                return None
            df = pd.DataFrame(data, columns=["ts", "o", "h", "l", "c", "v", "volCcy", "volCcyQuote", "confirm"])
            df = df.iloc[::-1].reset_index(drop=True)
            df[["o", "h", "l", "c", "v"]] = df[["o", "h", "l", "c", "v"]].astype(float)
            return df
        except Exception as e:
            print(f"⚠️ Error fetching candles: {e}")
            return None

    def ask_ai(self, mode, symbol, price, rsi, adx, trend, direction):
        strategy_name = "SCALP_MULTI_TF"
        
        # Определяем стиль торговли от таймфрейма (передается в аргументе trend или direction)
        # Если таймфрейм 5m - режим "Aggressive", если 15m - "Conservative"
        tf_mode = "AGGRESSIVE (Fast entry)" if "5m" in trend else "CONFIRMATION (Trend follow)"

        print(f"⚡ AI Analyzing {symbol} [{tf_mode}]...")

        json_template = '{"Confidence": int, "Verdict": "BUY" or "SELL" or "WAIT", "Reason": "text"}'
        
        system_prompt = (
            f"Ты — Профессиональный Скальпер. Твой режим: {tf_mode}.\n"
            f"АКТИВ: {symbol}. ЦЕНА: {price}.\n"
            f"ИНДИКАТОРЫ: RSI={rsi}, ADX={adx}.\n\n"
            f"ПРАВИЛА ДЛЯ 5m (Минутки):\n"
            f"1. Ищи быстрые отскоки (RSI < 25 или RSI > 75). Это твои лучшие входы.\n"
            f"2. Если ADX > 30 — входи на пробой EMA, не бойся перекупленности.\n"
            f"3. Твой TP короткий (0.5-1%), SL жесткий.\n\n"
            f"ПРАВИЛА ДЛЯ 15m:\n"
            f"1. Это подтверждение тренда. Если RSI нейтрален (45-55) — WAIT.\n"
            f"2. Входи только если тренд совпадает с 5m.\n"
            f"ФОРМАТ ОТВЕТА (JSON): {json_template}"
        )
        
        user_prompt = f"Price: {price}. Should we enter {direction}?"

        for i in range(2):
            try:
                response = self.client.chat.completions.create(
                    model="deepseek-chat",
                    messages=[
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": user_prompt}
                    ],
                    max_tokens=150,
                    temperature=0.3
                )
                content = response.choices[0].message.content
                content = content.replace("```json", "").replace("```", "").strip()
                return content, strategy_name
            except Exception as e:
                print(f"❌ AI Request Failed: {e}")
                time.sleep(1)
                continue
        
        return "Skip", strategy_name

    def check_futures(self):
        print("--- ⚡ Checking Futures (Scalping 5m & 15m) ---")
        # Используем 5 минут для быстрых сделок
        timeframes = ["5m", "15m"]
        
        for name, info in FUTURES_SYMBOLS.items():
            symbol = info["id"]
            lev = info["lev"]
            
            # 🔥 ВАЖНО: Сбрасываем позицию для теста, если она была "залипшей"
            # В реальной торговле тут должна быть проверка PnL, но пока просто логируем
            if self.positions[name] is not None:
                print(f"ℹ️ {name} is already in position ({self.positions[name]}). Skipping.")
                # Раскомментируйте строчку ниже, если хотите принудительно сбросить память бота:
                # self.positions[name] = None 
                continue

            for tf in timeframes:
                time.sleep(0.2)
                df = self.get_candles(symbol, tf, limit=100)
                if df is None: continue

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

                # ЛОГИРУЕМ ИНДИКАТОРЫ В КОНСОЛЬ
                print(f"🔎 {name}: RSI={round(rsi_val,1)} | ADX={round(adx_val,1)} | EMA_Diff={round(curr['ema_f'] - curr['ema_s'], 2)}")

                signal_type = None
                
                # --- ОСЛАБЛЕННЫЕ УСЛОВИЯ (LITE MODE) ---
                
                # 1. EMA CROSS (Трендовая)
                # Убрали RSI < 82, сделали мягче (RSI < 85)
                # Убрали условие ADX для теста, пусть заходит на пересечении
                if (curr["ema_f"] > curr["ema_s"]):
                    signal_type = "LONG_CROSS"
                
                elif (curr["ema_f"] < curr["ema_s"]):
                    signal_type = "SHORT_CROSS"

                # 2. RSI REVERSAL (Контртренд)
                if rsi_val < 30:
                    signal_type = "LONG_OVERSOLD"
                elif rsi_val > 75: # Было 82, сделал мягче
                    signal_type = "SHORT_OVERBOUGHT"

                if signal_type:
                    print(f"✨ Potential Signal found: {signal_type}. Asking AI...")
                    
                    ai_verdict, strategy_used = self.ask_ai(
                        "FUTURES", name, price, round(rsi_val,1), round(adx_val,1), 
                        f"{tf}", signal_type
                    )
                    
                    print(f"🤖 AI Verdict: {ai_verdict}")

                    verdict_up = str(ai_verdict).upper()
                    if "WAIT" in verdict_up or "SKIP" in verdict_up: 
                        print("⛔ AI said WAIT. Not sending.")
                        continue

                    atr_mult = 2.0
                    
                    if "LONG" in signal_type:
                        tp = price + (curr["atr"] * atr_mult)
                        sl = price - (curr["atr"] * 1.5)
                        emoji = "🟢"
                    else:
                        tp = price - (curr["atr"] * atr_mult)
                        sl = price + (curr["atr"] * 1.5)
                        emoji = "🔴"

                    msg = (
                        f"⚡ **SIGNAL: {signal_type}** {emoji}\n"
                        f"#{name} — {tf}\n"
                        f"📊 RSI: {round(rsi_val,1)} | ADX: {round(adx_val,1)}\n"
                        f"💰 Price: {price}\n"
                        f"🎯 TP: {round(tp,2)}\n🛑 SL: {round(sl,2)}\n"
                        f"📝 AI: {ai_verdict}"
                    )
                    self.send(msg)
                    self.positions[name] = signal_type 
                    print(f"✅ Message sent for {name}!")
                    time.sleep(2)
                    break
                else:
                    print(f"😴 No setup for {name}")

    def check_spot(self):
        # Спот пока пропустим, фокус на фьючерсах
        pass

    def analyze(self):
        self.check_futures()
        self.check_spot()
