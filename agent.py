import os
import ccxt
import time
import json
import pandas as pd
import pandas_ta as ta
from datetime import datetime
from dotenv import load_dotenv
from openai import OpenAI

# --- 🔐 ЗАГРУЗКА БЕЗОПАСНЫХ НАСТРОЕК ---
load_dotenv()

API_KEY = os.getenv("OKX_API_KEY", "")
API_SECRET = os.getenv("OKX_API_SECRET", "")
API_PASSWORD = os.getenv("OKX_PASSWORD", "")
DEEPSEEK_API_KEY = os.getenv("DEEPSEEK_API_KEY", "")
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID", "")

# --- ⚙️ НАСТРОЙКИ ТОРГОВЛИ ---
SANDBOX_MODE = True  # True = тестовый режим, False = реальные деньги

# Параметры риска
MAX_POSITIONS = 10
ORDER_AMOUNT_USD = 100  # Размер позиции в USD
STOP_LOSS_PERCENT = 2.0  # Стоп-лосс 2%
TAKE_PROFIT_PERCENT = 5.0  # Тейк-профит 5%
MAX_DAILY_LOSS_PERCENT = 5.0  # Максимальная дневная просадка

# --- 🕒 КОНФИГУРАЦИЯ ТАЙМФРЕЙМОВ ---
TIMEFRAME_CONFIG = {
    "futures": {
        "trend": "4h",      # Основной тренд
        "signal": "1h",     # Сигнальный таймфрейм
        "entry": "15m",     # Таймфрейм для входа
        "exit": "5m"        # Таймфрейм для выхода (опционально)
    },
    "spot": {
        "trend": "1d",      # Долгосрочный тренд
        "signal": "4h",     # Сигнальный таймфрейм
        "entry": "1h",      # Таймфрейм для входа
        "exit": "30m"       # Таймфрейм для выхода
    }
}

# Веса таймфреймов для принятия решений (сумма = 1.0)
TIMEFRAME_WEIGHTS = {
    "4h": 0.4,
    "1h": 0.3,
    "15m": 0.2,
    "5m": 0.1
}

# --- 📊 ТОРГОВЫЕ ПАРЫ ---
FUTURES_SYMBOLS = {
    "BTC/USDT:USDT": {"lev": 10, "timeframes": ["4h", "1h", "15m"]},
    "ETH/USDT:USDT": {"lev": 10, "timeframes": ["4h", "1h", "15m"]},
    "SOL/USDT:USDT": {"lev": 10, "timeframes": ["4h", "1h", "15m"]},
    "TON/USDT:USDT": {"lev": 5, "timeframes": ["4h", "1h", "30m"]},
    "DOGE/USDT:USDT": {"lev": 5, "timeframes": ["4h", "1h", "30m"]},
    "PEPE/USDT:USDT": {"lev": 3, "timeframes": ["1h", "30m", "15m"]},
    "STRK/USDT:USDT": {"lev": 3, "timeframes": ["1h", "30m", "15m"]},
    "WIF/USDT:USDT": {"lev": 3, "timeframes": ["1h", "30m", "15m"]},
}

SPOT_SYMBOLS = {
    "BTC/USDT": {"timeframes": ["1d", "4h", "1h"]},
    "ETH/USDT": {"timeframes": ["1d", "4h", "1h"]},
    "SOL/USDT": {"timeframes": ["1d", "4h", "1h"]},
    "TON/USDT": {"timeframes": ["1d", "4h", "2h"]},
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
            self.log("❌ ОШИБКА: Не заданы API ключи OKX в переменных окружения")
            print("""
            ⚠️  ВНИМАНИЕ: Создайте файл .env в той же папке с содержимым:
            
            OKX_API_KEY=ваш_ключ
            OKX_API_SECRET=ваш_секрет
            OKX_PASSWORD=ваш_пароль
            DEEPSEEK_API_KEY=ваш_ключ_deepseek
            TELEGRAM_BOT_TOKEN=токен_бота
            TELEGRAM_CHAT_ID=ид_чата
            
            Или задайте переменные окружения в системе.
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
            
        except Exception as e:
            self.log(f"❌ Ошибка подключения к OKX: {e}")
            raise
    
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
        if elapsed < 0.1:  # Не более 10 запросов в секунду
            time.sleep(0.1 - elapsed)
        
        self.api_request_count += 1
        self.last_request_time = time.time()
        
        try:
            return func(*args, **kwargs)
        except ccxt.RateLimitExceeded as e:
            self.log(f"⚠️ Превышен лимит запросов, пауза 5 секунд: {e}")
            time.sleep(5)
            return func(*args, **kwargs)
        except ccxt.RequestTimeout as e:
            self.log(f"⚠️ Таймаут запроса, повтор: {e}")
            time.sleep(2)
            return func(*args, **kwargs)
        except Exception as e:
            self.log(f"❌ Ошибка API: {e}", "ERROR")
            return None
    
    def get_candles(self, symbol, timeframe='15m', limit=100):
        """Получение свечных данных"""
        try:
            ohlcv = self.safe_api_call(
                self.exchange.fetch_ohlcv, symbol, timeframe, limit=limit
            )
            if ohlcv:
                df = pd.DataFrame(ohlcv, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
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
            if df is not None:
                # Добавляем базовые индикаторы для каждого ТФ
                df['ema9'] = ta.ema(df['close'], length=9)
                df['ema21'] = ta.ema(df['close'], length=21)
                df['rsi'] = ta.rsi(df['close'], length=14)
                df['adx'] = ta.adx(df['high'], df['low'], df['close'])['ADX_14']
                df['volume_sma'] = ta.sma(df['volume'], length=20)
                
                data[tf] = df
            time.sleep(0.2)  # Пауза между запросами
        
        return data
    
    def analyze_trend_multi_tf(self, data):
        """Анализ тренда по нескольким таймфреймам"""
        if not data:
            return "neutral", 0
        
        scores = []
        weights = []
        
        for tf, df in data.items():
            if df is None or len(df) < 20:
                continue
                
            curr = df.iloc[-1]
            weight = TIMEFRAME_WEIGHTS.get(tf, 0.1)
            
            # Оценка тренда для данного ТФ
            tf_score = 0
            
            # 1. EMA направление (вес 40%)
            if curr['ema9'] > curr['ema21']:
                tf_score += 0.4
            elif curr['ema9'] < curr['ema21']:
                tf_score -= 0.4
            
            # 2. RSI момент (вес 30%)
            rsi = curr['rsi']
            if 50 < rsi < 70:
                tf_score += 0.3
            elif 30 < rsi < 50:
                tf_score -= 0.3
            
            # 3. ADX сила тренда (вес 30%)
            adx = curr['adx']
            if adx > 25:
                if tf_score > 0:  # Бычий тренд
                    tf_score += 0.3
                elif tf_score < 0:  # Медвежий тренд
                    tf_score -= 0.3
            
            scores.append(tf_score * weight)
            weights.append(weight)
        
        if not scores:
            return "neutral", 0
        
        # Взвешенная сумма
        total_score = sum(scores) / sum(weights) if sum(weights) > 0 else 0
        
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
            return {"verdict": "NO", "reason": "AI не инициализирован"}
        
        prompt = f"""
        Ты опытный крипто-трейдер. Проанализируй торговую ситуацию:
        
        АКТИВ: {symbol}
        ЦЕНА: {price}
        
        ТРЕНД ПО ТАЙМФРЕЙМАМ:
        4h: {trend_data.get('4h', 'Нет данных')}
        1h: {trend_data.get('1h', 'Нет данных')}
        15m: {trend_data.get('15m', 'Нет данных')}
        
        ИНДИКАТОРЫ (15m):
        RSI: {indicators.get('rsi', 'N/A')}
        ADX: {indicators.get('adx', 'N/A')}
        EMA9/21: {indicators.get('ema_signal', 'N/A')}
        Объем: {indicators.get('volume_signal', 'N/A')}
        
        ТВОИ ПРАВИЛА:
        1. Подтверждай LONG если: все 3 ТФ бычьи, RSI < 65, ADX > 20
        2. Подтверждай SHORT если: все 3 ТФ медвежьи, RSI > 35, ADX > 20
        3. Отказывай если: RSI в экстремуме (>75 или <25), ADX < 15 (флэт)
        4. Будь осторожен при низких объемах
        
        Верни JSON строго в формате:
        {{
            "verdict": "YES" или "NO",
            "confidence": число от 1 до 10,
            "reason": "краткое объяснение",
            "recommended_action": "LONG", "SHORT" или "WAIT"
        }}
        """
        
        try:
            response = self.ai_client.chat.completions.create(
                model="deepseek-chat",
                messages=[{"role": "user", "content": prompt}],
                max_tokens=300,
                temperature=0.3
            )
            
            content = response.choices[0].message.content
            
            # Парсинг JSON из ответа
            try:
                # Ищем JSON в ответе
                import re
                json_match = re.search(r'\{.*\}', content, re.DOTALL)
                if json_match:
                    result = json.loads(json_match.group())
                    return result
            except:
                pass
            
            # Fallback: анализ текста
            if "YES" in content.upper():
                return {"verdict": "YES", "reason": "AI одобрил", "confidence": 7}
            else:
                return {"verdict": "NO", "reason": "AI отказал", "confidence": 3}
                
        except Exception as e:
            self.log(f"❌ Ошибка AI: {e}", "ERROR")
            return {"verdict": "NO", "reason": f"Ошибка AI: {str(e)}"}
    
    def calculate_position_size(self, symbol, risk_percent=STOP_LOSS_PERCENT):
        """Расчет размера позиции с учетом риска"""
        try:
            ticker = self.safe_api_call(self.exchange.fetch_ticker, symbol)
            if not ticker:
                return 0
            
            price = ticker['last']
            
            # Размер позиции в базовой валюте
            amount = (ORDER_AMOUNT_USD / price)
            
            # Учитываем плечо для фьючерсов
            if ":USDT" in symbol:
                # Для фьючерсов учитываем только маржу
                amount = amount * 0.1  # Консервативный подход
            
            return round(amount, 8)
            
        except Exception as e:
            self.log(f"❌ Ошибка расчета размера позиции: {e}", "ERROR")
            return 0
    
    def open_position(self, symbol, side, leverage=1):
        """Открытие позиции со стоп-лоссом и тейк-профитом"""
        try:
            # Проверяем, нет ли уже открытой позиции
            if symbol in self.positions:
                self.log(f"⚠️ Позиция {symbol} уже открыта", "WARNING")
                return False
            
            # Расчет размера
            amount = self.calculate_position_size(symbol)
            if amount <= 0:
                self.log(f"❌ Неверный размер позиции для {symbol}", "ERROR")
                return False
            
            # Установка плеча (для фьючерсов)
            if ":USDT" in symbol and leverage > 1:
                try:
                    self.safe_api_call(self.exchange.set_leverage, leverage, symbol)
                except Exception as e:
                    self.log(f"⚠️ Не удалось установить плечо: {e}", "WARNING")
            
            # Получаем текущую цену
            ticker = self.safe_api_call(self.exchange.fetch_ticker, symbol)
            if not ticker:
                return False
            
            entry_price = ticker['last']
            
            # Расчет стоп-лосса и тейк-профита
            if side.lower() == "buy":
                stop_price = entry_price * (1 - STOP_LOSS_PERCENT / 100)
                take_profit_price = entry_price * (1 + TAKE_PROFIT_PERCENT / 100)
            else:  # sell/short
                stop_price = entry_price * (1 + STOP_LOSS_PERCENT / 100)
                take_profit_price = entry_price * (1 - TAKE_PROFIT_PERCENT / 100)
            
            # Параметры ордера
            params = {}
            if ":USDT" in symbol:  # Для фьючерсов
                params['stopLoss'] = {'triggerPrice': stop_price, 'type': 'market'}
                params['takeProfit'] = {'triggerPrice': take_profit_price, 'type': 'market'}
            
            # Открытие ордера
            self.log(f"⚡ Открытие {side.upper()} позиции: {symbol}, размер: {amount}, цена: {entry_price}")
            
            order = self.safe_api_call(
                self.exchange.create_order,
                symbol,
                'market',
                side,
                amount,
                None,
                params
            )
            
            if order:
                self.positions[symbol] = {
                    'side': side,
                    'entry_price': entry_price,
                    'amount': amount,
                    'timestamp': datetime.now(),
                    'stop_loss': stop_price,
                    'take_profit': take_profit_price,
                    'order_id': order['id']
                }
                
                self.send_telegram(
                    f"🎯 **НОВАЯ ПОЗИЦИЯ**\n"
                    f"#{symbol.replace('/', '')}\n"
                    f"📈 Направление: {side.upper()}\n"
                    f"💰 Цена входа: ${entry_price:.2f}\n"
                    f"📊 Размер: ${ORDER_AMOUNT_USD}\n"
                    f"🛡️ Стоп-лосс: ${stop_price:.2f} ({STOP_LOSS_PERCENT}%)\n"
                    f"🎯 Тейк-профит: ${take_profit_price:.2f} ({TAKE_PROFIT_PERCENT}%)\n"
                    f"⏰ Время: {datetime.now().strftime('%H:%M:%S')}"
                )
                return True
            
        except Exception as e:
            self.log(f"❌ Ошибка открытия позиции {symbol}: {e}", "ERROR")
        
        return False
    
    def check_futures_signals(self):
        """Проверка сигналов для фьючерсов с мультитаймфреймами"""
        self.log("--- 🔍 СКАНИРОВАНИЕ ФЬЮЧЕРСОВ ---")
        
        for symbol, config in FUTURES_SYMBOLS.items():
            time.sleep(1)  # Базовая пауза
            
            try:
                # Получаем данные по всем таймфреймам
                timeframes = config.get("timeframes", ["4h", "1h", "15m"])
                data = self.get_multi_timeframe_data(symbol, timeframes)
                
                if not data:
                    continue
                
                # Анализируем тренд по всем ТФ
                trend, score = self.analyze_trend_multi_tf(data)
                
                # Получаем детали с 15m таймфрейма (для входа)
                tf_15m = data.get("15m") or data.get(list(data.keys())[-1])
                if tf_15m is None:
                    continue
                
                curr = tf_15m.iloc[-1]
                price = curr['close']
                rsi = curr['rsi']
                adx = curr['adx']
                
                # Логика для LONG
                if trend in ["bullish", "strong_bullish"] and score > 0.2:
                    # Дополнительные фильтры для входа
                    if 40 < rsi < 65 and adx > 20:
                        
                        # AI анализ
                        trend_data = {}
                        for tf in timeframes:
                            if tf in data:
                                tf_trend, _ = self.analyze_trend_multi_tf({tf: data[tf]})
                                trend_data[tf] = tf_trend
                        
                        ai_result = self.ask_ai_analysis(
                            symbol, trend_data, price,
                            {"rsi": rsi, "adx": adx, "ema_signal": "bullish"}
                        )
                        
                        if ai_result.get("verdict") == "YES":
                            self.log(f"✅ LONG сигнал для {symbol}, уверенность AI: {ai_result.get('confidence')}/10")
                            self.open_position(symbol, "buy", config["lev"])
                
                # Логика для SHORT
                elif trend in ["bearish", "strong_bearish"] and score < -0.2:
                    if 35 < rsi < 60 and adx > 20:
                        
                        trend_data = {}
                        for tf in timeframes:
                            if tf in data:
                                tf_trend, _ = self.analyze_trend_multi_tf({tf: data[tf]})
                                trend_data[tf] = tf_trend
                        
                        ai_result = self.ask_ai_analysis(
                            symbol, trend_data, price,
                            {"rsi": rsi, "adx": adx, "ema_signal": "bearish"}
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
                timeframes = config.get("timeframes", ["1d", "4h", "1h"])
                data = self.get_multi_timeframe_data(symbol, timeframes)
                
                if not data:
                    continue
                
                # Анализ для спота (более консервативный)
                tf_4h = data.get("4h") or data.get("1h")
                if tf_4h is None:
                    continue
                
                curr = tf_4h.iloc[-1]
                price = curr['close']
                rsi = curr['rsi']
                
                # BUY сигнал: сильная перепроданность на старших ТФ
                if rsi < 30 and symbol not in self.spot_signals:
                    trend, score = self.analyze_trend_multi_tf(data)
                    if trend in ["bullish", "strong_bullish"]:
                        self.spot_signals[symbol] = {
                            "type": "BUY",
                            "price": price,
                            "timestamp": datetime.now(),
                            "rsi": rsi
                        }
                        
                        self.send_telegram(
                            f"💎 **SPOT BUY SIGNAL**\n"
                            f"#{symbol.replace('/', '')}\n"
                            f"📉 Сильная перепроданность (RSI: {rsi:.1f})\n"
                            f"💰 Цена: ${price:.2f}\n"
                            f"📊 Тренд: {trend}\n"
                            f"⏰ Время для DCA входа!"
                        )
                
                # SELL сигнал: сильная перекупленность
                elif rsi > 75 and symbol in self.spot_signals:
                    if self.spot_signals[symbol]["type"] == "BUY":
                        entry_price = self.spot_signals[symbol]["price"]
                        profit_pct = ((price - entry_price) / entry_price) * 100
                        
                        if profit_pct > 5:  # Минимальная прибыль 5%
                            self.send_telegram(
                                f"💰 **SPOT TAKE PROFIT**\n"
                                f"#{symbol.replace('/', '')}\n"
                                f"📈 Перекупленность (RSI: {rsi:.1f})\n"
                                f"💰 Цена: ${price:.2f}\n"
                                f"📊 Прибыль: {profit_pct:.1f}%\n"
                                f"💵 Фиксируйте прибыль!"
                            )
                            del self.spot_signals[symbol]
                            
            except Exception as e:
                self.log(f"❌ Ошибка спот анализа {symbol}: {e}", "ERROR")
    
    def monitor_positions(self):
        """Мониторинг открытых позиций"""
        if not self.positions:
            return
        
        self.log(f"--- 📊 МОНИТОРИНГ {len(self.positions)} ПОЗИЦИЙ ---")
        
        for symbol, pos in list(self.positions.items()):
            try:
                # Получаем текущую цену
                ticker = self.safe_api_call(self.exchange.fetch_ticker, symbol)
                if not ticker:
                    continue
                
                current_price = ticker['last']
                entry_price = pos['entry_price']
                
                if pos['side'] == "buy":
                    pnl_pct = ((current_price - entry_price) / entry_price) * 100
                else:  # sell/short
                    pnl_pct = ((entry_price - current_price) / entry_price) * 100
                
                # Проверка стоп-лосса и тейк-профита
                stop_loss = pos['stop_loss']
                take_profit = pos['take_profit']
                
                should_close = False
                reason = ""
                
                if pos['side'] == "buy":
                    if current_price <= stop_loss:
                        should_close = True
                        reason = f"Стоп-лосс ({pnl_pct:.1f}%)"
                    elif current_price >= take_profit:
                        should_close = True
                        reason = f"Тейк-профит ({pnl_pct:.1f}%)"
                else:  # short
                    if current_price >= stop_loss:
                        should_close = True
                        reason = f"Стоп-лосс ({pnl_pct:.1f}%)"
                    elif current_price <= take_profit:
                        should_close = True
                        reason = f"Тейк-профит ({pnl_pct:.1f}%)"
                
                # Закрытие позиции при срабатывании условий
                if should_close:
                    self.close_position(symbol, reason, pnl_pct)
                    
                # Логирование состояния
                elif abs(pnl_pct) > 1:  # Логируем только при значительном изменении
                    status = "🟢" if pnl_pct > 0 else "🔴"
                    self.log(f"{status} {symbol}: {pnl_pct:.2f}%")
                    
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
                # Обновляем дневной PnL
                self.daily_pnl += pnl_pct
                
                # Отправляем уведомление
                emoji = "✅" if pnl_pct > 0 else "❌"
                self.send_telegram(
                    f"{emoji} **ПОЗИЦИЯ ЗАКРЫТА**\n"
                    f"#{symbol.replace('/', '')}\n"
                    f"📊 Причина: {reason}\n"
                    f"💰 PnL: {pnl_pct:.2f}%\n"
                    f"📈 Всего сделок: {len(self.positions)}\n"
                    f"📊 Дневной PnL: {self.daily_pnl:.2f}%"
                )
                
                # Удаляем из активных позиций
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
                "parse_mode": "Markdown",
                "disable_web_page_preview": True
            }
            
            response = requests.post(url, json=payload, timeout=10)
            if response.status_code != 200:
                self.log(f"⚠️ Ошибка отправки в Telegram: {response.text}", "WARNING")
                
        except Exception as e:
            self.log(f"⚠️ Не удалось отправить в Telegram: {e}", "WARNING")
    
    def run_cycle(self):
        """Запуск одного цикла анализа"""
        cycle_start = time.time()
        
        try:
            # Шаг 1: Мониторинг текущих позиций
            self.monitor_positions()
            
            # Шаг 2: Проверка новых сигналов (если есть место)
            if len(self.positions) < MAX_POSITIONS:
                self.check_futures_signals()
                self.check_spot_signals()
            else:
                self.log(f"⚠️ Достигнут лимит позиций ({MAX_POSITIONS})")
            
            # Шаг 3: Отчет о состоянии
            self.print_status()
            
        except Exception as e:
            self.log(f"❌ Критическая ошибка в цикле: {e}", "ERROR")
        
        # Расчет времени цикла
        cycle_time = time.time() - cycle_start
        sleep_time = max(10, 60 - cycle_time)  # Минимум 10 секунд между циклами
        
        self.log(f"🔄 Цикл завершен за {cycle_time:.1f}с, следующая проверка через {sleep_time:.0f}с")
        return sleep_time
    
    def print_status(self):
        """Вывод статуса системы"""
        status = f"""
{'='*50}
📊 СТАТУС ТОРГОВОГО АГЕНТА
{'='*50}
⏰ Время: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
⏳ Работает: {datetime.now() - self.start_time}
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
            self.send_telegram(f"💥 *Критическая ошибка:* {str(e)}")
            raise

# --- 🚀 ЗАПУСК ПРОГРАММЫ ---
if __name__ == "__main__":
    # Проверка обязательных переменных
    required_vars = ["OKX_API_KEY", "OKX_API_SECRET", "OKX_PASSWORD"]
    missing_vars = [var for var in required_vars if not os.getenv(var)]
    
    if missing_vars:
        print(f"❌ Отсутствуют переменные окружения: {', '.join(missing_vars)}")
        print("📝 Создайте файл .env с необходимыми переменными.")
        exit(1)
    
    # Создание и запуск агента
    try:
        agent = TradingAgent()
        agent.run()
    except Exception as e:
        print(f"❌ Не удалось запустить агента: {e}")
