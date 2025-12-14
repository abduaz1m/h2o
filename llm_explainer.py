import os
import requests

OPENAI_KEY = os.getenv("OPENAI_API_KEY")

def explain(signal):
    if not OPENAI_KEY:
        return "AI объяснение отключено (нет OPENAI_API_KEY)"

    prompt = f"""
Ты трейдер.
Объясни сигнал кратко:
{signal}
"""

    r = requests.post(
        "https://api.openai.com/v1/chat/completions",
        headers={
            "Authorization": f"Bearer {OPENAI_KEY}",
            "Content-Type": "application/json"
        },
        json={
            "model": "gpt-4o-mini",
            "messages": [{"role": "user", "content": prompt}],
            "max_tokens": 120
        },
        timeout=20
    )

    return r.json()["choices"][0]["message"]["content"]
