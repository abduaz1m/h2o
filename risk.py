def risk_params(price, signal):
    if signal == "BUY":
        sl = price * 0.985
        tp = price * 1.03
    else:
        sl = price * 1.015
        tp = price * 0.97

    rr = abs(tp - price) / abs(price - sl)

    leverage = 5 if rr < 2 else 10
    return tp, sl, leverage
