import os
import requests
import pandas as pd
import pandas_ta as ta
from datetime import datetime
from openai import OpenAI  # 🆕 Импорт клиента OpenAI

OKX_URL = "https://www.okx.com/api/v5/market/candles"

SYMBOLS = {
    "ETH": "ETH-USDT-SWAP",
    "ARB": "ARB-USDT-SWAP",
    "OP": "OP-USDT-SWAP",
    "LDO": "LDO-USDT-SWAP",
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
    def ask_ai(self, symbol, side, price, rsi, atr, trend_strength):
        print(f"🧠 Asking AI about {symbol}...")
        
        prompt = f"""
        Ты профессиональный крипто-трейдер. Оцени сделку.
        
        Вводные данные:
        - Тикер: {symbol}
        - Сигнал: {side} (Технический анализ сработал)
        - Цена: {price}
        - RSI (14): {rsi}
        - ATR (волатильность): {atr}
        - Сила тренда (разрыв EMA): {trend_strength}%
        
        Задача:
        1. Оцени риск сделки от 1 до 10.
        2. Дай краткий комментарий (1 предложение), стоит ли входить или это ложный сигнал.
        3. Если RSI в экстремальной зоне (>70 для Long или <30 для Short), предупреди об опасности.
        
        Ответ верни в формате:
        Risk: [Число]/10
        Verdict: [Текст]
        """

        try:
            response = self.client.chat.completions.create(
                model="gpt-4o-mini", # Дешевая и быстрая модель
                messages=[{"role": "user", "content": prompt}],
                max_tokens=100
            )
            return response.choices[0].message.content
        except Exception as e:
            return f"AI Error: {e}"

    def analyze(self):
        print(f"--- AI Analysis Loop {datetime.now().strftime('%H:%M')} ---")
        
        for name, symbol in SYMBOLS.items():
            df = self.get_data(symbol)
            if df is None: continue

            # Расчет индикаторов
            df["ema_fast"] = ta.ema(df["c"], length=21)
            df["ema_slow"] = ta.ema(df["c"], length=50)
            df["rsi"] = ta.rsi(df["c"], length=14)
            df["atr"] = ta.atr(df["h"], df["l"], df["c"], length=14)

            curr = df.iloc[-2] # Последняя закрытая свеча
            
            # Логика сигналов
            signal = None
            if curr["ema_fast"] > curr["ema_slow"] and curr["rsi"] < 70:
                signal = "BUY"
            elif curr["ema_fast"] < curr["ema_slow"] and curr["rsi"] > 30:
                signal = "SELL"

            # Если есть НОВЫЙ сигнал
            if signal and self.positions[name] != signal:
                
                # Рассчитываем "Силу тренда" для ИИ (насколько широко разошлись EMA)
                trend_diff = abs(curr["ema_fast"] - curr["ema_slow"]) / curr["c"] * 100
                
                # 🧠 СПРАШИВАЕМ ИИ
                ai_analysis = self.ask_ai(
                    symbol=name, 
                    side=signal, 
                    price=curr["c"], 
                    rsi=round(curr["rsi"], 1), 
                    atr=round(curr["atr"], 4),
                    trend_strength=round(trend_diff, 3)
                )

                # Формируем стопы
                if signal == "BUY":
                    sl = curr["c"] - (curr["atr"] * 2)
                    tp = curr["c"] + (curr["atr"] * 3)
                else:
                    sl = curr["c"] + (curr["atr"] * 2)
                    tp = curr["c"] - (curr["atr"] * 3)

                # Отправляем в Telegram с мнением ИИ
                msg = (
                    f"🤖 **AI TRADING SIGNAL**\n"
                    f"#{name} — {signal}\n\n"
                    f"💰 Price: `{curr['c']}`\n"
                    f"🎯 TP: `{round(tp,4)}`\n"
                    f"🛑 SL: `{round(sl,4)}`\n"
                    f"📊 Techs: RSI {round(curr['rsi'],1)} | ATR {round(curr['atr'],4)}\n\n"
                    f"🧠 **AI Opinion:**\n{ai_analysis}"
                )
                
                self.send(msg)
                self.positions[name] = signal # Запоминаем

            elif signal is None:
                pass
