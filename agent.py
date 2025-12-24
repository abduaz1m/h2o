import os
import ccxt
import time
import json
import pandas as pd
import pandas_ta as ta
from datetime import datetime
from openai import OpenAI

# --- 🔐 НАСТРОЙКИ БЕЗОПАСНОСТИ ---
API_KEY = os.environ.get("OKX_API_KEY", "")
API_SECRET = os.environ.get("OKX_API_SECRET", "") 
API_PASSWORD = os.environ.get("OKX_PASSWORD", "")
DEEPSEEK_API_KEY = os.environ.get("DEEPSEEK_API_KEY", "")
TELEGRAM_BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN", "")
TELEGRAM_CHAT_ID = os.environ.get("TELEGRAM_CHAT_ID", "")

# --- ⚙️ НАСТРОЙКИ ТОРГОВЛИ ---
SANDBOX_MODE = False

# Параметры риска
MAX_POSITIONS = 5
ORDER_AMOUNT_USD = 50
STOP_LOSS_PERCENT = 2.0
TAKE_PROFIT_PERCENT = 3.0
MAX_DAILY_LOSS_PERCENT = 5.0

# --- 🕒 КОНФИГУРАЦИЯ ТАЙМФРЕЙМОВ ---
TIMEFRAME_CONFIG = {
    "futures": {
        "trend": "1h",      # Основной тренд
        "signal": "30m",    # Сигнальный таймфрейм
        "entry": "15m",     # Таймфрейм для входа
    },
    "spot": {
        "trend": "4h",      # Долгосрочный тренд
        "signal": "1h",     # Сигнальный таймфрейм
    }
}

# Веса таймфреймов для принятия решений
TIMEFRAME_WEIGHTS = {
    "1h": 0.5,
    "30m": 0.3,
    "15m": 0.2
}

# --- 📊 ТОРГОВЫЕ ПАРЫ (без STRK) ---
FUTURES_SYMBOLS = {
    "BTC/USDT:USDT": {"lev": 5, "timeframes": ["1h", "30m", "15m"]},
    "ETH/USDT:USDT": {"lev": 5, "timeframes": ["1h", "30m", "15m"]},
    "SOL/USDT:USDT": {"lev": 5, "timeframes": ["1h", "30m", "15m"]},
    "TON/USDT:USDT": {"lev": 3, "timeframes": ["1h", "30m", "15m"]},
    "DOGE/USDT:USDT": {"lev": 3, "timeframes": ["1h", "30m", "15m"]},
    "PEPE/USDT:USDT": {"lev": 3, "timeframes": ["1h", "30m", "15m"]},
    "XRP/USDT:USDT": {"lev": 3, "timeframes": ["1h", "30m", "15m"]},
    "ADA/USDT:USDT": {"lev": 3, "timeframes": ["1h", "30m", "15m"]},
    "MATIC/USDT:USDT": {"lev": 3, "timeframes": ["1h", "30m", "15m"]},
    "LINK/USDT:USDT": {"lev": 3, "timeframes": ["1h", "30m", "15m"]},
    "AVAX/USDT:USDT": {"lev": 3, "timeframes": ["1h", "30m", "15m"]},
}

SPOT_SYMBOLS = {
    "BTC/USDT": {"timeframes": ["4h", "1h"]},
    "ETH/USDT": {"timeframes": ["4h", "1h"]},
    "SOL/USDT": {"timeframes": ["4h", "1h"]},
    "TON/USDT": {"timeframes": ["4h", "1h"]},
}

class TradingAgent:
    def __init__(self):
        """Инициализация торгового агента"""
        self.setup_logging()
        
        # Проверка настроек безопасности
        self.check_security()
        
        # Инициализация API
        self.init_exchange()
        self.init_ai()
        
        # Статистика и состояние
        self.positions = {}
        self.spot_signals = {}
        self.daily_pnl = 0
        self.start_time = datetime.now()
        self.api_request_count = 0
        self.last_request_time = time.time()
        
        print(f"✅ Торговый агент инициализирован: {datetime.now()}")
        print(f"📊 Режим: {'САНДБОКС' if SANDBOX_MODE else 'РЕАЛЬНЫЙ'}")
        print(f"💰 Размер позиции: ${ORDER_AMOUNT_USD}")
        print(f"🛡️ Стоп-лосс: {STOP_LOSS_PERCENT}%, Тейк-профит: {TAKE_PROFIT_PERCENT}%")
    
    def setup_logging(self):
        """Настройка системы логирования"""
        log_dir = "logs"
        if not os.path.exists(log_dir):
            os.makedirs(log_dir)
        
        self.log_file = f"{log_dir}/trading_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log"
    
    def check_security(self):
        """Проверка безопасности настроек"""
        if not all([API_KEY, API_SECRET, API_PASSWORD]):
            self.log("❌ ОШИБКА: Не заданы API ключи OKX")
            print("""
            ⚠️  ВНИМАНИЕ: Задайте переменные окружения:
            
            OKX_API_KEY=ваш_api_key_okx
            OKX_API_SECRET=ваш_api_secret_okx
            OKX_PASSWORD=ваш_api_password_okx
            
            Или создайте файл config.py с этими переменными.
            """)
            raise ValueError("Отсутствуют API ключи")
    
    def init_exchange(self):
        """Инициализация подключения к бирже"""
        try:
            self.exchange = ccxt.okx({
                'apiKey': API_KEY,
                'secret': API_SECRET,
                'password': API_PASSWORD,
                'enableRateLimit': True,
                'options': {'defaultType': 'swap'},
                'timeout': 30000,
                'rateLimit': 100,
            })
            
            if SANDBOX_MODE:
                self.exchange.set_sandbox_mode(True)
                print("🔧 Режим сандбокса активирован")
            
            # Проверка подключения
            self.exchange.fetch_time()
            print("✅ Подключение к OKX установлено")
            
            # Проверяем доступность символов
            self.check_symbol_availability()
            
        except Exception as e:
            self.log(f"❌ Ошибка подключения к OKX: {e}")
            raise
    
    def check_symbol_availability(self):
        """Проверка доступности символов на бирже"""
        try:
            markets = self.exchange.load_markets()
            available_futures = []
            
            for symbol in FUTURES_SYMBOLS.keys():
                if symbol in markets:
                    available_futures.append(symbol)
                else:
                    self.log(f"⚠️ Символ {symbol} недоступен на OKX", "WARNING")
            
            # Обновляем список доступных символов
            global FUTURES_SYMBOLS
            FUTURES_SYMBOLS = {k: v for k, v in FUTURES_SYMBOLS.items() if k in available_futures}
            
            print(f"✅ Доступно {len(FUTURES_SYMBOLS)} фьючерсных пар")
            
        except Exception as e:
            self.log(f"⚠️ Ошибка проверки символов: {e}", "WARNING")
    
    def init_ai(self):
        """Инициализация AI клиента"""
        if DEEPSEEK_API_KEY:
            try:
                self.ai_client = OpenAI(
                    api_key=DEEPSEEK_API_KEY,
                    base_url="https://api.deepseek.com"
                )
                print("✅ DeepSeek AI инициализирован")
            except Exception as e:
                self.log(f"⚠️ Не удалось инициализировать AI: {e}")
                self.ai_client = None
        else:
            self.ai_client = None
            print("⚠️ DeepSeek API ключ не задан, AI отключен")
    
    def log(self, message, level="INFO"):
        """Логирование сообщений"""
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        log_msg = f"[{timestamp}] [{level}] {message}"
        
        # Вывод в консоль
        print(log_msg)
        
        # Запись в файл
        try:
            with open(self.log_file, "a", encoding="utf-8") as f:
                f.write(log_msg + "\n")
        except:
            pass
    
    def safe_api_call(self, func, *args, **kwargs):
        """Безопасный вызов API с лимитами"""
        # Соблюдение rate limit
        elapsed = time.time() - self.last_request_time
        if elapsed < 0.1:
            time.sleep(0.1 - elapsed)
        
        self.api_request_count += 1
        self.last_request_time = time.time()
        
        try:
            return func(*args, **kwargs)
        except ccxt.RateLimitExceeded:
            self.log("⚠️ Превышен лимит запросов, пауза 5 секунд", "WARNING")
            time.sleep(5)
            return func(*args, **kwargs)
        except ccxt.RequestTimeout:
            self.log("⚠️ Таймаут запроса, повтор через 2 секунды", "WARNING")
            time.sleep(2)
            return func(*args, **kwargs)
        except Exception as e:
            self.log(f"❌ Ошибка API: {e}", "ERROR")
            return None
    
    def get_candles(self, symbol, timeframe='15m', limit=100):
        """Получение свечных данных с безопасной проверкой"""
        try:
            ohlcv = self.safe_api_call(
                self.exchange.fetch_ohlcv, symbol, timeframe, limit=limit
            )
            
            # Безопасная проверка данных
            if ohlcv is None:
                return None
            if not isinstance(ohlcv, list):
                return None
            if len(ohlcv) == 0:
                return None
                
            df = pd.DataFrame(ohlcv, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
            
            # Явная проверка DataFrame
            if df.empty:
                return None
            if len(df) < 10:
                return None
                
            df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
            return df
            
        except Exception as e:
            self.log(f"❌ Ошибка получения данных {symbol} {timeframe}: {e}", "ERROR")
            return None
    
    def get_multi_timeframe_data(self, symbol, timeframes):
        """Получение данных по нескольким таймфреймам"""
        data = {}
        for tf in timeframes:
            df = self.get_candles(symbol, tf)
            if df is not None and not df.empty and len(df) >= 20:
                # Добавляем базовые индикаторы
                df['ema9'] = ta.ema(df['close'], length=9)
                df['ema21'] = ta.ema(df['close'], length=21)
                df['rsi'] = ta.rsi(df['close'], length=14)
                
                # Безопасный расчет ADX
                try:
                    adx_result = ta.adx(df['high'], df['low'], df['close'])
                    if adx_result is not None and 'ADX_14' in adx_result:
                        df['adx'] = adx_result['ADX_14']
                    else:
                        df['adx'] = 25  # Значение по умолчанию
                except:
                    df['adx'] = 25
                
                data[tf] = df
            
            time.sleep(0.2)
        
        return data if data else None
    
    def analyze_trend_multi_tf(self, data):
        """Анализ тренда по нескольким таймфреймам"""
        if not data:
            return "neutral", 0
        
        scores = []
        
        for tf, df in data.items():
            if df is None or df.empty:
                continue
                
            curr = df.iloc[-1]
            weight = TIMEFRAME_WEIGHTS.get(tf, 0.2)
            
            tf_score = 0
            
            # 1. EMA направление
            if 'ema9' in df.columns and 'ema21' in df.columns:
                if curr['ema9'] > curr['ema21']:
                    tf_score += 0.4
                elif curr['ema9'] < curr['ema21']:
                    tf_score -= 0.4
            
            # 2. RSI момент
            if 'rsi' in df.columns:
                rsi = curr['rsi']
                if 50 < rsi < 70:
                    tf_score += 0.3
                elif 30 < rsi < 50:
                    tf_score -= 0.3
            
            # 3. ADX сила тренда
            if 'adx' in df.columns:
                adx = curr['adx']
                if adx > 25:
                    if tf_score > 0:
                        tf_score += 0.3
                    elif tf_score < 0:
                        tf_score -= 0.3
            
            scores.append(tf_score * weight)
        
        if not scores:
            return "neutral", 0
        
        total_score = sum(scores) / len(scores)
        
        # Интерпретация
        if total_score > 0.3:
            return "strong_bullish", total_score
        elif total_score > 0.1:
            return "bullish", total_score
        elif total_score < -0.3:
            return "strong_bearish", total_score
        elif total_score < -0.1:
            return "bearish", total_score
        else:
            return "neutral", total_score
    
    def ask_ai_analysis(self, symbol, trend_data, price, indicators):
        """Запрос анализа у AI"""
        if not self.ai_client:
            return {"verdict": "NO", "reason": "AI не инициализирован", "confidence": 0}
        
        prompt = f"""
        Анализ торговой ситуации:
        
        АКТИВ: {symbol}
        ЦЕНА: {price}
        
        ИНДИКАТОРЫ:
        RSI: {indicators.get('rsi', 'N/A')}
        ADX: {indicators.get('adx', 'N/A')}
        Тренд: {indicators.get('trend', 'N/A')}
        
        Верни JSON в формате:
        {{
            "verdict": "YES" или "NO",
            "confidence": число от 1 до 10,
            "reason": "краткое объяснение"
        }}
        """
        
        try:
            response = self.ai_client.chat.completions.create(
                model="deepseek-chat",
                messages=[{"role": "user", "content": prompt}],
                max_tokens=150,
                temperature=0.3
            )
            
            content = response.choices[0].message.content
            
            # Парсинг JSON
            try:
                import re
                json_match = re.search(r'\{.*\}', content, re.DOTALL)
                if json_match:
                    return json.loads(json_match.group())
            except:
                pass
            
            # Fallback
            if "YES" in content.upper():
                return {"verdict": "YES", "reason": "AI одобрил", "confidence": 7}
            else:
                return {"verdict": "NO", "reason": "AI отказал", "confidence": 3}
                
        except Exception as e:
            self.log(f"❌ Ошибка AI: {e}", "ERROR")
            return {"verdict": "NO", "reason": f"Ошибка AI: {e}", "confidence": 0}
    
    def calculate_position_size(self, symbol):
        """Расчет размера позиции"""
        try:
            ticker = self.safe_api_call(self.exchange.fetch_ticker, symbol)
            if not ticker:
                return 0
            
            price = ticker['last']
            amount = ORDER_AMOUNT_USD / price
            
            # Для фьючерсов учитываем плечо
            if ":USDT" in symbol:
                amount = amount * 0.2  # Консервативный подход
            
            return round(amount, 8)
            
        except Exception as e:
            self.log(f"❌ Ошибка расчета размера позиции: {e}", "ERROR")
            return 0
    
    def open_position(self, symbol, side, leverage=1):
        """Открытие позиции"""
        try:
            if symbol in self.positions:
                return False
            
            amount = self.calculate_position_size(symbol)
            if amount <= 0:
                return False
            
            # Установка плеча для фьючерсов
            if ":USDT" in symbol and leverage > 1:
                try:
                    self.safe_api_call(self.exchange.set_leverage, leverage, symbol)
                except:
                    pass
            
            # Открытие ордера
            order = self.safe_api_call(
                self.exchange.create_order,
                symbol,
                'market',
                side,
                amount
            )
            
            if order:
                self.positions[symbol] = {
                    'side': side,
                    'entry_price': order['price'],
                    'amount': amount,
                    'timestamp': datetime.now(),
                    'leverage': leverage
                }
                
                self.send_telegram(
                    f"🎯 **НОВАЯ ПОЗИЦИЯ**\n"
                    f"#{symbol.replace('/', '')}\n"
                    f"📈 Направление: {side.upper()}\n"
                    f"💰 Размер: ${ORDER_AMOUNT_USD}\n"
                    f"⚙️ Плечо: {leverage}x\n"
                    f"⏰ Время: {datetime.now().strftime('%H:%M:%S')}"
                )
                
                return True
            
        except Exception as e:
            self.log(f"❌ Ошибка открытия позиции {symbol}: {e}", "ERROR")
        
        return False
    
    def check_futures_signals(self):
        """Проверка сигналов для фьючерсов"""
        if len(self.positions) >= MAX_POSITIONS:
            return
        
        self.log("--- 🔍 СКАНИРОВАНИЕ ФЬЮЧЕРСОВ ---")
        
        for symbol, config in FUTURES_SYMBOLS.items():
            time.sleep(1)
            
            try:
                # Пропускаем, если уже есть позиция
                if symbol in self.positions:
                    continue
                
                # Получаем данные
                timeframes = config.get("timeframes", ["1h", "30m", "15m"])
                data = self.get_multi_timeframe_data(symbol, timeframes)
                
                if not data:
                    continue
                
                # Анализируем тренд
                trend, score = self.analyze_trend_multi_tf(data)
                
                # Получаем данные для входа (15m)
                tf_data = data.get("15m") or data.get(list(data.keys())[-1])
                if tf_data is None or tf_data.empty:
                    continue
                
                curr = tf_data.iloc[-1]
                price = curr['close']
                rsi = curr.get('rsi', 50)
                adx = curr.get('adx', 25)
                
                # Логика для LONG
                if trend in ["bullish", "strong_bullish"] and score > 0.2:
                    if 40 < rsi < 65 and adx > 20:
                        
                        # AI анализ
                        ai_result = self.ask_ai_analysis(
                            symbol, {}, price,
                            {"rsi": round(rsi, 1), "adx": round(adx, 1), "trend": trend}
                        )
                        
                        if ai_result.get("verdict") == "YES":
                            self.log(f"✅ LONG сигнал для {symbol}, уверенность AI: {ai_result.get('confidence')}/10")
                            self.open_position(symbol, "buy", config["lev"])
                
                # Логика для SHORT
                elif trend in ["bearish", "strong_bearish"] and score < -0.2:
                    if 35 < rsi < 60 and adx > 20:
                        
                        ai_result = self.ask_ai_analysis(
                            symbol, {}, price,
                            {"rsi": round(rsi, 1), "adx": round(adx, 1), "trend": trend}
                        )
                        
                        if ai_result.get("verdict") == "YES":
                            self.log(f"✅ SHORT сигнал для {symbol}, уверенность AI: {ai_result.get('confidence')}/10")
                            self.open_position(symbol, "sell", config["lev"])
                            
            except Exception as e:
                self.log(f"❌ Ошибка анализа {symbol}: {e}", "ERROR")
    
    def check_spot_signals(self):
        """Проверка сигналов для спота"""
        self.log("--- 🏦 СКАНИРОВАНИЕ СПОТА ---")
        
        for symbol, config in SPOT_SYMBOLS.items():
            time.sleep(1)
            
            try:
                # Получаем данные
                tf_data = self.get_candles(symbol, "4h", 50)
                if tf_data is None or tf_data.empty:
                    continue
                
                # Расчет RSI
                rsi_series = ta.rsi(tf_data['close'], length=14)
                if rsi_series is None or rsi_series.empty:
                    continue
                
                rsi = rsi_series.iloc[-1]
                price = tf_data['close'].iloc[-1]
                
                # BUY сигнал
                if rsi < 30 and symbol not in self.spot_signals:
                    self.spot_signals[symbol] = {
                        "type": "BUY",
                        "price": price,
                        "timestamp": datetime.now(),
                        "rsi": rsi
                    }
                    
                    self.send_telegram(
                        f"💎 **SPOT BUY SIGNAL**\n"
                        f"#{symbol.replace('/', '')}\n"
                        f"📉 RSI: {rsi:.1f} (перепроданность)\n"
                        f"💰 Цена: ${price:.2f}"
                    )
                
                # SELL сигнал
                elif rsi > 75 and symbol in self.spot_signals:
                    entry = self.spot_signals[symbol]
                    profit_pct = ((price - entry["price"]) / entry["price"]) * 100
                    
                    if profit_pct > 5:
                        self.send_telegram(
                            f"💰 **SPOT TAKE PROFIT**\n"
                            f"#{symbol.replace('/', '')}\n"
                            f"📈 RSI: {rsi:.1f} (перекупленность)\n"
                            f"💰 Цена: ${price:.2f}\n"
                            f"📊 Прибыль: {profit_pct:.1f}%"
                        )
                        del self.spot_signals[symbol]
                        
            except Exception as e:
                self.log(f"❌ Ошибка спот анализа {symbol}: {e}", "ERROR")
    
    def monitor_positions(self):
        """Мониторинг открытых позиций"""
        if not self.positions:
            return
        
        current_time = datetime.now()
        
        for symbol, pos in list(self.positions.items()):
            try:
                # Проверяем время удержания позиции
                hold_time = (current_time - pos['timestamp']).total_seconds()
                
                # Закрываем позицию через 30 минут
                if hold_time > 1800:  # 30 минут
                    self.close_position(symbol, "Таймаут 30 мин", 0)
                    continue
                
                # Получаем текущую цену
                ticker = self.safe_api_call(self.exchange.fetch_ticker, symbol)
                if not ticker:
                    continue
                
                current_price = ticker['last']
                entry_price = pos['entry_price']
                
                # Расчет PnL
                if pos['side'] == "buy":
                    pnl_pct = ((current_price - entry_price) / entry_price) * 100
                else:  # sell/short
                    pnl_pct = ((entry_price - current_price) / entry_price) * 100
                
                # Автоматический тейк-профит
                if pnl_pct >= TAKE_PROFIT_PERCENT:
                    self.close_position(symbol, f"Тейк-профит {pnl_pct:.1f}%", pnl_pct)
                # Автоматический стоп-лосс
                elif pnl_pct <= -STOP_LOSS_PERCENT:
                    self.close_position(symbol, f"Стоп-лосс {pnl_pct:.1f}%", pnl_pct)
                    
            except Exception as e:
                self.log(f"❌ Ошибка мониторинга {symbol}: {e}", "ERROR")
    
    def close_position(self, symbol, reason, pnl_pct):
        """Закрытие позиции"""
        try:
            pos = self.positions.get(symbol)
            if not pos:
                return
            
            # Определяем сторону для закрытия
            close_side = "sell" if pos['side'] == "buy" else "buy"
            
            # Закрываем позицию
            order = self.safe_api_call(
                self.exchange.create_order,
                symbol,
                'market',
                close_side,
                pos['amount']
            )
            
            if order:
                # Обновляем PnL
                self.daily_pnl += pnl_pct
                
                # Уведомление
                emoji = "✅" if pnl_pct > 0 else "❌"
                self.send_telegram(
                    f"{emoji} **ПОЗИЦИЯ ЗАКРЫТА**\n"
                    f"#{symbol.replace('/', '')}\n"
                    f"📊 Причина: {reason}\n"
                    f"💰 PnL: {pnl_pct:.2f}%\n"
                    f"📈 Дневной PnL: {self.daily_pnl:.2f}%"
                )
                
                # Удаляем позицию
                del self.positions[symbol]
                self.log(f"📤 Закрыта позиция {symbol}: {reason}, PnL: {pnl_pct:.2f}%")
                
        except Exception as e:
            self.log(f"❌ Ошибка закрытия позиции {symbol}: {e}", "ERROR")
    
    def send_telegram(self, message):
        """Отправка сообщения в Telegram"""
        if not TELEGRAM_BOT_TOKEN or not TELEGRAM_CHAT_ID:
            return
        
        try:
            import requests
            url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
            payload = {
                "chat_id": TELEGRAM_CHAT_ID,
                "text": message,
                "parse_mode": "Markdown"
            }
            
            requests.post(url, json=payload, timeout=10)
                
        except Exception as e:
            self.log(f"⚠️ Не удалось отправить в Telegram: {e}", "WARNING")
    
    def run_cycle(self):
        """Запуск одного цикла анализа"""
        try:
            # Мониторинг текущих позиций
            self.monitor_positions()
            
            # Проверка новых сигналов
            self.check_futures_signals()
            self.check_spot_signals()
            
            # Отчет о состоянии
            self.print_status()
            
        except Exception as e:
            self.log(f"❌ Критическая ошибка в цикле: {e}", "ERROR")
        
        # Время до следующего цикла
        return 60
    
    def print_status(self):
        """Вывод статуса системы"""
        status = f"""
{'='*50}
📊 СТАТУС ТОРГОВОГО АГЕНТА
{'='*50}
⏰ Время: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
⏳ Работает: {str(datetime.now() - self.start_time).split('.')[0]}
💰 Открыто позиций: {len(self.positions)}/{MAX_POSITIONS}
📈 Дневной PnL: {self.daily_pnl:.2f}%
📡 Запросов API: {self.api_request_count}
{'='*50}
"""
        print(status)
    
    def run(self):
        """Главный цикл работы бота"""
        self.log("🚀 ЗАПУСК ТОРГОВОГО АГЕНТА")
        self.send_telegram("🤖 *Торговый агент запущен*")
        
        try:
            while True:
                sleep_time = self.run_cycle()
                time.sleep(sleep_time)
                
        except KeyboardInterrupt:
            self.log("🛑 Остановка по команде пользователя")
            self.send_telegram("🛑 *Торговый агент остановлен*")
            
        except Exception as e:
            self.log(f"💥 Критическая ошибка: {e}", "CRITICAL")
            self.send_telegram(f"💥 *Критическая ошибка:* {str(e)[:100]}")

# --- 🚀 ЗАПУСК ПРОГРАММЫ ---
if __name__ == "__main__":
    # Проверка обязательных переменных
    required_vars = ["OKX_API_KEY", "OKX_API_SECRET", "OKX_PASSWORD"]
    missing_vars = [var for var in required_vars if not os.getenv(var)]
    
    if missing_vars:
        print(f"❌ Отсутствуют переменные окружения: {', '.join(missing_vars)}")
        exit(1)
    
    # Создание и запуск агента
    try:
        agent = TradingAgent()
        agent.run()
    except Exception as e:
        print(f"❌ Не удалось запустить агента: {e}")
