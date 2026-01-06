import os
import requests
import time
from openai import OpenAI

# --- КОНФИГУРАЦИЯ ---
# Используем Ticker endpoint для получения данных стакана (Level 1)
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

    # 📊 ПОЛУЧЕНИЕ ДАННЫХ Ticker (ЦЕНА + BID/ASK)
    def get_ticker_data(self, symbol):
        try:
            r = requests.get(OKX_TICKER_URL, params={"instId": symbol}, timeout=5)
            data = r.json().get("data", [])
            if not data: return None
            
            ticker = data[0]
            return {
                "price": float(ticker["last"]),      # Последняя цена сделки
                "bid_px": float(ticker["bidPx"]),    # Цена покупки (лучшая)
                "bid_sz": float(ticker["bidSz"]),    # Объем на покупку (стенка)
                "ask_px": float(ticker["askPx"]),    # Цена продажи (лучшая)
                "ask_sz": float(ticker["askSz"]),    # Объем на продажу (стенка)
            }
        except Exception:
            return None

    # 🔥 AI: ЧТЕНИЕ ПОТОКА ОРДЕРОВ (TAPE READING)
    def ask_ai_orderflow(self, symbol, price, bid_sz, ask_sz, ratio, imbalance):
        strategy_name = "ORDER_FLOW_SCALPER"
        
        print(f"🧠 DeepSeek reading Tape for {symbol} | Ratio: {ratio}...")

        json_template = '{"Confidence": int, "Verdict": "BUY" or "SELL" or "WAIT", "Reason": "text"}'
        
        system_prompt = (
            f"Ты — HFT алгоритм (High Frequency Trading). Ты анализируешь Bid-Ask Ratio и дисбаланс ликвидности.\n"
            f"ТВОЯ ЗАДАЧА: Определить, кто давит на цену прямо сейчас — Покупатели или Продавцы.\n\n"
            f"ДАННЫЕ:\n"
            f"- Bid Volume (Покупатели): Объем заявок на покупку в моменте.\n"
            f"- Ask Volume (Продавцы): Объем заявок на продажу в моменте.\n"
            f"- Ratio: Bid / Ask.\n\n"
            f"ПРАВИЛА:\n"
            f"1. Ratio > 2.0 (Покупателей в 2 раза больше) -> Вероятный РОСТ (BUY).\n"
            f"2. Ratio < 0.5 (Продавцов в 2 раза больше) -> Вероятное ПАДЕНИЕ (SELL).\n"
            f"3. Если Ratio около 1.0 (1.0 - 1.3) -> Рынок в равновесии -> WAIT.\n"
            f"4. Игнорируй мелкие объемы, ищи большие 'стенки'.\n"
            f"ФОРМАТ ОТВЕТА (JSON): {json_template}"
        )

        user_prompt = (
            f"Asset: {symbol}\n"
            f"Current Price: {price}\n"
            f"Bid Size (Buyers): {bid_sz}\n"
            f"Ask Size (Sellers): {ask_sz}\n"
            f"Bid-Ask Ratio: {ratio}\n"
            f"Imbalance Status: {imbalance}\n"
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
                    temperature=0.1 # Нужна максимальная математическая точность
                )
                content = response.choices[0].message.content
                content = content.replace("```json", "").replace("```", "").strip()
                return content, strategy_name
            except Exception:
                time.sleep(1)
                continue
        
        return "Skip", strategy_name

    # --- АНАЛИЗ РЫНКА ---
    def check_market(self):
        print("--- ⚖️ Checking Order Flow & Bid-Ask Ratio ---")
        
        for name, info in FUTURES_SYMBOLS.items():
            symbol = info["id"]
            lev = info["lev"]
            
            # Задержка, чтобы не превысить лимиты API
            time.sleep(0.2) 

            # 1. Получаем "сырые" данные с рынка
            ticker = self.get_ticker_data(symbol)
            if not ticker: continue

            price = ticker["price"]
            bid_sz = ticker["bid_sz"]
            ask_sz = ticker["ask_sz"]

            # 2. Считаем Bid-Ask Ratio
            # Защита от деления на ноль
            if ask_sz == 0: ask_sz = 0.0001 
            ratio = round(bid_sz / ask_sz, 2)

            # 3. Определяем дисбаланс
            imbalance = "NEUTRAL"
            signal_type = None

            # Фильтры для первичного отсева (чтобы не дергать AI зря)
            if ratio >= 2.5: # Покупателей в 2.5 раза больше
                imbalance = "STRONG_BUY_WALL"
                signal_type = "LONG"
            elif ratio <= 0.4: # Продавцов в 2.5 раза больше
                imbalance = "STRONG_SELL_WALL"
                signal_type = "SHORT"
            
            # Если есть сильный перекос в стакане, зовем AI
            if signal_type and self.positions[name] is None:
                
                ai_verdict, strategy_used = self.ask_ai_orderflow(
                    name, price, bid_sz, ask_sz, ratio, imbalance
                )
                
                # Если AI сказал WAIT - пропускаем
                if "WAIT" in str(ai_verdict).upper(): 
                    continue

                # Расчет простых целей (скальпинг)
                # Берем фиксированный % так как ATR у нас больше нет
                take_profit_pct = 0.015  # 1.5% движения цены
                stop_loss_pct = 0.008    # 0.8% стоп

                if signal_type == "LONG":
                    tp = price * (1 + take_profit_pct)
                    sl = price * (1 - stop_loss_pct)
                    emoji = "🟢"
                    title = "BUY PRESSURE"
                    desc = f"Buyers dominate x{ratio}"
                else:
                    tp = price * (1 - take_profit_pct)
                    sl = price * (1 + stop_loss_pct)
                    emoji = "🔴"
                    title = "SELL PRESSURE"
                    desc = f"Sellers dominate (Ratio {ratio})"

                msg = (
                    f"⚡ **{title}** {emoji}\n"
                    f"#{name} — Order Flow\n"
                    f"📊 Bid/Ask Ratio: **{ratio}**\n"
                    f"🧱 Imbalance: {desc}\n"
                    f"💰 Price: {price}\n"
                    f"🎯 TP: {round(tp,5)}\n🛑 SL: {round(sl,5)}\n"
                    f"🤖 AI Verdict: {ai_verdict}"
                )
                self.send(msg)
                
                # Ставим "блокировку" на вход по этой монете на короткое время
                self.positions[name] = signal_type 

            # Сброс позиции (простая логика для примера)
            # В реальности тут нужно отслеживать PnL, но для простого бота сбрасываем флаг,
            # если Ratio вернулся в норму (стал нейтральным)
            elif self.positions[name] is not None:
                if 0.8 < ratio < 1.2:
                    self.positions[name] = None # Сброс, можно снова искать вход

    def analyze(self):
        self.check_market()
