import requests
import os

OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")

def explain_signal(data: dict) -> str:
    prompt = f"""
Ты крипто-трейдер.
Объясни сигнал кратко и понятно.

Данные:
Цена: {data['price']}
RSI: {data['rsi']}
EMA20: {data['ema20']}
EMA50: {data['ema50']}
Сигнал: {data['signal']}

Ответь на русском, 2–4 предложения.
"""

    response = requests.post(
        "https://openrouter.ai/api/v1/chat/completions",
        headers={
            "Authorization": f"Bearer {OPENROUTER_API_KEY}",
            "Content-Type": "application/json"
        },
        json={
            "model": "openai/gpt-4o-mini",
            "messages": [{"role": "user", "content": prompt}],
            "temperature": 0.4
        },
        timeout=15
    )

    return response.json()["choices"][0]["message"]["content"]
