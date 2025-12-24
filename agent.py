# bot_runner.py
import os
import sys
import signal
import time
from datetime import datetime
from agent import TradingAgent

def signal_handler(sig, frame):
    """Обработчик сигналов для корректного завершения"""
    print(f'\n🛑 [{datetime.now().strftime("%H:%M:%S")}] Получен сигнал остановки')
    sys.exit(0)

def check_environment():
    """Проверка переменных окружения"""
    print("🔍 Проверка настроек...")
    
    required_vars = []
    optional_vars = []
    
    # Обязательные для базовой работы (AI и Telegram опциональны)
    if not os.getenv("OKX_API_KEY") and not os.getenv("OKX_API_SECRET") and not os.getenv("OKX_PASSWORD"):
        print("⚠️  ВНИМАНИЕ: Ключи OKX не заданы")
        print("   Будет использоваться публичный доступ к данным (лимитированный)")
    
    # Проверка Telegram
    if not os.getenv("TELEGRAM_BOT_TOKEN") or not os.getenv("TELEGRAM_CHAT_ID"):
        print("⚠️  ВНИМАНИЕ: Telegram уведомления отключены")
        print("   Для получения сигналов задайте:")
        print("   - TELEGRAM_BOT_TOKEN")
        print("   - TELEGRAM_CHAT_ID")
    else:
        print("✅ Telegram настройки: OK")
    
    # Проверка DeepSeek
    if not os.getenv("DEEPSEEK_API_KEY"):
        print("⚠️  ВНИМАНИЕ: AI анализ отключен")
        print("   Для AI анализа задайте DEEPSEEK_API_KEY")
    else:
        print("✅ DeepSeek AI: OK")
    
    return True

def send_telegram_startup(bot_token, chat_id):
    """Отправка уведомления о запуске"""
    if not bot_token or not chat_id:
        return False
    
    try:
        import requests
        message = f"""
🤖 *АНАЛИТИЧЕСКИЙ БОТ ЗАПУЩЕН*

⏰ Время: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
📊 Режим: ТОЛЬКО СИГНАЛЫ
⚡ Статус: РАБОТАЕТ

*Функции:*
✅ Анализ рынка (индикаторы)
✅ AI фильтрация сигналов
✅ Уведомления в Telegram
❌ Автоторговля отключена

*Параметры:*
📈 Таймфрейм: 15m (фьючерсы), 4H (спот)
🔔 Задержка сигналов: 30 минут
🤖 AI анализ: {'ВКЛЮЧЕН' if os.getenv("DEEPSEEK_API_KEY") else 'ОТКЛЮЧЕН'}

Бот начал мониторинг рынка...
        """
        
        url = f"https://api.telegram.org/bot{bot_token}/sendMessage"
        payload = {
            "chat_id": chat_id,
            "text": message,
            "parse_mode": "Markdown",
            "disable_web_page_preview": True
        }
        
        response = requests.post(url, json=payload, timeout=10)
        return response.status_code == 200
        
    except Exception as e:
        print(f"❌ Ошибка отправки стартового уведомления: {e}")
        return False

def main():
    """Главная функция запуска"""
    print("\n" + "="*60)
    print("🤖 АНАЛИТИЧЕСКИЙ АГЕНТ - ТОЛЬКО СИГНАЛЫ")
    print("="*60)
    print("📊 Автор: Trading Bot AI Assistant")
    print("📅 Дата: " + datetime.now().strftime("%Y-%m-%d"))
    print("⏰ Время: " + datetime.now().strftime("%H:%M:%S"))
    print("="*60)
    
    # Регистрация обработчика сигналов
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    # Проверка окружения
    check_environment()
    
    # Попытка отправить уведомление о запуске
    bot_token = os.getenv("TELEGRAM_BOT_TOKEN")
    chat_id = os.getenv("TELEGRAM_CHAT_ID")
    
    if bot_token and chat_id:
        print("\n📨 Отправка уведомления о запуске в Telegram...")
        if send_telegram_startup(bot_token, chat_id):
            print("✅ Стартовое уведомление отправлено")
        else:
            print("⚠️  Не удалось отправить стартовое уведомление")
    else:
        print("\n⚠️  Telegram уведомления отключены")
    
    print("\n" + "="*60)
    print("🚀 ЗАПУСК АГЕНТА...")
    print("="*60)
    print("⚡ Бот начинает работу через 5 секунд")
    print("🛑 Для остановки нажмите Ctrl+C")
    print("="*60)
    
    time.sleep(5)  # Пауза перед запуском
    
    try:
        # Создание и запуск агента
        agent = TradingAgent()
        
        # Запуск основного цикла
        agent.run()
        
    except KeyboardInterrupt:
        print(f"\n🛑 [{datetime.now().strftime('%H:%M:%S')}] Остановка по команде пользователя")
        
        # Отправка уведомления об остановке
        if bot_token and chat_id:
            try:
                import requests
                message = f"""
🛑 *АНАЛИТИЧЕСКИЙ БOT ОСТАНОВЛЕН*

⏰ Время: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
📊 Статус: ВЫКЛЮЧЕН

Бот был остановлен пользователем.
До новых сигналов! 👋
                """
                
                url = f"https://api.telegram.org/bot{bot_token}/sendMessage"
                payload = {
                    "chat_id": chat_id,
                    "text": message,
                    "parse_mode": "Markdown"
                }
                
                requests.post(url, json=payload, timeout=5)
                print("✅ Уведомление об остановке отправлено")
            except:
                print("⚠️  Не удалось отправить уведомление об остановке")
        
    except Exception as e:
        print(f"\n💥 КРИТИЧЕСКАЯ ОШИБКА: {e}")
        print("🔄 Перезапустите бот вручную")
        
        # Отправка уведомления об ошибке
        if bot_token and chat_id:
            try:
                import requests
                message = f"""
💥 *БОТ АВАРИЙНО ОСТАНОВЛЕН*

⏰ Время: {datetime.now().strftime('%H:%M:%S')}
❌ Ошибка: {str(e)[:100]}
📊 Статус: АВАРИЯ

Требуется ручной перезапуск!
                """
                
                url = f"https://api.telegram.org/bot{bot_token}/sendMessage"
                payload = {
                    "chat_id": chat_id,
                    "text": message,
                    "parse_mode": "Markdown"
                }
                
                requests.post(url, json=payload, timeout=5)
            except:
                pass
        
        sys.exit(1)
    
    print(f"\n✅ [{datetime.now().strftime('%H:%M:%S')}] Работа завершена корректно")

if __name__ == "__main__":
    main()
