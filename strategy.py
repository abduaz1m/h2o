import math

def ema(values, period):
    k = 2 / (period + 1)
    ema_val = sum(values[:period]) / period
    for v in values[period:]:
        ema_val = v * k + ema_val * (1 - k)
    return ema_val

def rsi(values, period=14):
    gains, losses = [], []
    for i in range(1, period + 1):
        diff = values[i] - values[i - 1]
        gains.append(max(diff, 0))
        losses.append(abs(min(diff, 0)))
    rs = (sum(gains) / period) / (sum(losses) / period + 1e-9)
    return 100 - (100 / (1 + rs))

def signal(prices):
    r = rsi(prices)
    e_fast = ema(prices, 20)
    e_slow = ema(prices, 50)

    if r < 30 and e_fast > e_slow:
        return "BUY"
    if r > 70 and e_fast < e_slow:
        return "SELL"
    return None
