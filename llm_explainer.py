import openai
import os

openai.api_key = os.getenv("OPENAI_API_KEY")

def explain_signal(signal):
    prompt = f"""
Ты профессиональный крипто-трейдер.
Объясни торговый сигнал простыми словами.

Сигнал:
Монета: ETH
Тип: {signal['side']}
Цена входа: {signal['entry']}
TP: {signal['tp']}
SL: {signal['sl']}
RSI: {signal['rsi']}
EMA тренд: {signal['trend']}
Плечо: {signal['leverage']}x
"""

    try:
        resp = openai.ChatCompletion.create(
            model="gpt-4o-mini",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.4
        )
        return resp.choices[0].message.content.strip()
    except Exception as e:
        return f"LLM недоступен: {e}"
