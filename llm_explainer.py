def explain_signal(signal):
    if signal["action"] == "BUY":
        return (
            "RSI показывает перепроданность, "
            "а быстрая EMA выше медленной — "
            "вероятен импульс вверх."
        )
    elif signal["action"] == "SELL":
        return (
            "RSI в зоне перекупленности, "
            "EMA указывает на ослабление тренда."
        )
    return "Рынок без чёткого направления."
