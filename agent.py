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

# Список тикеров
SYMBOLS = {
    "ETH": "ETH-USDT-SWAP",
    "ARB": "ARB-USDT-SWAP",
    "OP": "OP-USDT-SWAP",
    "LDO": "LDO-USDT-SWAP",
    "UNI": "UNI-USDT-SWAP",
    "BTC": "BTC-USDT-SWAP",
}

class TradingAgent:
    def __init__(self, bot_token, chat_id, openai_key):
        self.bot_token = bot_token
        self.chat_id = chat_id
        # Подключение к AI (можно заменить base_url для DeepSeek, если нужно)
        self.client = OpenAI(api_key=openai_key)
        
        # Память позиций: { 'ETH': 'BUY', ... }
        self.positions = {symbol: None for symbol in SYMBOLS}

    # ---------------------------------------------------
    # 1. ОТПРАВКА В TELEGRAM
    # ---------------------------------------------------
    def send(self, text):
        url = f"https://api.telegram.org/bot{self.bot_token}/sendMessage"
        try:
            requests.post(
                url, 
                json={"chat_id": self.chat_id, "text": text, "parse_mode": "Markdown"}, 
                timeout=5
            )
        except Exception as e:
            print(f"⚠️ Telegram Error: {e}")

    # ---------------------------------------------------
    # 2. ПОЛУЧЕНИЕ ДАННЫХ (15m)
    # ---------------------------------------------------
    def get_data(self, symbol):
        try:
            r = requests.get(
                OKX_URL,
                params={"instId": symbol, "bar": INTERVAL, "limit": 100},
                timeout=10
            )
            r.raise_for_status()
            data = r.json().get("data", [])
            if not data: return None
            
            # DataFrame
            df = pd.DataFrame(data, columns=["ts", "o", "h", "l", "c", "v", "volCcy", "volCcyQuote", "confirm"])
            df = df.iloc[::-1].reset_index(drop=True)
            df[["o", "h", "l", "c", "v"]] = df[["o", "h", "l", "c", "v"]].astype(float)
            return df
        except Exception as e:
            print(f"❌ Data Error {symbol}: {e}")
            return None

    # ---------------------------------------------------
    # 3. ПОЛУЧЕНИЕ ГЛОБАЛЬНОГО ТРЕНДА (4H)
    # ---------------------------------------------------
    def get_trend_4h(self, symbol):
        try:
            r = requests.get(
                OKX_URL,
                params={"instId": symbol, "bar": "4H", "limit": 100},
                timeout=10
            )
            data = r.json().get("data", [])
            if not data: return "NEUTRAL"
            
            df = pd.DataFrame(data, columns=["ts", "o", "h", "l", "c", "v", "volCcy", "volCcyQuote", "confirm"])
            df = df.iloc[::-1].reset_index(drop=True)
            df["c"] = df["c"].astype(float)

            # EMA 50/200 Cross
            ema50 = ta.ema(df["c"], length=50).iloc[-1]
            ema200 = ta.ema(df["c"], length=200).iloc[-1]

            if ema50 > ema200: return "UP"
            if ema50 < ema200: return "DOWN"
            return "NEUTRAL"
        except Exception as e:
            print(f"⚠️ Trend 4H Error {symbol}: {e}")
            return "NEUTRAL"

    # ---------------------------------------------------
    # 4. 🔥 ПРОДВИНУТЫЙ AI АНАЛИЗ (HEDGE FUND PERSONA)
    # ---------------------------------------------------
    def ask_ai(self, symbol, side, price, rsi, atr, trend_strength, global_trend):
        print(f"🧠 AI analyzing {symbol} ({side})...")
        
        # Промпт: Роль Хедж-фонд менеджера
        prompt = f"""
        Ты Риск-менеджер крупного крипто-фонда. Твоя задача — жестко фильтровать сигналы.
        
        ВХОДНЫЕ ДАННЫЕ:
        - Актив: {symbol}
        - Сигнал (15m): {side}
        - Глобальный тренд (4H): {global_trend}
        - Цена: {price}
        - RSI (14): {rsi} (Опасно: >70 для BUY, <30 для SELL)
        - ATR (Волатильность): {atr}
        - Сила импульса: {trend_strength}%
        
        ЗАДАЧА:
        1. Сравни локальный сигнал ({side}) с глобальным трендом ({global_trend}).
        2. Оцени риск входа по шкале 1-10.
        3. Дай вердикт (Одобрено/Отклонено) и краткую причину.
        
        Формат ответа (строго текст):
        Risk: [Число]/10
        Verdict: [Текст вывода]
        Reason: [1 предложение]
        """

        # Попытка запроса с повторами (Retries)
        for i in range(3):
            try:
                response = self.client.chat.completions.create(
                    model="gpt-4o-mini",
                    messages=[{"role": "user", "content": prompt}],
                    max_tokens=150
                )
                return response.choices[0].message.content
            except Exception as e:
                error_str = str(e)
                if "429" in error_str:
                    wait_time = (i + 1) * 3
                    print(f"⚠️ OpenAI Rate Limit (429). Waiting {wait_time}s...")
                    time.sleep(wait_time)
                    continue
                else:
                    return f"❌ AI Error: {e}"
        
        return "⚠️ AI Limit Reached (Skip)"

    # ---------------------------------------------------
    # 5. ОСНОВНОЙ ЦИКЛ
    # ---------------------------------------------------
    def analyze(self):
        print(f"--- 🔍 Analysis Loop {datetime.now().strftime('%H:%M:%S')} ---")
        
        for name, symbol in SYMBOLS.items():
            # Получаем данные
            df = self.get_data(symbol)
            if df is None: continue

            # Индикаторы
            df["ema_fast"] = ta.ema(df["c"], length=21)
            df["ema_slow"] = ta.ema(df["c"], length=50)
            df["rsi"] = ta.rsi(df["c"], length=14)
            df["atr"] = ta.atr(df["h"], df["l"], df["c"], length=14)

            curr = df.iloc[-2] # Закрытая свеча
            price = curr["c"]
            atr = curr["atr"]

            # Логика 15m
            signal = None
            if curr["ema_fast"] > curr["ema_slow"] and curr["rsi"] < 70:
                signal = "BUY"
            elif curr["ema_fast"] < curr["ema_slow"] and curr["rsi"] > 30:
                signal = "SELL"

            if signal is None:
                continue

            # Если сигнал новый
            if self.positions[name] != signal:
                
                # 1. Сначала проверяем тренд 4H
                global_trend = self.get_trend_4h(symbol)
                
                # Фильтр: Не торгуем против тренда
                if signal == "BUY" and global_trend == "DOWN":
                    print(f"🚫 FILTER: {name} BUY blocked by DOWN trend")
                    continue
                if signal == "SELL" and global_trend == "UP":
                    print(f"🚫 FILTER: {name} SELL blocked by UP trend")
                    continue

                # 2. Спрашиваем AI (Только если прошли фильтр тренда)
                trend_diff = abs(curr["ema_fast"] - curr["ema_slow"]) / curr["c"] * 100
                
                ai_verdict = self.ask_ai(
                    symbol=name, 
                    side=signal, 
                    price=price, 
                    rsi=round(curr["rsi"], 1), 
                    atr=round(atr, 4), 
                    trend_strength=round(trend_diff, 3), 
                    global_trend=global_trend # <--- Передаем тренд в AI
                )

                # 3. Расчет Стопов
                if signal == "BUY":
                    sl = price - (atr * 2)
                    tp = price + (atr * 3)
                else:
                    sl = price + (atr * 2)
                    tp = price - (atr * 3)

                # 4. Отправка
                msg = (
                    f"🤖 **AI HEDGE SIGNAL**\n"
                    f"#{name} — {signal}\n"
                    f"🌍 4H Trend: {global_trend}\n\n"
                    f"💰 Entry: `{price}`\n"
                    f"🎯 TP: `{round(tp, 4)}`\n"
                    f"🛑 SL: `{round(sl, 4)}`\n"
                    f"📊 RSI: {round(curr['rsi'], 1)} | ATR: {round(atr, 4)}\n\n"
                    f"🧠 **AI Analysis:**\n{ai_verdict}"
                )
                
                self.send(msg)
                self.positions[name] = signal
                
                # Пауза
                time.sleep(3)
