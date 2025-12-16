import requests
import time
import pandas as pd
import pandas_ta as ta
from datetime import datetime, timezone

OKX_URL = "https://www.okx.com/api/v5/market/candles"

SYMBOLS = {
    "ETH": "ETH-USDT-SWAP",
    "ARB": "ARB-USDT-SWAP",
    "OP": "OP-USDT-SWAP",
    "LDO": "LDO-USDT-SWAP",
    "UNI": "UNI-USDT-SWAP",
}

INTERVAL = "15m"

class TradingAgent:
    def __init__(self, bot_token, chat_id):
        self.bot_token = bot_token
        self.chat_id = chat_id
        # Память бота: храним состояние, чтобы не спамить сигналами
        # Структура: {'ETH': 'BUY', 'ARB': None ...}
        self.positions = {symbol: None for symbol in SYMBOLS} 

    def send(self, text):
        url = f"https://api.telegram.org/bot{self.bot_token}/sendMessage"
        try:
            requests.post(url, json={"chat_id": self.chat_id, "text": text}, timeout=5)
        except Exception as e:
            print(f"Telegram Error: {e}")

    def get_data(self, symbol):
        try:
            r = requests.get(
                OKX_URL,
                params={"instId": symbol, "bar": INTERVAL, "limit": 100},
                timeout=10
            )
            r.raise_for_status()
            data = r.json().get("data", [])
            if not data:
                return None
            
            # Создаем DataFrame для удобной работы
            df = pd.DataFrame(data, columns=["ts", "o", "h", "l", "c", "v", "volCcy", "volCcyQuote", "confirm"])
            df = df.iloc[::-1].reset_index(drop=True) # Разворачиваем (старые сверху)
            df["c"] = df["c"].astype(float)
            df["h"] = df["h"].astype(float)
            df["l"] = df["l"].astype(float)
            return df
        except Exception as e:
            print(f"API Error {symbol}: {e}")
            return None

    def analyze(self):
        print(f"--- Analysis started at {datetime.now().strftime('%H:%M:%S')} ---")
        
        for name, symbol in SYMBOLS.items():
            df = self.get_data(symbol)
            if df is None:
                continue

            # 1. Расчет индикаторов через pandas_ta (быстро и точно)
            df["ema_fast"] = ta.ema(df["c"], length=21)
            df["ema_slow"] = ta.ema(df["c"], length=50)
            df["rsi"] = ta.rsi(df["c"], length=14)
            df["atr"] = ta.atr(df["h"], df["l"], df["c"], length=14)

            # Берем значения последней ЗАКРЫТОЙ свечи (предпоследняя строка, index -2)
            # Последняя строка (index -1) - это текущая еще не закрытая свеча
            curr = df.iloc[-2] 
            price = curr["c"]
            atr = curr["atr"]

            # Логика сигналов
            signal = None
            
            # Условие BUY
            if curr["ema_fast"] > curr["ema_slow"] and curr["rsi"] < 70:
                signal = "BUY"
            
            # Условие SELL
            elif curr["ema_fast"] < curr["ema_slow"] and curr["rsi"] > 30:
                signal = "SELL"

            # 2. Фильтрация повторов (State Management)
            if signal and self.positions[name] != signal:
                
                # Расчет динамического SL/TP на основе ATR (волатильности)
                # Stop Loss = 2 * ATR, Take Profit = 3 * ATR
                if signal == "BUY":
                    sl = price - (atr * 2)
                    tp = price + (atr * 3)
                else:
                    sl = price + (atr * 2)
                    tp = price - (atr * 3)

                # Отправка
                self.send(
                    f"🚀 {name} SIGNAL (Improved)\n"
                    f"📈 {signal}\n"
                    f"💰 Price: {price}\n"
                    f"🎯 TP: {round(tp, 4)} | 🛑 SL: {round(sl, 4)}\n"
                    f"📊 RSI: {round(curr['rsi'], 1)} | ATR: {round(atr, 4)}\n"
                )
                
                # Запоминаем позицию
                self.positions[name] = signal
            
            elif signal is None:
                # Если сигнал пропал (флэт), сбрасываем состояние (опционально)
                # self.positions[name] = None 
                pass

        print("--- Analysis finished ---")
