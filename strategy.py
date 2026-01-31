from lumibot.strategies import Strategy
from lumibot.entities import Asset
from datetime import datetime
import pandas_ta as ta
import pandas as pd
from openai import OpenAI
import requests
import time

class DeepSeekScalper(Strategy):
    # Параметры стратегии по умолчанию
    parameters = {
        "symbol": "BTC/USDT",      # Торгуемая пара (формат CCXT)
        "timeframe": "5m",         # Таймфрейм
        "deepseek_key": "",        # Ключ AI
        "telegram_token": "",      # Токен ТГ
        "chat_id": ""              # ID чата
    }

    def initialize(self):
        # Инициализация (запускается  один раз при старте)
        self.sleeptime = "5m"  # Частота проверки (совпадает с таймфреймом)
        self.client = OpenAI(
            api_key=self.parameters["deepseek_key"], 
            base_url="https://api.deepseek.com"
        )
        self.set_market(self.parameters["symbol"]) 

    def send_telegram(self, message):
        try:
            token = self.parameters["telegram_token"]
            chat = self.parameters["chat_id"]
            url = f"https://api.telegram.org/bot{token}/sendMessage"
            requests.post(url, json={"chat_id": chat, "text": message, "parse_mode": "Markdown"})
        except: pass

    def ask_deepseek(self, price, rsi, bb_status):
        # Спрашиваем мнение AI
        json_tmpl = '{"Verdict": "BUY" or "SELL", "Reason": "text"}'
        system = (
            f"You are a Scalper Bot. Asset: {self.parameters['symbol']}.\n"
            f"Strategy: Bollinger Band Breakout.\n"
            f"Conditions: Price hit {bb_status}. RSI={rsi}.\n"
            f"Task: Decide trade direction immediately. Format: {json_tmpl}"
        )
        try:
            response = self.client.chat.completions.create(
                model="deepseek-chat",
                messages=[
                    {"role": "system", "content": system},
                    {"role": "user", "content": f"Price {price}. Action?"}
                ],
                max_tokens=100
            )
            return response.choices[0].message.content
        except Exception as e:
            return f"Error: {e}"

    def on_trading_iteration(self):
        # ЭТА ФУНКЦИЯ ЗАПУСКАЕТСЯ КАЖДЫЕ 5 МИНУТ
        
        symbol = self.parameters["symbol"]
        
        # 1. Получаем исторические данные (свечи)
        # Берем 50 свечей для расчета индикаторов
        bars = self.get_historical_prices(symbol, 50, "5m")
        if bars is None or len(bars) < 20: 
            return

        df = bars.df
        
        # 2. Считаем индикаторы (Pandas TA)
        # Полосы Боллинджера
        bb = ta.bbands(df["close"], length=20, std=2.0)
        df = pd.concat([df, bb], axis=1)
        # RSI
        df["rsi"] = ta.rsi(df["close"], length=14)
        # ATR (для стопов)
        df["atr"] = ta.atr(df["high"], df["low"], df["close"], length=14)

        last = df.iloc[-1]
        price = last["close"]
        rsi = round(last["rsi"], 1)
        
        # Имена колонок в pandas_ta для BB (зависят от версии, обычно BBL_20_2.0)
        lower_band = last["BBL_20_2.0"]
        upper_band = last["BBU_20_2.0"]
        atr = last["atr"]

        # 3. Логика Сигналов
        signal = None
        setup = ""
        
        # LONG: Касание низа + RSI < 50
        if price <= lower_band and rsi < 50:
            signal = "BUY"
            setup = "Lower BB Touch"
            
        # SHORT: Касание верха + RSI > 50
        elif price >= upper_band and rsi > 50:
            signal = "SELL"
            setup = "Upper BB Touch"

        # 4. Исполнение
        current_position = self.get_position(symbol)
        
        if signal:
            # Спрашиваем AI
            ai_resp = self.ask_deepseek(price, rsi, setup)
            
            # Если позиций нет - открываем
            if current_position is None:
                if "BUY" in str(ai_resp).upper() and signal == "BUY":
                    # Расчет TP/SL
                    tp_price = price + (atr * 2.0)
                    sl_price = price - (atr * 1.5)
                    
                    # Отправка ордера через Lumibot
                    order = self.create_order(
                        symbol, 
                        quantity=0.01, # ⚠️ Настройте объем (в лотах/монетах)
                        side="buy", 
                        take_profit_price=tp_price, 
                        stop_loss_price=sl_price
                    )
                    self.submit_order(order)
                    self.send_telegram(f"🟢 **LUMIBOT LONG**\n#{symbol}\nPrice: {price}\nAI: {ai_resp}")

                elif "SELL" in str(ai_resp).upper() and signal == "SELL":
                    tp_price = price - (atr * 2.0)
                    sl_price = price + (atr * 1.5)
                    
                    order = self.create_order(
                        symbol, 
                        quantity=0.01, # ⚠️ Настройте объем
                        side="sell", 
                        take_profit_price=tp_price, 
                        stop_loss_price=sl_price
                    )
                    self.submit_order(order)
                    self.send_telegram(f"🔴 **LUMIBOT SHORT**\n#{symbol}\nPrice: {price}\nAI: {ai_resp}")

        # P.S. Lumibot сам закроет позицию по TP/SL, нам не нужно писать логику выхода
