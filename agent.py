import os
import requests
import time
from openai import OpenAI

# --- КОНФИГУРАЦИЯ ---
OKX_TICKER_URL = "https://www.okx.com/api/v5/market/ticker"

# 1. 🚜 СПИСОК ФЬЮЧЕРСОВ (ТОЛЬКО BTC и ETH)
FUTURES_SYMBOLS = {
    # Для BTC и ETH можно брать плечо побольше, так как они стабильнее
    "BTC":    {"id": "BTC-USDT-SWAP",    "lev": 20}, 
    "ETH":    {"id": "ETH-USDT-SWAP",    "lev": 20},
}

class TradingAgent:
    def __init__(self, bot_token, chat_id, openai_key):
        self.bot_token = bot_token
        self.chat_id = chat_id
        # Стандартный клиент OpenAI (gpt-4o-mini)
        self.client = OpenAI(api_key=openai_key)
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

    def get_ticker_data(self, symbol):
        try:
            r = requests.get(OKX_TICKER_URL, params={"instId": symbol}, timeout=5)
            data = r.json().get("data", [])
            if not data: return None
            
            ticker = data[0]
            return {
                "price": float(ticker["last"]),
                "bid_px": float(ticker["bidPx"]),    # Цена покупки
                "bid_sz": float(ticker["bidSz"]),    # Объем бидов (стенка покупателей)
                "ask_px": float(ticker["askPx"]),    # Цена продажи
                "ask_sz": float(ticker["askSz"]),    # Объем асков (стенка продавцов)
            }
        except Exception:
            return None

    # 🔥 AI: СТРАТЕГИЯ ДЛЯ MAJORS (BTC/ETH)
    def ask_ai_majors(self, symbol, price, bid_sz, ask_sz, ratio, imbalance):
        strategy_name = "MAJORS_LIQUIDITY_HUNT"
        
        print(f"🧠 GPT-4o-mini analyzing {symbol} (Ratio: {ratio})...")

        json_template = '{"Confidence": int, "Verdict": "BUY" or "SELL" or "WAIT", "Reason": "text"}'
        
        system_prompt = (
            f"Ты — профессиональный скальпер по стакану для BTC и ETH.\n"
            f"Твоя особенность: Ты ищешь микро-дисбалансы в ликвидности.\n"
            f"ДАННЫЕ:\n"
            f"- Bid Vol (Покупатели): {bid_sz}\n"
            f"- Ask Vol (Продавцы): {ask_sz}\n"
            f"- Ratio: {ratio}\n\n"
            f"СТРАТЕГИЯ:\n"
            f"1. BTC и ETH — это тяжелые активы. Ratio > 2.0 уже считается сильным сигналом BUY.\n"
            f"2. Ratio < 0.5 — сильный сигнал SELL.\n"
            f"3. Если объемы (bid_sz/ask_sz) аномально маленькие — это манипуляция, WAIT.\n"
            f"4. Твой ответ должен быть JSON: {json_template}"
        )

        user_prompt = f"Analyze liquidity pressure for {symbol}."

        for i in range(2):
            try:
                response = self.client.chat.completions.create(
                    model="gpt-4o-mini",
                    messages=[
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": user_prompt}
                    ],
                    max_tokens=150,
                    temperature=0.1 # Минимум фантазии, максимум логики
                )
                content = response.choices[0].message.content
                content = content.replace("```json", "").replace("```", "").strip()
                return content, strategy_name
            except Exception:
                time.sleep(1)
                continue
        
        return "Skip", strategy_name

    def check_market(self):
        print("--- ⚖️ Checking Majors (BTC/ETH) ---")
        
        for name, info in FUTURES_SYMBOLS.items():
            symbol = info["id"]
            
            time.sleep(0.3) 
            ticker = self.get_ticker_data(symbol)
            if not ticker: continue

            price = ticker["price"]
            bid_sz = ticker["bid_sz"]
            ask_sz = ticker["ask_sz"]

            if ask_sz == 0: ask_sz = 0.0001 
            ratio = round(bid_sz / ask_sz, 2)

            signal_type = None
            
            # --- ЛОГИКА ДЛЯ BTC/ETH ---
            # Для биткоина и эфира ratio 2.0 это уже много (на альтах бывает и 10.0)
            if ratio >= 2.0:
                signal_type = "LONG"
            elif ratio <= 0.5:
                signal_type = "SHORT"
            
            # Если есть сигнал и мы еще не в позиции
            if signal_type and self.positions[name] is None:
                
                ai_verdict, strategy_used = self.ask_ai_majors(
                    name, price, bid_sz, ask_sz, ratio, signal_type
                )
                
                verdict_up = str(ai_verdict).upper()
                
                # Фильтр ответов AI
                if "SKIP" in verdict_up or "WAIT" in verdict_up or "NEUTRAL" in verdict_up or "ERROR" in verdict_up:
                    print(f"🛑 AI Blocked {name}: {ai_verdict}")
                    continue
                
                if signal_type == "LONG" and "BUY" not in verdict_up:
                    continue
                if signal_type == "SHORT" and "SELL" not in verdict_up:
                    continue

                # --- НАСТРОЙКИ РИСК-МЕНЕДЖМЕНТА ДЛЯ MAJORS ---
                # BTC и ETH ходят медленнее, поэтому цели короче, но плечо больше (20x)
                take_profit_pct = 0.006  # 0.6% движения цены (с 20x плечом это 12% профита)
                stop_loss_pct = 0.004    # 0.4% стоп (с 20x плечом это 8% убытка)

                if signal_type == "LONG":
                    tp = price * (1 + take_profit_pct)
                    sl = price * (1 - stop_loss_pct)
                    emoji = "🟢"
                    title = "LIQUIDITY BUY"
                else:
                    tp = price * (1 - take_profit_pct)
                    sl = price * (1 + stop_loss_pct)
                    emoji = "🔴"
                    title = "LIQUIDITY SELL"

                msg = (
                    f"👑 **{title}** {emoji}\n"
                    f"#{name} — Majors Scalp\n"
                    f"⚖️ Ratio: **{ratio}**\n"
                    f"🌊 Flow: {bid_sz} 🆚 {ask_sz}\n"
                    f"💰 Price: {price}\n"
                    f"🎯 TP: {round(tp,2)} | 🛑 SL: {round(sl,2)}\n"
                    f"🧠 AI: {ai_verdict}"
                )
                self.send(msg)
                self.positions[name] = signal_type 

            # --- СБРОС ПОЗИЦИИ ---
            elif self.positions[name] is not None:
                # Для BTC/ETH сброс должен быть чувствительнее
                if self.positions[name] == "LONG" and ratio < 1.2:
                     self.positions[name] = None 
                elif self.positions[name] == "SHORT" and ratio > 0.8:
                     self.positions[name] = None

    def analyze(self):
        self.check_market()
