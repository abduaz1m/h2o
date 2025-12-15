import requests
import time
from datetime import datetime

OKX_URL = "https://www.okx.com/api/v5/market/candles"

SYMBOLS = {
    "ETH": "ETH-USDT-SWAP",
    "ARB": "ARB-USDT-SWAP",
    "OP": "OP-USDT-SWAP",
    "LDO": "LDO-USDT-SWAP",
    "UNI": "UNI-USDT-SWAP",
}

INTERVAL = "15m"
LEVERAGE = 10


class TradingAgent:
    def __init__(self, bot_token, chat_id):
        self.bot_token = bot_token
        self.chat_id = chat_id

    # -------------------------
    def send(self, text):
        url = f"https://api.telegram.org/bot{self.bot_token}/sendMessage"
        requests.post(url, json={"chat_id": self.chat_id, "text": text})

    # -------------------------
    def get_candles(self, symbol):
        r = requests.get(
            OKX_URL,
            params={
                "instId": symbol,
                "bar": INTERVAL,
                "limit": 100
            },
            timeout=10
        )
        r.raise_for_status()
        data = r.json()["data"]
        closes = [float(c[4]) for c in data]
        return closes[::-1]

    # -------------------------
    def ema(self, prices, period):
        k = 2 / (period + 1)
        ema = prices[0]
        for p in prices[1:]:
            ema = p * k + ema * (1 - k)
        return ema

    def rsi(self, prices, period=14):
        gains, losses = 0, 0
        for i in range(1, period + 1):
            diff = prices[-i] - prices[-i - 1]
            if diff > 0:
                gains += diff
            else:
                losses -= diff
        if losses == 0:
            return 100
        rs = gains / losses
        return 100 - (100 / (1 + rs))

    # -------------------------
    def analyze(self):
        for name, symbol in SYMBOLS.items():
            try:
                prices = self.get_candles(symbol)
                ema_fast = self.ema(prices[-50:], 21)
                ema_slow = self.ema(prices[-50:], 50)
                rsi = self.rsi(prices)

                price = prices[-1]

                if ema_fast > ema_slow and rsi < 70:
                    side = "BUY"
                    tp = round(price * 1.03, 4)
                    sl = round(price * 0.97, 4)
                elif ema_fast < ema_slow and rsi > 30:
                    side = "SELL"
                    tp = round(price * 0.97, 4)
                    sl = round(price * 1.03, 4)
                else:
                    continue  # ❗ HOLD игнорируем

                self.send(
                    f"🚀 {name} OKX SIGNAL\n"
                    f"⏱ TF: 15m | ⚙️ {LEVERAGE}x\n"
                    f"📈 {side}\n"
                    f"💰 Entry: {price}\n"
                    f"🎯 TP: {tp}\n"
                    f"🛑 SL: {sl}\n"
                    f"📊 RSI: {round(rsi,1)}\n"
                    f"🕒 {datetime.utcnow()}"
                )

                time.sleep(2)

            except Exception as e:
                self.send(f"⚠️ {name} ERROR: {e}")
                time.sleep(2)
