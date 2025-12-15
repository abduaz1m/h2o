import requests
import math

def get_okx_candles():
    url = "https://www.okx.com/api/v5/market/candles"
    params = {
        "instId": "ETH-USDT-SWAP",
        "bar": "15m",
        "limit": 100
    }
    r = requests.get(url, params=params, timeout=10).json()
    return [float(c[4]) for c in r["data"]]  # close prices


def rsi(prices, period=14):
    gains, losses = [], []
    for i in range(1, period + 1):
        diff = prices[i] - prices[i - 1]
        if diff >= 0:
            gains.append(diff)
        else:
            losses.append(abs(diff))
    avg_gain = sum(gains) / period
    avg_loss = sum(losses) / period if losses else 0.0001
    rs = avg_gain / avg_loss
    return 100 - (100 / (1 + rs))


def ema(prices, period):
    k = 2 / (period + 1)
    ema_val = prices[0]
    for p in prices[1:]:
        ema_val = p * k + ema_val * (1 - k)
    return ema_val


def generate_signal():
    prices = get_okx_candles()
    price = prices[-1]

    rsi_val = rsi(prices)
    ema_fast = ema(prices[-20:], 20)
    ema_slow = ema(prices[-50:], 50)

    if rsi_val < 30 and ema_fast > ema_slow:
        side = "BUY"
    elif rsi_val > 70 and ema_fast < ema_slow:
        side = "SELL"
    else:
        return None

    # динамическое плечо
    volatility = abs(prices[-1] - prices[-15]) / price
    leverage = max(3, min(15, int(1 / volatility)))

    tp = price * (1.01 if side == "BUY" else 0.99)
    sl = price * (0.995 if side == "BUY" else 1.005)

    return {
        "side": side,
        "price": price,
        "rsi": round(rsi_val, 2),
        "ema_fast": round(ema_fast, 2),
        "ema_slow": round(ema_slow, 2),
        "leverage": leverage,
        "tp": round(tp, 2),
        "sl": round(sl, 2)
    }
