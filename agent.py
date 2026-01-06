import os
import requests
import time
from openai import OpenAI

# --- КОНФИГУРАЦИЯ ---
# Используем Ticker Endpoint для получения Bid/Ask и цены в реальном времени
OKX_TICKER_URL = "https://www.okx.com/api/v5/market/ticker"

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
}

class TradingAgent:
    def __init__(self, bot_token, chat_id, openai_key):
        self.bot_token = bot_token
        self.chat_id = chat_id
        # Подключение к DeepSeek
        self.client = OpenAI(api_key=openai_key, base_url="https://api.deepseek.com")
        self.positions = {name: None for name in FUTURES_SYMBOLS}

    def send(self, text):
        try:
            requests.post(
                f"https://api.telegram.org/bot{self.bot_token}/sendMessage", 
                json={"chat_id": self.chat_id, "text": text, "parse_mode": "Markdown"}, 
                timeout=5
            )
        except Exception:
            pass

    # 📊 ПОЛУЧЕНИЕ ДАННЫХ (Price + Order Book Depth)
    def get_ticker_data(self, symbol):
        try:
            params = {"instId": symbol}
            r = requests.get(OKX_TICKER_URL, params=params, timeout=5)
            data = r.json().get("data", [])
            if not data: return None
            
            ticker = data[0]
            return {
                "price": float(ticker["last"]),
                "bid_px": float(ticker["bidPx"]), # Цена покупки
                "bid_sz": float(ticker["bidSz"]), # Объем на покупку (Спрос)
                "ask_px": float(ticker["askPx"]), # Цена продажи
                "ask_sz": float(ticker["askSz"])  # Объем на продажу (Предложение)
            }
        except Exception:
            return None

    # 🔥 AI МОЗГ: ORDER FLOW ANALYST
    def ask_ai(self, symbol, price, bid_sz, ask_sz, ratio):
        strategy_name = "ORDER_FLOW_SCALPER"
        
        print(f"🧠 Checking Order Flow for {symbol} (Ratio: {ratio})...")

        json_template = '{"Risk": int, "Verdict": "BUY" or "SELL" or "WAIT", "Reason": "text"}'

        # Промпт теперь смотрит только на стакан
        system_prompt = (
            f"Ты — скальпер, торгующий по стакану (Order Flow).\n"
            f"ТВОЯ ЗАДАЧА: Найти дисбаланс спроса и предложения.\n"
            f"ДАННЫЕ:\n"
            f"- Bid Size (Покупатели): {bid_sz}\n"
            f"- Ask Size (Продавцы): {ask_sz}\n"
            f"- Ratio (Bid/Ask): {ratio}\n\n"
            f"ПРАВИЛА:\n"
            f"1. Ratio > 2.0 -> СИЛЬНОЕ давление покупателей -> BUY.\n"
            f"2. Ratio < 0.5 -> СИЛЬНОЕ давление продавцов -> SELL.\n"
            f"3. Если Ratio между 0.8 и 1.2 -> Рынок в равновесии -> WAIT.\n"
            f"4. Игнорируй мелкие объемы, ищи аномалии.\n"
            f"ФОРМАТ ОТВЕТА (JSON): {json_template}"
        )

        user_prompt = (
            f"Asset: {symbol}\n"
            f"Price: {price}\n"
            f"Order Book State: Bid={bid_sz} vs Ask={ask_sz}\n"
        )

        for i in range(2):
            try:
                response = self.client.chat.completions.create(
                    model="deepseek-chat",
                    messages=[
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": user_prompt}
                    ],
                    max_tokens=150,
                    temperature=0.1 # Максимальная строгость
                )
                content = response.choices[0].message.content
                content = content.replace("```json", "").replace("```", "").strip()
                return content, strategy_name
            except Exception:
                time.sleep(1)
                continue
        
        return "Skip", strategy_name

    def analyze(self):
        print("--- ⚡ Scanning Order Flow (Bid/Ask) ---")
        
        for name, info in FUTURES_SYMBOLS.items():
            symbol = info["id"]
            lev = info["lev"]
            time.sleep(0.1) # Быстрый скан

            data = self.get_ticker_data(symbol)
            if not data: continue

            price = data["price"]
            bid_sz = data["bid_sz"]
            ask_sz = data["ask_sz"]
            
            # Избегаем деления на ноль
            if ask_sz == 0: continue
            
            # 🔥 РАСЧЕТ КОЭФФИЦИЕНТА ДАВЛЕНИЯ
            # Ratio = 1.0 (Равновесие)
            # Ratio = 3.0 (Покупателей в 3 раза больше)
            ratio = round(bid_sz / ask_sz, 2)
            
            signal_type = None

            # Фильтр шума: реагируем только на явный перевес (минимум в 2 раза)
            if ratio >= 2.5:
                signal_type = "LONG"
            elif ratio <= 0.4: # (Это значит Ask в 2.5 раза больше Bid)
                signal_type = "SHORT"

            # Если мы не в позиции и нашли сигнал
            if signal_type and self.positions[name] != signal_type:
                
                # AI подтверждение
                ai_verdict, strategy_used = self.ask_ai(name, price, bid_sz, ask_sz, ratio)
                
                if "WAIT" in str(ai_verdict).upper(): continue

                # Скальперские тейки (очень короткие, так как стакан меняется быстро)
                tp_pct = 0.015  # 1.5% движения цены
                sl_pct = 0.008  # 0.8% стоп

                if signal_type == "LONG":
                    tp = price * (1 + tp_pct)
                    sl = price * (1 - sl_pct)
                    emoji = "🟢"
                    title = "BID WALL DETECTED" # Стена на покупку
                else:
                    tp = price * (1 - tp_pct)
                    sl = price * (1 + sl_pct)
                    emoji = "🔴"
                    title = "ASK WALL DETECTED" # Стена на продажу

                msg = (
                    f"⚡ **{title}** {emoji}\n"
                    f"#{name} — Price: {price}\n"
                    f"⚖️ **Ratio:** {ratio} (Bids vs Asks)\n"
                    f"🌊 Flow: {bid_sz} 🆚 {ask_sz}\n"
                    f"🧠 AI: {ai_verdict}\n"
                    f"🎯 TP: {round(tp,4)} | 🛑 SL: {round(sl,4)}"
                )
                self.send(msg)
                self.positions[name] = signal_type 
                time.sleep(1) # Небольшая пауза после сигнала

            # Если сигнал пропал (давление ушло), сбрасываем позицию (виртуально)
            # Чтобы бот мог снова дать сигнал, если снова появится стена
            elif self.positions[name] and 0.8 < ratio < 1.2:
                self.positions[name] = None
