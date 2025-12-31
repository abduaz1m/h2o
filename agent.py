import os
import requests
import time
import pandas as pd
import pandas_ta as ta
from openai import OpenAI

# --- CONFIGURATION ---
OKX_URL = "https://www.okx.com/api/v5/market/candles"

# 1. 🚜 FUTURES LIST
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

# 2. 🏦 SPOT LIST
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
        self.client = OpenAI(api_key=openai_key, base_url="https://api.deepseek.com")
        self.positions = {name: None for name in FUTURES_SYMBOLS}
        self.spot_positions = {name: None for name in SPOT_SYMBOLS}

    def send(self, text):
        try:
            requests.post(
                f"https://api.telegram.org/bot{self.bot_token}/sendMessage", 
                json={"chat_id": self.chat_id, "text": text, "parse_mode": "Markdown"}, 
                timeout=5
            )
        except Exception:
            pass

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

    # 🔥 AI BRAIN: PULLBACK STRATEGY
    def ask_ai(self, mode, symbol, price, rsi, adx, trend, direction):
        strategy_name = "SMART_PULLBACK_V3"
        print(f"🧠 AI Analyzing {symbol} ({direction})...")

        json_template = '{"Risk": int, "Verdict": "BUY" or "SELL" or "WAIT", "Reason": "text"}'
        
        if direction == "LONG":
            # We want to buy when everyone is scared (RSI low) but Trend is UP
            context = "We are buying the DIP in an Uptrend. Do not fear red candles."
        else: 
            # We want to short when price spikes up in a Downtrend
            context = "We are shorting the RALLY in a Downtrend. Sell the pump."

        system_prompt = (
            f"You are a Sniper Trader. Strategy: PULLBACK TRADING.\n"
            f"CONTEXT: {context}\n"
            f"RULES:\n"
            f"1. IGNORE FOMO. We enter ONLY on corrections.\n"
            f"2. Risk is HIGH if ADX < 20 (No trend).\n"
            f"3. Confirm if the 'dip' is stabilizing.\n"
            f"OUTPUT FORMAT (JSON): {json_template}"
        )

        user_prompt = (
            f"Asset: {symbol}\n"
            f"Price: {price}\n"
            f"RSI (14): {rsi} (Should be favorable for pullback)\n"
            f"ADX: {adx}\n"
            f"Trend: {trend}\n"
            f"Setup: {direction} Entry\n"
        )

        for i in range(2):
            try:
                response = self.client.chat.completions.create(
                    model="deepseek-chat",
                    messages=[
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": user_prompt}
                    ],
                    max_tokens=200,
                    temperature=0.2
                )
                content = response.choices[0].message.content
                content = content.replace("```json", "").replace("```", "").strip()
                return content, strategy_name
            except Exception:
                time.sleep(1)
                continue
        
        return "Skip", strategy_name

    # --- FUTURES (15m, 30m, 1H) ---
    def check_futures(self):
        print("--- 🚀 Checking Futures (Pullback Logic) ---")
        timeframes = ["15m", "30m", "1H"]
        
        for name, info in FUTURES_SYMBOLS.items():
            symbol = info["id"]
            lev = info["lev"]
            
            if self.positions[name] is not None:
                continue

            for tf in timeframes:
                time.sleep(0.15)
                # Need enough data for EMA 50
                df = self.get_candles(symbol, tf, limit=100)
                if df is None or len(df) < 55: continue

                # INDICATORS
                df["ema_50"] = ta.ema(df["c"], length=50) # Main Trend
                df["rsi"] = ta.rsi(df["c"], length=14)
                df["atr"] = ta.atr(df["h"], df["l"], df["c"], length=14)
                try:
                    df["adx"] = ta.adx(df["h"], df["l"], df["c"], length=14)["ADX_14"]
                except: continue
                
                curr = df.iloc[-2] # Closed candle
                adx_val = curr["adx"]
                rsi_val = curr["rsi"]
                price = curr["c"]
                ema_50 = curr["ema_50"]

                if pd.isna(ema_50) or pd.isna(rsi_val): continue

                signal_type = None
                
                # --- NEW LOGIC: PULLBACKS ---
                
                # 1. LONG SETUP (Trend UP + Price Cheap)
                # Trend: Price > EMA 50
                # Trigger: RSI < 45 (We buy the dip!) 
                if (price > ema_50 and 
                    rsi_val < 45 and 
                    adx_val > 20):
                    signal_type = "LONG"

                # 2. SHORT SETUP (Trend DOWN + Price Expensive)
                # Trend: Price < EMA 50
                # Trigger: RSI > 55 (We sell the bounce!)
                elif (price < ema_50 and 
                      rsi_val > 55 and 
                      adx_val > 20):
                    signal_type = "SHORT"

                if signal_type:
                    ai_verdict, strategy_used = self.ask_ai("FUTURES", name, price, round(rsi_val,1), round(adx_val,1), f"{tf} Trend", signal_type)
                    
                    if "WAIT" in str(ai_verdict).upper(): continue

                    # Tighter Stops for Pullback
                    atr_mult_sl = 1.5
                    atr_mult_tp = 3.0
                    
                    if signal_type == "LONG":
                        tp = price + (curr["atr"] * atr_mult_tp)
                        sl = price - (curr["atr"] * atr_mult_sl)
                        emoji = "🟢"
                        title = "BUY THE DIP"
                    else:
                        tp = price - (curr["atr"] * atr_mult_tp)
                        sl = price + (curr["atr"] * atr_mult_sl)
                        emoji = "🔴"
                        title = "SELL THE PUMP"

                    msg = (
                        f"🚀 **{title}** {emoji}\n"
                        f"#{name} — {tf}\n"
                        f"🧠 Strat: **{strategy_used}**\n"
                        f"⚙️ Lev: {lev}x\n"
                        f"📉 RSI: {round(rsi_val,1)} (Pullback)\n"
                        f"💰 Entry: {price}\n🎯 TP: {round(tp,4)}\n🛑 SL: {round(sl,4)}\n"
                        f"💬 AI: {ai_verdict}"
                    )
                    self.send(msg)
                    self.positions[name] = signal_type 
                    time.sleep(2)
                    break 

    # --- SPOT (1D, 4H) ---
    def check_spot(self):
        print("--- 🏦 Checking Spot ---")
        timeframes = ["4H", "1D"]
        
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
                    setup = f"Oversold ({tf})"

                if is_dip:
                    ai_verdict, strategy_used = self.ask_ai("SPOT", name, price, round(rsi,1), 0, setup, "LONG")
                    
                    msg = (
                        f"💎 **SPOT ENTRY**\n#{name} — {tf} 🔵\n"
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
