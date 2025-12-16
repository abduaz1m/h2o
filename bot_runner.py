import os
import time
from datetime import datetime, timedelta
from agent import TradingAgent

# Загрузка переменных (лучше использовать python-dotenv)
BOT_TOKEN = os.getenv("BOT_TOKEN")
CHAT_ID = os.getenv("CHAT_ID")

agent = TradingAgent(BOT_TOKEN, CHAT_ID)

agent.send("🤖 AI Trader V2 Started\nWaiting for candle close...")

while True:
    # Запускаем анализ
    agent.analyze()

    # СИНХРОНИЗАЦИЯ С ТАЙМФРЕЙМОМ
    # Вычисляем сколько секунд осталось до следующих :00, :15, :30, :45 минут
    now = datetime.now()
    next_run = now + timedelta(minutes=15)
    # Округляем до ближайших 15 минут
    next_run = next_run.replace(second=0, microsecond=0, minute=(now.minute // 15 + 1) * 15 % 60)
    if next_run.minute == 0 and now.minute >= 45: 
        next_run += timedelta(hours=1) # Коррекция перехода часа

    sleep_seconds = (next_run - now).total_seconds() + 5 # +5 сек задержки, чтобы свеча точно закрылась на бирже
    
    print(f"Sleeping for {int(sleep_seconds)}s until {next_run.strftime('%H:%M:%S')}")
    time.sleep(sleep_seconds)
