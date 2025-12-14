import os
import time
import requests
import statistics
from datetime import datetime

# ================== CONFIG ==================
BOT_TOKEN = os.getenv("BOT_TOKEN")
CHAT_ID = os.getenv("CHAT_ID")

SYMBOL_ID = "ethereum"      # CoinGecko ID
INTERVAL_SEC = 600          # 10 минут
COINGECKO_URL = "https://api.coingecko.com/api/v3"

if not BOT_TOKEN or not CHAT_ID:
    raise RuntimeError("❌ BOT_TOKEN или CHAT_ID не заданы")

print("🔥 ETH BOT STARTED (FINAL VERSION)")
print(f"🔹 SYMBOL: {SYMBOL_ID}")
print(f"🔹 INTERVAL: {INTERVAL_SEC} sec")

# ================== TELEGRAM ==================
def send_telegram(text: str):
    try:
        url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
        payload = {
            "chat_id": CHAT_ID,
            "text": text,
            "parse_mode": "HTML"
        }
        requests.post(url, data=payload, timeout=10)
    except Exception as e:
        print("❌ Telegram error:", e)

# ================== DATA ==================
def get_prices():
    """
    Берём минутные цены за 1 день (1440 точек)
    """
    url = f"{COINGECKO_URL}/coins/{SYMBOL_ID}/market_chart"
    params = {
        "vs_currency": "usd",
        "days": 1,
        "interval": "minutely"
    }
    r = requests.get(url, params=params, timeout=15)
    r.raise_for_status()
    prices = [p[1] for p in r.json()["prices"]]
    return prices

# ================== INDICATORS ==================
def ema(values, period):
    k = 2 / (period + 1)
    ema_val = values[0]
    for v in values[1:]:
        ema_val = v * k + ema_val * (1 - k)
    return ema_val

def rsi(values, period=14):
    gains, losses = [], []
    for i in range(1, period + 1):
        delta = values[-i] - values[-i - 1]
        if delta >= 0:
            gains.append(delta)
        else:
            losses.append(abs(delta))

    avg_gain = sum(gains) / period if gains else 0.0001
    avg_loss = sum(losses) / period if losses else 0.0001
    rs = avg_gain / avg_loss
    return 100 - (100 / (1 + rs))

# ================== STRATEGY ==================
def analyze():
    prices = get_prices()
    price = prices[-1]

    ema_fast = ema(prices[-50:], 50)
    ema_slow = ema(prices[-200:], 200)
    rsi_val = rsi(prices)

    signal = None
    reason = ""

    if ema_fast > ema_slow and rsi_val < 70:
        signal = "🟢 BUY"
        reason = "EMA50 > EMA200 и RSI < 70"
    elif ema_fast < ema_slow and rsi_val > 30:
        signal = "🔴 SELL"
        reason = "EMA50 < EMA200 и RSI > 30"

    if not signal:
        return None

    # TP / SL
    if signal == "🟢 BUY":
        tp = price * 1.03
        sl = price * 0.98
    else:
        tp = price * 0.97
        sl = price * 1.02

    explanation = (
        "AI-анализ:\n"
        f"• Тренд: {'восходящий' if ema_fast > ema_slow else 'нисходящий'}\n"
        f"• RSI: {rsi_val:.1f}\n"
        f"• Импульс подтверждён EMA"
    )

    msg = (
        f"🤖 <b>ETH SIGNAL (CoinGecko)</b>\n\n"
        f"💰 Цена: ${price:,.2f}\n"
        f"📊 RSI: {rsi_val:.1f}\n\n"
        f"{signal}\n"
        f"🎯 TP: ${tp:,.2f}\n"
        f"🛑 SL: ${sl:,.2f}\n\n"
        f"🧠 {reason}\n\n"
        f"{explanation}\n\n"
        f"⏰ {datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')} UTC"
    )

    return msg

# ================== LOOP ==================
send_telegram("🚀 ETH Bot запущен и работает в фоне")

while True:
    try:
        print("⏳ Анализ ETH...")
        result = analyze()
        if result:
            send_telegram(result)
            print("✅ Сигнал отправлен")
        else:
            print("⚪ Нет сигнала")

    except Exception as e:
        print("❌ Ошибка анализа:", e)

    time.sleep(INTERVAL_SEC)
