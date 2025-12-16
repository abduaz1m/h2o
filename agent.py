import time
import os
import requests
import pandas as pd
import pandas_ta as ta
from datetime import datetime
from openai import OpenAI  # 🆕 Импорт клиента OpenAI

OKX_URL = "https://www.okx.com/api/v5/market/candles"

SYMBOLS = {
    "ETH": "ETH-USDT-SWAP",
}

INTERVAL = "15m"

class TradingAgent:
    def __init__(self, bot_token, chat_id, openai_key):
        self.bot_token = bot_token
        self.chat_id = chat_id
        self.client = OpenAI(api_key=openai_key) # 🆕 Инициализация AI
        self.positions = {symbol: None for symbol in SYMBOLS}

    # ... (методы send и get_data остаются теми же, что и в предыдущем ответе) ...
    def send(self, text):
        url = f"https://api.telegram.org/bot{self.bot_token}/sendMessage"
        try:
            requests.post(url, json={"chat_id": self.chat_id, "text": text, "parse_mode": "Markdown"}, timeout=5)
        except Exception as e:
            print(f"Telegram Error: {e}")

    def get_data(self, symbol):
        # (Код получения данных через pandas, см. предыдущий ответ)
        try:
            r = requests.get(OKX_URL, params={"instId": symbol, "bar": INTERVAL, "limit": 100}, timeout=10)
            r.raise_for_status()
            data = r.json().get("data", [])
            if not data: return None
            df = pd.DataFrame(data, columns=["ts", "o", "h", "l", "c", "v", "volCcy", "volCcyQuote", "confirm"])
            df = df.iloc[::-1].reset_index(drop=True)
            df[["o","h","l","c","v"]] = df[["o","h","l","c","v"]].astype(float)
            return df
        except: return None

    # 🆕 НОВЫЙ МЕТОД: Анализ через LLM
# В начало файла agent.py добавьте импорт time, если его нет
    import time 

    # ... (код класса)

    def get_trend_4h(self, symbol):
        try:
            # Запрашиваем 4-часовые свечи
            r = requests.get(
                OKX_URL,
                params={"instId": symbol, "bar": "4H", "limit": 100},
                timeout=10
            )
            r.raise_for_status()
            data = r.json().get("data", [])
            
            if not data:
                return "NEUTRAL"
            
            df = pd.DataFrame(data, columns=["ts", "o", "h", "l", "c", "v", "volCcy", "volCcyQuote", "confirm"])
            df = df.iloc[::-1].reset_index(drop=True)
            df["c"] = df["c"].astype(float)

            # EMA 50 и EMA 200 на 4H — золотой стандарт тренда
            ema50 = ta.ema(df["c"], length=50).iloc[-1]
            ema200 = ta.ema(df["c"], length=200).iloc[-1]

            if ema50 > ema200:
                return "UP"   # Восходящий тренд
            elif ema50 < ema200:
                return "DOWN" # Нисходящий тренд
            else:
                return "NEUTRAL"

        except Exception as e:
            print(f"⚠️ Error getting 4H trend for {symbol}: {e}")
            return "NEUTRAL" # В случае ошибки считаем тренд нейтральным

    # ---------------------------------------------------------
    # 🔄 ОБНОВЛЕННЫЙ МЕТОД ANALYZE (С Фильтром)
    # ---------------------------------------------------------
    def analyze(self):
        print(f"--- 🔍 Analysis Loop {datetime.now().strftime('%H:%M:%S')} ---")
        
        for name, symbol in SYMBOLS.items():
            # 1. Получаем данные 15m (как раньше)
            df = self.get_data(symbol)
            if df is None:
                continue

            # 2. Считаем индикаторы
            df["ema_fast"] = ta.ema(df["c"], length=21)
            df["ema_slow"] = ta.ema(df["c"], length=50)
            df["rsi"] = ta.rsi(df["c"], length=14)
            df["atr"] = ta.atr(df["h"], df["l"], df["c"], length=14)

            # Берем предпоследнюю (закрытую) свечу
            curr = df.iloc[-2]
            price = curr["c"]
            atr = curr["atr"]

            # 3. Ищем первичный сигнал на 15m
            signal = None
            if curr["ema_fast"] > curr["ema_slow"] and curr["rsi"] < 70:
                signal = "BUY"
            elif curr["ema_fast"] < curr["ema_slow"] and curr["rsi"] > 30:
                signal = "SELL"

            # Если сигнала нет — идем к следующей монете
            if signal is None:
                continue

            # 4. 🔥 ФИЛЬТР: Проверяем глобальный тренд ТОЛЬКО если есть сигнал
            if self.positions[name] != signal:
                print(f"🔎 Found {signal} setup for {name}. Checking 4H trend...")
                
                global_trend = self.get_trend_4h(symbol)
                
                # Логика фильтрации
                is_valid = False
                if signal == "BUY" and global_trend in ["UP", "NEUTRAL"]:
                    is_valid = True
                elif signal == "SELL" and global_trend in ["DOWN", "NEUTRAL"]:
                    is_valid = True
                else:
                    print(f"🚫 BLOCKED: {name} Signal {signal} vs Trend {global_trend}")
                    is_valid = False

                if is_valid:
                    # Рассчитываем силу локального тренда для AI
                    trend_diff = abs(curr["ema_fast"] - curr["ema_slow"]) / curr["c"] * 100
                    
                    # 5. Спрашиваем AI (передаем ему и глобальный тренд)
                    # ВАЖНО: Убедитесь, что ваш метод ask_ai принимает аргумент global_trend!
                    ai_analysis = self.ask_ai(
                        symbol=name, 
                        side=signal, 
                        price=price, 
                        rsi=round(curr["rsi"], 1), 
                        atr=round(atr, 4), 
                        trend_strength=round(trend_diff, 3),
                        # global_trend=global_trend # <--- Раскомментируйте, если обновили ask_ai
                    )

                    # 6. Расчет Стопов (ATR)
                    if signal == "BUY":
                        sl = price - (atr * 2)
                        tp = price + (atr * 3)
                    else:
                        sl = price + (atr * 2)
                        tp = price - (atr * 3)

                    # 7. Отправка в Telegram
                    msg = (
                        f"🤖 **SMART TRADER SIGNAL**\n"
                        f"#{name} — {signal}\n"
                        f"🌍 Global Trend (4H): {global_trend}\n\n"
                        f"💰 Entry: `{price}`\n"
                        f"🎯 TP: `{round(tp, 4)}`\n"
                        f"🛑 SL: `{round(sl, 4)}`\n"
                        f"📊 RSI: {round(curr['rsi'], 1)} | ATR: {round(atr, 4)}\n\n"
                        f"🧠 **AI Verdict:**\n{ai_analysis}"
                    )
                    
                    self.send(msg)
                    self.positions[name] = signal
                    
                    # Пауза, чтобы не спамить API, если несколько монет сработали одновременно
                    print("⏳ Cooling down...")
                    time.sleep(3)

            elif signal is None:
                pass
