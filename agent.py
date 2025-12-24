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

# Параметры анализа
ANALYSIS_TIMEFRAME = "15m"  # Таймфрейм для анализа
SIGNAL_COOLDOWN_MINUTES = 30  # Задержка между одинаковыми сигналами

# --- 📊 ТОРГОВЫЕ ПАРЫ ---
# Убрал global - использую просто константы
FUTURES_SYMBOLS = {
    "BTC/USDT:USDT": {"lev": 5},
    "ETH/USDT:USDT": {"lev": 5},
    "SOL/USDT:USDT": {"lev": 5},
    "TON/USDT:USDT": {"lev": 3},
    "DOGE/USDT:USDT": {"lev": 3},
    "PEPE/USDT:USDT": {"lev": 3},
    "XRP/USDT:USDT": {"lev": 3},
    "ADA/USDT:USDT": {"lev": 3},
    "MATIC/USDT:USDT": {"lev": 3},
    "LINK/USDT:USDT": {"lev": 3},
    "AVAX/USDT:USDT": {"lev": 3},
}

SPOT_SYMBOLS = {
    "BTC/USDT": {},
    "ETH/USDT": {},
    "SOL/USDT": {},
    "TON/USDT": {},
}

class TradingAgent:
    def __init__(self):
        """Инициализация торгового агента"""
        self.setup_logging()
        
        # Проверка настроек безопасности
        self.check_security()
        
        # Инициализация API (только для получения данных)
        self.init_exchange()
        self.init_ai()
        
        # История сигналов (чтобы избежать спама)
        self.signal_history = {}
        self.last_check_time = datetime.now()
        
        # Копируем символы в атрибуты класса
        self.futures_symbols = dict(FUTURES_SYMBOLS)
        self.spot_symbols = dict(SPOT_SYMBOLS)
        
        print(f"✅ Аналитический агент инициализирован: {datetime.now()}")
        print(f"📊 Режим: ТОЛЬКО АНАЛИЗ (без автоторговли)")
        print(f"⏰ Таймфрейм анализа: {ANALYSIS_TIMEFRAME}")
        print(f"🔔 Задержка между сигналами: {SIGNAL_COOLDOWN_MINUTES} мин")
        print(f"📈 Пар для анализа: {len(self.futures_symbols)} фьючерсов, {len(self.spot_symbols)} спотовых")
    
    def setup_logging(self):
        """Настройка системы логирования"""
        log_dir = "logs"
        if not os.path.exists(log_dir):
            os.makedirs(log_dir)
        
        self.log_file = f"{log_dir}/signals_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log"
    
    def check_security(self):
        """Проверка безопасности настроек"""
        # Проверяем только AI ключ для анализа
        if not DEEPSEEK_API_KEY:
            self.log("⚠️ ВНИМАНИЕ: Не задан DEEPSEEK_API_KEY")
            print("""
            ⚠️  ВНИМАНИЕ: Без AI ключа анализ будет ограничен:
            
            Задайте переменную окружения:
            DEEPSEEK_API_KEY=ваш_ключ_deepseek
            
            Для получения данных с биржи также нужны:
            OKX_API_KEY=ваш_api_key_okx
            OKX_API_SECRET=ваш_api_secret_okx  
            OKX_PASSWORD=ваш_api_password_okx
            """)
    
    def init_exchange(self):
        """Инициализация подключения к бирже (только для данных)"""
        try:
            if all([API_KEY, API_SECRET, API_PASSWORD]):
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
            else:
                self.exchange = None
                print("⚠️ Ключи OKX не заданы, используем публичные данные")
                
        except Exception as e:
            self.log(f"⚠️ Не удалось подключиться к OKX: {e}")
            self.exchange = None
            print("⚠️ Будет использоваться публичный доступ к данным")
    
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
    
    def get_candles(self, symbol, timeframe='15m', limit=100):
        """Получение свечных данных"""
        try:
            # Если есть подключение к бирже, используем его
            if self.exchange:
                ohlcv = self.exchange.fetch_ohlcv(symbol, timeframe, limit=limit)
            else:
                # Иначе используем публичный API без ключей
                exchange_public = ccxt.okx()
                ohlcv = exchange_public.fetch_ohlcv(symbol, timeframe, limit=limit)
            
            # Безопасная проверка данных
            if not ohlcv or not isinstance(ohlcv, list) or len(ohlcv) == 0:
                return None
                
            df = pd.DataFrame(ohlcv, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
            
            # Явная проверка DataFrame
            if df.empty or len(df) < 10:
                return None
                
            return df
            
        except Exception as e:
            self.log(f"❌ Ошибка получения данных {symbol} {timeframe}: {e}", "ERROR")
            return None
    
    def calculate_indicators(self, df):
        """Расчет индикаторов"""
        if df is None or df.empty:
            return None
        
        try:
            # EMA
            df['ema9'] = ta.ema(df['close'], length=9)
            df['ema21'] = ta.ema(df['close'], length=21)
            
            # RSI
            df['rsi'] = ta.rsi(df['close'], length=14)
            
            # ADX
            adx_result = ta.adx(df['high'], df['low'], df['close'])
            if adx_result is not None and 'ADX_14' in adx_result:
                df['adx'] = adx_result['ADX_14']
            else:
                df['adx'] = 25
            
            return df
            
        except Exception as e:
            self.log(f"❌ Ошибка расчета индикаторов: {e}", "ERROR")
            return None
    
    def ask_ai_analysis(self, symbol, price, rsi, adx, signal_type, trend_info=""):
        """AI анализ сигнала"""
        if not self.ai_client:
            return "AI не доступен"
        
        print(f"🧠 AI анализ для {symbol} ({signal_type})...")
        
        prompt = f"""
        Ты криптотрейдер-аналитик. Проанализируй ситуацию:
        
        📊 Актив: {symbol}
        💰 Цена: {price}
        📈 Сигнал: {signal_type}
        📊 Тех.индикаторы:
        - RSI: {rsi}
        - ADX: {adx}
        {trend_info}
        
        📋 ПРАВИЛА АНАЛИЗА:
        1. Для BUY/LONG: RSI < 65, ADX > 20, тренд восходящий
        2. Для SELL/SHORT: RSI > 35, ADX > 20, тренд нисходящий
        3. Если ADX < 15 - рынок во флэте, избегай входов
        4. RSI > 75 - перекупленность, RSI < 25 - перепроданность
        
        🔍 Вердикт: 
        - "STRONG_BUY" - сильный сигнал на покупку
        - "BUY" - умеренный сигнал на покупку  
        - "NEUTRAL" - нейтрально, жди
        - "SELL" - умеренный сигнал на продажу
        - "STRONG_SELL" - сильный сигнал на продажу
        
        📝 Объяснение: кратко объясни решение (1-2 предложения)
        
        📌 Формат ответа:
        Вердикт: [STRONG_BUY/BUY/NEUTRAL/SELL/STRONG_SELL]
        Уверенность: [1-10]/10
        Объяснение: [твое объяснение]
        """
        
        try:
            response = self.ai_client.chat.completions.create(
                model="deepseek-chat",
                messages=[{"role": "user", "content": prompt}],
                max_tokens=200,
                temperature=0.3
            )
            
            return response.choices[0].message.content
            
        except Exception as e:
            self.log(f"❌ Ошибка AI анализа: {e}", "ERROR")
            return f"Ошибка AI анализа: {e}"
    
    def check_signal_cooldown(self, symbol, signal_type):
        """Проверка времени с последнего сигнала"""
        key = f"{symbol}_{signal_type}"
        
        if key in self.signal_history:
            last_time = self.signal_history[key]
            time_diff = (datetime.now() - last_time).total_seconds() / 60
            
            if time_diff < SIGNAL_COOLDOWN_MINUTES:
                return False
        
        self.signal_history[key] = datetime.now()
        return True
    
    def analyze_futures(self):
        """Анализ фьючерсных пар"""
        self.log("--- 🔍 АНАЛИЗ ФЬЮЧЕРСОВ (Long/Short) ---")
        
        signals_found = 0
        
        for symbol, config in self.futures_symbols.items():
            time.sleep(1)  # Пауза между запросами
            
            try:
                # Получаем данные
                df = self.get_candles(symbol, ANALYSIS_TIMEFRAME, 100)
                if df is None:
                    continue
                
                # Расчет индикаторов
                df = self.calculate_indicators(df)
                if df is None:
                    continue
                
                # Текущие значения
                curr = df.iloc[-1]
                price = curr['close']
                rsi = curr['rsi'] if 'rsi' in curr else 50
                adx = curr['adx'] if 'adx' in curr else 25
                ema9 = curr['ema9'] if 'ema9' in curr else price
                ema21 = curr['ema21'] if 'ema21' in curr else price
                
                signal = None
                signal_type = ""
                trend_info = ""
                
                # 📈 LONG сигнал
                if ema9 > ema21 and 40 < rsi < 65 and adx > 20:
                    signal = "BUY"
                    signal_type = "LONG_SIGNAL"
                    trend_info = f"- Тренд: EMA9 ({ema9:.2f}) > EMA21 ({ema21:.2f}) - восходящий"
                
                # 📉 SHORT сигнал  
                elif ema9 < ema21 and 35 < rsi < 60 and adx > 20:
                    signal = "SELL"
                    signal_type = "SHORT_SIGNAL"
                    trend_info = f"- Тренд: EMA9 ({ema9:.2f}) < EMA21 ({ema21:.2f}) - нисходящий"
                
                # Если есть сигнал
                if signal and self.check_signal_cooldown(symbol, signal_type):
                    
                    # 🔍 AI анализ
                    ai_response = self.ask_ai_analysis(
                        symbol, price, round(rsi, 1), round(adx, 1), signal_type, trend_info
                    )
                    
                    # Отправляем сигнал в Telegram
                    self.send_signal_to_telegram(
                        symbol=symbol,
                        signal_type=signal,
                        signal_name=signal_type,
                        price=price,
                        rsi=rsi,
                        adx=adx,
                        ai_analysis=ai_response,
                        timeframe=ANALYSIS_TIMEFRAME,
                        leverage=config["lev"]
                    )
                    
                    signals_found += 1
                    self.log(f"✅ Найден сигнал {signal} для {symbol}")
            
            except Exception as e:
                self.log(f"❌ Ошибка анализа {symbol}: {e}", "ERROR")
        
        return signals_found
    
    def analyze_spot(self):
        """Анализ спотовых пар"""
        self.log("--- 🏦 АНАЛИЗ СПОТОВЫХ ПАР (4H) ---")
        
        signals_found = 0
        
        for symbol, config in self.spot_symbols.items():
            time.sleep(1)
            
            try:
                # Для спота используем 4H таймфрейм
                df = self.get_candles(symbol, "4H", 50)
                if df is None:
                    continue
                
                # Расчет RSI
                df['rsi'] = ta.rsi(df['close'], length=14)
                
                curr = df.iloc[-1]
                price = curr['close']
                rsi = curr['rsi'] if 'rsi' in curr else 50
                
                signal = None
                signal_type = ""
                
                # 💎 BUY сигнал (перепроданность)
                if rsi < 30:
                    signal = "BUY"
                    signal_type = "SPOT_BUY_DIP"
                
                # 💰 SELL сигнал (перекупленность)
                elif rsi > 75:
                    signal = "SELL"
                    signal_type = "SPOT_TAKE_PROFIT"
                
                # Если есть сигнал
                if signal and self.check_signal_cooldown(symbol, signal_type):
                    
                    # 🔍 AI анализ
                    ai_response = self.ask_ai_analysis(
                        symbol, price, round(rsi, 1), 25, signal_type, 
                        f"- RSI: {rsi:.1f} ({'сильная перепроданность' if rsi < 30 else 'сильная перекупленность'})"
                    )
                    
                    # Отправляем сигнал
                    self.send_signal_to_telegram(
                        symbol=symbol,
                        signal_type=signal,
                        signal_name=signal_type,
                        price=price,
                        rsi=rsi,
                        adx=25,
                        ai_analysis=ai_response,
                        timeframe="4H",
                        leverage=1
                    )
                    
                    signals_found += 1
                    self.log(f"✅ Найден спот сигнал {signal} для {symbol}")
            
            except Exception as e:
                self.log(f"❌ Ошибка спот анализа {symbol}: {e}", "ERROR")
        
        return signals_found
    
    def send_signal_to_telegram(self, symbol, signal_type, signal_name, price, rsi, adx, ai_analysis, timeframe, leverage=1):
        """Отправка сигнала в Telegram"""
        if not TELEGRAM_BOT_TOKEN or not TELEGRAM_CHAT_ID:
            self.log("⚠️ Telegram ключи не заданы, пропускаем уведомление")
            return
        
        try:
            import requests
            
            # Эмодзи для сигналов
            emoji = "🟢" if signal_type == "BUY" else "🔴"
            action = "ПОКУПКА/LONG" if signal_type == "BUY" else "ПРОДАЖА/SHORT"
            
            # Форматируем AI анализ
            ai_lines = ai_analysis.split('\n')
            ai_formatted = ""
            for line in ai_lines:
                if 'Вердикт:' in line:
                    ai_formatted += f"🎯 *{line.strip()}*\n"
                elif 'Уверенность:' in line:
                    ai_formatted += f"📊 {line.strip()}\n"
                elif 'Объяснение:' in line:
                    ai_formatted += f"💡 {line.strip().replace('Объяснение:', '')}\n"
                else:
                    ai_formatted += f"{line.strip()}\n"
            
            # Создаем сообщение
            message = f"""
{emoji} *{action} СИГНАЛ*

📊 *Пара:* #{symbol.replace('/', '').replace(':USDT', '')}
⏰ *Таймфрейм:* {timeframe}
💰 *Цена:* ${price:.4f}
📈 *RSI:* {rsi:.1f}
📊 *ADX:* {adx:.1f}
⚡ *Сигнал:* {signal_name}

🤖 *AI АНАЛИЗ:*
{ai_formatted}

📌 *Рекомендации:*
- Используйте лимитные ордера
- Всегда ставьте стоп-лосс
- Рискуйте не более 1-2% от депозита
"""
            if leverage > 1:
                message += f"⚙️ *Плечо:* {leverage}x (опционально)\n"
            
            message += f"\n⏰ *Время сигнала:* {datetime.now().strftime('%H:%M:%S')}"
            
            # Отправляем в Telegram
            url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
            payload = {
                "chat_id": TELEGRAM_CHAT_ID,
                "text": message,
                "parse_mode": "Markdown",
                "disable_web_page_preview": True
            }
            
            response = requests.post(url, json=payload, timeout=10)
            
            if response.status_code == 200:
                self.log(f"✅ Сигнал отправлен в Telegram: {symbol} {signal_type}")
            else:
                self.log(f"⚠️ Ошибка отправки в Telegram: {response.text}", "WARNING")
                
        except Exception as e:
            self.log(f"❌ Ошибка отправки Telegram: {e}", "ERROR")
    
    def run_analysis_cycle(self):
        """Запуск одного цикла анализа"""
        self.log(f"\n{'='*60}")
        self.log(f"🔍 НАЧАЛО АНАЛИЗА: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        self.log(f"{'='*60}")
        
        total_signals = 0
        
        try:
            # Анализ фьючерсов
            futures_signals = self.analyze_futures()
            total_signals += futures_signals
            
            # Анализ спота
            spot_signals = self.analyze_spot()
            total_signals += spot_signals
            
            # Статистика
            self.log(f"\n📊 ИТОГИ ЦИКЛА:")
            self.log(f"   Фьючерсных сигналов: {futures_signals}")
            self.log(f"   Спотовых сигналов: {spot_signals}")
            self.log(f"   Всего сигналов: {total_signals}")
            
            if total_signals == 0:
                self.log("   ℹ️ Сигналов не найдено")
            
            self.log(f"{'='*60}")
            
        except Exception as e:
            self.log(f"💥 Критическая ошибка в цикле анализа: {e}", "ERROR")
        
        return total_signals
    
    def print_status(self):
        """Вывод статуса системы"""
        status = f"""
{'='*50}
🤖 АНАЛИТИЧЕСКИЙ АГЕНТ - ТОЛЬКО СИГНАЛЫ
{'='*50}
⏰ Время: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
⏳ Следующий анализ через: {ANALYSIS_TIMEFRAME}
📊 Анализируем пар: {len(self.futures_symbols)} фьюч., {len(self.spot_symbols)} спот
🔔 Задержка сигналов: {SIGNAL_COOLDOWN_MINUTES} мин
🤖 AI анализ: {'✅ ВКЛ' if self.ai_client else '❌ ВЫКЛ'}
{'='*50}
"""
        print(status)
    
    def run(self):
        """Главный цикл работы бота"""
        self.log("🚀 ЗАПУСК АНАЛИТИЧЕСКОГО АГЕНТА (ТОЛЬКО СИГНАЛЫ)")
        
        if TELEGRAM_BOT_TOKEN and TELEGRAM_CHAT_ID:
            try:
                self.send_signal_to_telegram(
                    symbol="SYSTEM",
                    signal_type="INFO",
                    signal_name="BOT_STARTED",
                    price=0,
                    rsi=50,
                    adx=25,
                    ai_analysis="🤖 Бот аналитики запущен\nВердикт: SYSTEM_READY\nУверенность: 10/10\nОбъяснение: Аналитический агент начал работу",
                    timeframe="SYSTEM",
                    leverage=1
                )
            except:
                pass
        
        try:
            cycle_count = 0
            
            while True:
                cycle_count += 1
                self.print_status()
                
                # Запускаем анализ
                signals_found = self.run_analysis_cycle()
                
                # Определяем время до следующего анализа
                if ANALYSIS_TIMEFRAME == "15m":
                    sleep_time = 60 * 15  # 15 минут
                elif ANALYSIS_TIMEFRAME == "1h":
                    sleep_time = 60 * 60  # 1 час
                elif ANALYSIS_TIMEFRAME == "4H":
                    sleep_time = 60 * 60 * 4  # 4 часа
                else:
                    sleep_time = 60 * 5  # 5 минут по умолчанию
                
                # Выводим информацию о следующем анализе
                next_time = datetime.now().timestamp() + sleep_time
                next_str = datetime.fromtimestamp(next_time).strftime('%H:%M:%S')
                self.log(f"⏰ Следующий анализ в {next_str} (через {sleep_time//60} мин)")
                
                # Ждем до следующего анализа
                time.sleep(sleep_time)
                
        except KeyboardInterrupt:
            self.log("🛑 Остановка по команде пользователя")
            
            if TELEGRAM_BOT_TOKEN and TELEGRAM_CHAT_ID:
                try:
                    self.send_signal_to_telegram(
                        symbol="SYSTEM",
                        signal_type="INFO",
                        signal_name="BOT_STOPPED",
                        price=0,
                        rsi=50,
                        adx=25,
                        ai_analysis="🛑 Бот аналитики остановлен\nВердикт: SYSTEM_STOPPED\nУверенность: 10/10\nОбъяснение: Аналитический агент завершил работу",
                        timeframe="SYSTEM",
                        leverage=1
                    )
                except:
                    pass
            
        except Exception as e:
            self.log(f"💥 Критическая ошибка: {e}", "CRITICAL")

# --- 🚀 ЗАПУСК ПРОГРАММЫ ---
if __name__ == "__main__":
    print("\n" + "="*60)
    print("🤖 АНАЛИТИЧЕСКИЙ АГЕНТ - ТОЛЬКО СИГНАЛЫ")
    print("="*60)
    print("📊 Функции:")
    print("  ✅ Анализ рынка с индикаторами")
    print("  ✅ AI анализ сигналов (DeepSeek)")
    print("  ✅ Уведомления в Telegram")
    print("  ❌ Автоторговля ОТКЛЮЧЕНА")
    print("="*60)
    
    # Создание и запуск агента
    try:
        agent = TradingAgent()
        agent.run()
    except Exception as e:
        print(f"❌ Не удалось запустить агента: {e}")
