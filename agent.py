import os
import requests
import time
from openai import OpenAI

# --- КОНФИГУРАЦИЯ ---
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

    def get_ticker_data(self, symbol):
        try:
            r = requests.get(OKX_TICKER_URL, params={"instId": symbol}, timeout=5)
            data = r.json().get("data", [])
            if not data: return None
            
            ticker = data[0]
            return {
                "price": float(ticker["last"]),
                "bid_px": float(ticker["bidPx"]),
                "bid_sz": float(ticker["bidSz"]),
                "ask_px": float(ticker["askPx"]),
                "ask_sz": float(ticker["askSz"]),
            }
        except Exception:
            return None

    def ask_ai_orderflow(self, symbol, price, bid_sz, ask_sz, ratio, imbalance):
        strategy_name = "ORDER_FLOW_SCALPER"
        
        print(f"🧠 DeepSeek analyzing {symbol} (Ratio: {ratio})...")

        json_template = '{"Confidence": int, "Verdict": "BUY" or "SELL" or "WAIT", "Reason": "text"}'
        
        system_prompt = (
            f"Ты — HFT алгоритм. Анализируй дисбаланс в стакане.\n"
            f"ДАННЫЕ:\n"
            f"- Bid Volume: {bid_sz}\n"
            f"- Ask Volume: {ask_sz}\n"
            f"- Ratio: {ratio}\n\n"
            f"ПРАВИЛА:\n"
            f"1. Ratio > 3.0 -> BUY (Покупатели давят).\n"
            f"2. Ratio < 0.3 -> SELL (Продавцы давят).\n"
            f"3. Если дисбаланс слабый или AI не уверен -> верни WAIT.\n"
            f"4. Твой ответ должен быть JSON: {json_template}"
        )

        user_prompt = f"Analyze {symbol} Order Flow."

        for i in range(2):
            try:
                response = self.client.chat.completions.create(
                    model="deepseek-chat",
                    messages=[
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": user_prompt}
                    ],
                    max_tokens=150,
                    temperature=0.1
                )
                content = response.choices[0].message.content
                content = content.replace("```json", "").replace("```", "").strip()
                return content, strategy_name
            except Exception:
                time.sleep(1)
                continue
        
        return "Skip", strategy_name

    def check_market(self):
        print("--- ⚖️ Checking Order Flow ---")
        
        for name, info in FUTURES_SYMBOLS.items():
            symbol = info["id"]
            
            time.sleep(0.2) 
            ticker = self.get_ticker_data(symbol)
            if not ticker: continue

            price = ticker["price"]
            bid_sz = ticker["bid_sz"]
            ask_sz = ticker["ask_sz"]

            if ask_sz == 0: ask_sz = 0.0001 
            ratio = round(bid_sz / ask_sz, 2)

            signal_type = None
            desc = ""

            # Пороги входа
            if ratio >= 2.5:
                signal_type = "LONG"
                desc = f"Strong Bids (x{ratio})"
            elif ratio <= 0.4:
                signal_type = "SHORT"
                desc = f"Strong Asks (x{ratio})"
            
            # --- ЛОГИКА ВХОДА ---
            if signal_type and self.positions[name] is None:
                
                ai_verdict, strategy_used = self.ask_ai_orderflow(
                    name, price, bid_sz, ask_sz, ratio, signal_type
                )
                
                # 🔥 ИСПРАВЛЕНИЕ: ЖЕСТКАЯ ПРОВЕРКА ОТВЕТА
                verdict_up = str(ai_verdict).upper()
                
                # Если AI сказал Skip, Wait, Neutral или произошла ошибка - ИГНОРИРУЕМ
                if "SKIP" in verdict_up or "WAIT" in verdict_up or "NEUTRAL" in verdict_up or "ERROR" in verdict_up:
                    print(f"🛑 AI Blocked {name}: {ai_verdict}")
                    continue
                
                # Если сигнал LONG, а AI не сказал BUY - игнорируем
                if signal_type == "LONG" and "BUY" not in verdict_up:
                    print(f"🛑 AI disagree with LONG on {name}")
                    continue

                # Если сигнал SHORT, а AI не сказал SELL - игнорируем
                if signal_type == "SHORT" and "SELL" not in verdict_up:
                    print(f"🛑 AI disagree with SHORT on {name}")
                    continue

                # Если все проверки пройдены - отправляем
                take_profit_pct = 0.015
                stop_loss_pct = 0.008

                if signal_type == "LONG":
                    tp = price * (1 + take_profit_pct)
                    sl = price * (1 - stop_loss_pct)
                    emoji = "🟢"
                    title = "BID WALL DETECTED"
                else:
                    tp = price * (1 - take_profit_pct)
                    sl = price * (1 + stop_loss_pct)
                    emoji = "🔴"
                    title = "ASK WALL DETECTED"

                msg = (
                    f"⚡ **{title}** {emoji}\n"
                    f"#{name} — Order Flow\n"
                    f"⚖️ Ratio: **{ratio}**\n"
                    f"🌊 Flow: {bid_sz} 🆚 {ask_sz}\n"
                    f"💰 Price: {price}\n"
                    f"🎯 TP: {round(tp,5)} | 🛑 SL: {round(sl,5)}\n"
                    f"🧠 AI: {ai_verdict}"
                )
                self.send(msg)
                self.positions[name] = signal_type 

            # --- ЛОГИКА СБРОСА ПОЗИЦИИ (ЧТОБЫ НЕ СПАМИЛ) ---
            elif self.positions[name] is not None:
                # Сбрасываем флаг ТОЛЬКО если дисбаланс исчез полностью
                # Раньше сбрасывали при ratio < 1.2, теперь даем запас (гистерезис)
                if self.positions[name] == "LONG" and ratio < 1.5:
                     self.positions[name] = None # Можно искать новый вход
                elif self.positions[name] == "SHORT" and ratio > 0.7:
                     self.positions[name] = None

    def analyze(self):
        self.check_market()
