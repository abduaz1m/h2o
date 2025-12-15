import os
import requests

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

def explain_signal(signal_text: str) -> str:
    if not OPENAI_API_KEY:
        return "LLM отключён (нет OPENAI_API_KEY)"

    try:
        r = requests.post(
            "https://api.openai.com/v1/chat/completions",
            headers={
                "Authorization": f"Bearer {OPENAI_API_KEY}",
                "Content-Type": "application/json"
            },
            json={
                "model": "gpt-4o-mini",
                "messages": [
                    {
                        "role": "system",
                        "content": "Ты профессиональный трейдер фьючерсов. Коротко объясняй торговые сигналы."
                    },
                    {
                        "role": "user",
                        "content": signal_text
                    }
                ],
                "temperature": 0.4
            },
            timeout=20
        )
        return r.json()["choices"][0]["message"]["content"]
    except Exception:
        return "LLM временно недоступен"
