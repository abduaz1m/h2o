import openai
import os

openai.api_key = os.getenv("OPENAI_API_KEY")

def explain(symbol, signal, rsi, leverage):
    prompt = f"""
You are a crypto futures trader.
Symbol: {symbol}
Signal: {signal}
RSI: {rsi}
Leverage: {leverage}x

Explain shortly why this trade makes sense.
"""

    r = openai.ChatCompletion.create(
        model="gpt-4o-mini",
        messages=[{"role": "user", "content": prompt}],
        max_tokens=80
    )
    return r.choices[0].message.content.strip()
