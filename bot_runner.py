import os
import time
import threading
import traceback

from crypto_trading_agent import CryptoTradingAgent

# =========================
# ENV
# =========================
BOT_TOKEN = os.getenv("BOT_TOKEN")
CHAT_ID = os.getenv("CHAT_ID")

if not BOT_TOKEN or not CHAT_ID:
    raise RuntimeError("❌ BOT_TOKEN или CHAT_ID не заданы в Render ENV")

# =========================
# НАСТРОЙКИ
# =========================
SYMBOL = "ethereum"      # ❗️ТОЛЬКО ETH
INTERVAL_SEC = 10 * 60   # 10 минут

print("🔥 ETH BOT STARTED (FINAL VERSION)")
print(f"📌 SYMBOL: {SYMBOL}")
print(f"⏱ INTERVAL: {INTERVAL_SEC} sec")

# =========================
# INIT AGENT
# =========================
agent = CryptoTradingAgent(
    telegram_bot_token=BOT_TOKEN,
    telegram_chat_id=CHAT_ID
)

# =========================
# ОСНОВНОЙ ЦИКЛ
# =========================
def run_loop():
    while True:
        try:
            print("🚀 Запуск анализа ETH...")
            agent.run()   # ⬅️ внутри уже RSI / EMA / TP / SL / BUY|SELL
            print("✅ Анализ завершён")

        except Exception as e:
            print("❌ Ошибка в анализе:")
            traceback.print_exc()

            # Чтобы бот НЕ ПАДАЛ
            try:
                agent.send_message(
                    "⚠️ Ошибка анализа ETH\n"
                    "Бот продолжит работу автоматически."
                )
            except:
                pass

        # 🔒 защита от 429 / перегрузки API
        time.sleep(INTERVAL_SEC)


# =========================
# START (Background Worker)
# =========================
if __name__ == "__main__":
    run_loop()
