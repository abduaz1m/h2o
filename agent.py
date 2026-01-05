import os
import requests
import time
import pandas as pd
import pandas_ta as ta
import xml.etree.ElementTree as ET
from openai import OpenAI

# --- КОНФИГУРАЦИЯ ---
OKX_URL = "https://www.okx.com/api/v5/market/candles"
NEWS_RSS_URL = "https://cointelegraph.com/rss"

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
    "WIF":    {"id": "WIF-USDT-SWAP",    "lev": 3},
}

# 2. 🏦 СПИСОК СПОТА
SPOT_SYMBOLS = {
    "BTC": "BTC-USDT",
    "ETH": "ETH-USDT",
    "SOL": "SOL-USDT",
    "TON": "TON-USDT",
    "SUI": "SUI-USDT",
    "BNB": "BNB-USDT",
}

class TradingAgent:
    def __init__(self, bot_token, chat_id, openai_key):
        self.bot_token = bot_token
        self.chat_id = chat_id
        # Подключение к DeepSeek
        self.client = OpenAI(api_key=openai_key, base_url="https://api.deepseek.com")
        self.positions = {name: None for name in FUTURES_SYMBOLS}
        self.spot_positions = {name: None for name in SPOT_SYMBOLS}
        self.last_news = ""
        self.last_news_time = 0

    def send(self, text):
        try:
            requests.post(
                f"https://api.telegram.org/bot{self.bot_token}/sendMessage", 
                json={"chat_id": self.chat_id, "text": text, "parse_mode": "Markdown"}, 
                timeout=5
            )
        except Exception:
            pass

    # 📰 НОВЫЙ МЕТОД: ЧТЕНИЕ НОВОСТЕЙ
    def get_news(self):
        # Кэшируем новости на 10 минут, чтобы не спамить запросами
        if time.time() - self.last_news_time < 600 and self.last_news:
            return self.last_news
        
        try:
            print("📰 Fetching latest crypto news...")
            r = requests.get(NEWS_RSS_URL, timeout=5)
            root = ET.fromstring(r.content)
            headlines = []
            # Берем 3 последних заголовка
            for item in root.findall('.//item')[:3]:
                title = item.find('title').text
                headlines.append(f"- {title}")
            
            self.last_news = "\n".join(headlines)
            self.last_news_time = time.time()
            return self.last_news
        except Exception as e:
            print(f"⚠️ News Error: {e}")
            return "Market news unavailable."

    def get_candles(self, symbol, bar, limit=100):
        try:
            r = requests.get(OKX_URL, params={"instId": symbol, "bar": bar, "limit": limit}, timeout=10)
            data = r.json().get("data", [])
            if not data: return None
            df = pd.DataFrame(data, columns=["ts", "o", "h", "l", "c", "v", "volCcy", "volCcyQuote", "confirm"])
            df = df.iloc[::-1].reset_index(drop=True)
            df[["o", "h", "l", "c", "v"]] = df[["o", "h", "l", "c", "v"]].astype(float)
            return df
        except Exception:
            return None

    # 🔥 AI СТРАТЕГИЯ: TECH + FUNDAMENTAL
    def ask_ai(self, mode, symbol, price, rsi, adx, trend, direction, news_summary):
        strategy_name = "FUNDAMENTAL_HEDGE"
        
        print(f"🧠 Analyzing {symbol} ({direction}) with News Context...")

        json_template = '{"Risk": int, "Verdict": "BUY" or "SELL" or "WAIT", "Reason": "text"}'
        
        system_prompt = (
            f"Ты — элитный крипто-аналитик. Ты совмещаешь Технический анализ и Фундаментальные новости.\n"
            f"ЗАДАЧА: Подтвердить или Отклонить сделку ({direction}).\n\n"
            f"ВХОДНЫЕ ДАННЫЕ:\n"
            f"1. ТЕХНИКА: RSI={rsi}, ADX={adx}, Тренд={trend}.\n"
            f"2. НОВОСТИ (Последние заголовки):\n{news_summary}\n\n"
            f"ПРАВИЛА ПРИНЯТИЯ РЕШЕНИЙ:\n"
            f"1. ГЛАВНОЕ: Если новости КРАЙНЕ негативные (взлом, суд, запрет) -> ИГНОРИРУЙ любой сигнал BUY. Твой вердикт WAIT.\n"
            f"2. Если новости позитивные (партнерство, принятие ETF) -> BUY сигнал усиливается.\n"
            f"3. Если новостей нет или они нейтральные -> Работай чисто по технике (RSI, EMA).\n"
            f"4. Для SHORT: Плохие новости = Отличный сигнал.\n"
            f"ФОРМАТ ОТВЕТА (JSON): {json_template}"
        )

        user_prompt = (
            f"Asset: {symbol}\n"
            f"Price: {price}\n"
            f"Setup: {direction} Request\n"
        )

        for i in range(2):
            try:
                response = self.client.chat.completions.create(
                    model="deepseek-chat",
                    messages=[
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": user_prompt}
                    ],
                    max_tokens=250,
                    temperature=0.2
                )
                content = response.choices[0].message.content
                content = content.replace("```json", "").replace("```", "").strip()
                return content, strategy_name
            except Exception:
                time.sleep(1)
                continue
        
        return "Skip", strategy_name

    # --- ФЬЮЧЕРСЫ (15m, 30m, 1H) ---
    def check_futures(self):
        print("--- 🚀 Checking Futures (Smart + News) ---")
        
        # Получаем новости один раз для всего цикла проверки
        current_news = self.get_news()
        
        timeframes = ["15m", "30m", "1H"]
        
        for name, info in FUTURES_SYMBOLS.items():
            symbol = info["id"]
            lev = info["lev"]
            
            if self.positions[name] is not None:
                continue

            for tf in timeframes:
                time.sleep(0.15)
                df = self.get_candles(symbol, tf, limit=100)
                if df is None or len(df) < 60: continue

                df["ema_fast"] = ta.ema(df["c"], length=9)
                df["ema_trend"] = ta.ema(df["c"], length=50)
                df["rsi"] = ta.rsi(df["c"], length=14)
                df["atr"] = ta.atr(df["h"], df["l"], df["c"], length=14)
                try:
                    df["adx"] = ta.adx(df["h"], df["l"], df["c"], length=14)["ADX_14"]
                except: continue
                
                curr = df.iloc[-1]
                prev = df.iloc[-2]

                adx_val = curr["adx"]
                rsi_val = curr["rsi"]
                price = curr["c"]

                if pd.isna(curr["ema_trend"]) or pd.isna(rsi_val): continue

                signal_type = None
                
                # --- ЛОГИКА ВХОДА ---
                # 1. LONG: Пробой EMA 9 снизу вверх + Тренд EMA 50 UP
                if (price > curr["ema_trend"] and          
                    prev["c"] < prev["ema_fast"] and       
                    curr["c"] > curr["ema_fast"] and       
                    40 < rsi_val < 68 and                  
                    adx_val > 15):                         
                    signal_type = "LONG"

                # 2. SHORT: Пробой EMA 9 сверху вниз + Тренд EMA 50 DOWN
                elif (price < curr["ema_trend"] and        
                      prev["c"] > prev["ema_fast"] and     
                      curr["c"] < curr["ema_fast"] and     
                      32 < rsi_val < 60 and                
                      adx_val > 15):
                    signal_type = "SHORT"

                if signal_type:
                    # 🔥 ТЕПЕРЬ ПЕРЕДАЕМ НОВОСТИ В AI
                    ai_verdict, strategy_used = self.ask_ai(
                        "FUTURES", name, price, round(rsi_val,1), round(adx_val,1), 
                        f"{tf} Trend Breakout", signal_type, current_news
                    )
                    
                    if "WAIT" in str(ai_verdict).upper(): 
                        print(f"⛔ AI blocked {name} based on Analysis/News")
                        continue

                    atr_mult_sl = 1.5 
                    atr_mult_tp = 5.0 # Увеличенный тейк для профита
                    
                    if signal_type == "LONG":
                        tp = price + (curr["atr"] * atr_mult_tp)
                        sl = price - (curr["atr"] * atr_mult_sl)
                        emoji = "🟢"
                        title = "NEWS+TECH LONG"
                    else:
                        tp = price - (curr["atr"] * atr_mult_tp)
                        sl = price + (curr["atr"] * atr_mult_sl)
                        emoji = "🔴"
                        title = "NEWS+TECH SHORT"

                    msg = (
                        f"🗞️ **{title}** {emoji}\n"
                        f"#{name} — {tf}\n"
                        f"🧠 Strat: **{strategy_used}**\n"
                        f"⚙️ Lev: {lev}x\n"
                        f"📊 RSI: {round(rsi_val,1)}\n"
                        f"💰 Entry: {price}\n🎯 TP: {round(tp,4)}\n🛑 SL: {round(sl,4)}\n"
                        f"💬 AI Verdict: {ai_verdict}"
                    )
                    self.send(msg)
                    self.positions[name] = signal_type 
                    time.sleep(2)
                    break 

    # --- СПОТ (1D, 3D, 1W) ---
    def check_spot(self):
        print("--- 🏦 Checking Spot ---")
        current_news = self.get_news() # Новости для спота тоже важны
        timeframes = ["1D", "3D", "1W"]
        
        for name, symbol in SPOT_SYMBOLS.items():
            if self.spot_positions[name] == "BUY": continue

            for tf in timeframes:
                time.sleep(0.1)
                df = self.get_candles(symbol, tf, limit=300)
                if df is None or len(df) < 205: continue

                try:
                    rsi = ta.rsi(df["c"], length=14).iloc[-1]
                    ema200 = ta.ema(df["c"], length=200).iloc[-1]
                    price = df["c"].iloc[-1]
                    if pd.isna(ema200): continue
                except: continue

                is_dip = False
                setup = ""

                if price > ema200 and rsi < 40:
                    is_dip = True
                    setup = f"Trend Pullback ({tf})"
                elif rsi < 30:
                    is_dip = True
                    setup = f"Oversold Bounce ({tf})"

                if is_dip:
                    # Передаем новости и сюда
                    ai_verdict, strategy_used = self.ask_ai(
                        "SPOT", name, price, round(rsi,1), 0, setup, "LONG", current_news
                    )
                    
                    if "WAIT" in str(ai_verdict).upper(): continue

                    msg = (
                        f"💎 **SPOT INVEST**\n#{name} — {tf} 🔵\n"
                        f"📉 RSI: {round(rsi, 1)}\n"
                        f"🧠 Strat: {strategy_used}\n"
                        f"💰 Price: {price}\n"
                        f"💬 AI: {ai_verdict}"
                    )
                    self.send(msg)
                    self.spot_positions[name] = "BUY"
                    time.sleep(2)
                    break 
            
            if self.spot_positions[name] == "BUY":
                 pass 

    def analyze(self):
        self.check_futures()
        self.check_spot()
