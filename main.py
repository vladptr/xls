import os
import sys
import asyncio
import discord

# Добавляем обработку ошибок при импорте
print("=" * 50)
print("📦 НАЧАЛО ИМПОРТА МОДУЛЕЙ")
print("=" * 50)

try:
    print("[1/5] Импорт modules.config...")
    from modules.config import bot
    print("✅ modules.config импортирован")
except Exception as e:
    print(f"❌ КРИТИЧЕСКАЯ ОШИБКА при импорте modules.config: {e}")
    import traceback
    traceback.print_exc()
    # Не завершаем процесс сразу - даем возможность увидеть другие ошибки
    raise

try:
    print("[2/5] Импорт modules.database...")
    from modules.database import init_db
    print("✅ modules.database импортирован")
except Exception as e:
    print(f"⚠️ Ошибка при импорте modules.database: {e}")
    init_db = None

try:
    print("[3/5] Импорт modules.events...")
    import modules.events  # Импортируем events ПЕРЕД commands, чтобы избежать конфликтов
    print("✅ modules.events импортирован")
except Exception as e:
    print(f"❌ КРИТИЧЕСКАЯ ОШИБКА при импорте modules.events: {e}")
    import traceback
    traceback.print_exc()
    raise

try:
    print("[4/5] Импорт modules.commands...")
    import modules.commands  # Импортируем commands ПОСЛЕ events
    print("✅ modules.commands импортирован")
except Exception as e:
    print(f"❌ КРИТИЧЕСКАЯ ОШИБКА при импорте modules.commands: {e}")
    import traceback
    traceback.print_exc()
    raise

try:
    print("[5/5] Импорт RegistrationView...")
    from modules.registration import RegistrationView
    print("✅ RegistrationView импортирован")
except Exception as e:
    print(f"❌ КРИТИЧЕСКАЯ ОШИБКА при импорте RegistrationView: {e}")
    import traceback
    traceback.print_exc()
    raise

print("=" * 50)
print("✅ ВСЕ МОДУЛИ УСПЕШНО ИМПОРТИРОВАНЫ")
print("=" * 50)

# Попытка импортировать webserver (если есть)
try:
    from webserver import keep_alive
    HAS_WEBSERVER = True
    print("✅ webserver найден")
except ImportError:
    HAS_WEBSERVER = False
    print("⚠️ webserver.py не найден, пропускаем keep_alive")

async def main():
    print("=" * 50)
    print("🚀 НАЧАЛО ЗАПУСКА БОТА")
    print("=" * 50)
    
    try:
        # Запускаем webserver если доступен (для некоторых хостингов)
        if HAS_WEBSERVER:
            print("[1/7] 🌐 Запуск webserver...")
            try:
                keep_alive()
                print("✅ Webserver запущен")
            except Exception as e:
                print(f"⚠️ Ошибка webserver: {e}")
        else:
            print("[1/7] ⏭️ Webserver пропущен")
        
        # Инициализируем базу данных (не блокируем запуск при ошибке)
        print("[2/7] 💾 Инициализация базы данных...")
        if init_db:
            try:
                init_db()
                print("✅ База данных инициализирована")
            except Exception as e:
                print(f"⚠️ Предупреждение при инициализации БД: {e}")
                print("⚠️ Продолжаем запуск без БД...")
        else:
            print("⚠️ init_db недоступен, пропускаем инициализацию БД")
        
        # Запускаем фоновые задачи
        print("[3/7] 📋 Запуск фоновых задач...")
        try:
            import modules.events as events_module
            asyncio.create_task(events_module.weekly_reset())
            print("✅ Фоновые задачи запущены")
        except Exception as e:
            print(f"⚠️ Ошибка при запуске фоновых задач: {e}")
            import traceback
            traceback.print_exc()
        
        # Добавляем persistent view для регистрации
        print("[4/7] 📝 Добавление persistent views...")
        try:
            bot.add_view(RegistrationView())
            print("✅ Persistent views добавлены")
        except Exception as e:
            print(f"⚠️ Ошибка при добавлении views: {e}")
            import traceback
            traceback.print_exc()
        
        # Загружаем расширение check если оно есть
        print("[5/7] 🔌 Проверка расширений...")
        try:
            await bot.load_extension("check")
            print("✅ Расширение 'check' загружено")
        except Exception as e:
            print(f"⚠️ Расширение 'check' не найдено (это нормально): {e}")
        
        # Проверяем AI ключи
        print("[6/8] 🤖 Проверка AI настроек...")
        groq_key = os.getenv("GROQ_API_KEY")
        if groq_key:
            print(f"✅ GROQ_API_KEY найден (длина: {len(groq_key)} символов, начинается с: {groq_key[:4]}...)")
        else:
            print("⚠️ GROQ_API_KEY не установлен. AI чат будет недоступен.")
        ai_enabled = os.getenv("AI_ENABLED", "true").lower() == "true"
        ai_provider = os.getenv("AI_PROVIDER", "groq")
        print(f"   AI включен: {ai_enabled}, провайдер: {ai_provider}")
        
        # Запускаем бота
        print("[7/8] 🔑 Проверка токена...")
        token = os.getenv("TOKEN")
        if not token:
            print("=" * 50)
            print("❌ КРИТИЧЕСКАЯ ОШИБКА: Переменная окружения TOKEN не установлена!")
            print("❌ Установите переменную TOKEN на Koyeb в разделе Environment Variables")
            print("=" * 50)
            sys.exit(1)
        print(f"✅ Токен найден (длина: {len(token)} символов)")
        
        print("[8/8] 🔄 Попытка подключения к Discord...")
        print("=" * 50)
        try:
            await bot.start(token)
            print("✅ Бот успешно подключен!")
        except discord.errors.HTTPException as e:
            print("=" * 50)
            print("❌ HTTP ОШИБКА ПРИ ПОДКЛЮЧЕНИИ К DISCORD:")
            print(f"   Статус: {getattr(e, 'status', 'Unknown')}")
            print(f"   Код ошибки: {getattr(e, 'code', 'Unknown')}")
            print(f"   Сообщение: {str(e)[:500]}")
            import traceback
            traceback.print_exc()
            raise
        except Exception as e:
            print("=" * 50)
            print(f"❌ ОШИБКА ПРИ ПОДКЛЮЧЕНИИ: {type(e).__name__}")
            print(f"   Сообщение: {str(e)[:500]}")
            import traceback
            traceback.print_exc()
            raise
    except Exception as e:
        print("=" * 50)
        print(f"❌ КРИТИЧЕСКАЯ ОШИБКА В main(): {type(e).__name__}")
        print(f"   Сообщение: {str(e)}")
        import traceback
        traceback.print_exc()
        raise

if __name__ == "__main__":
    print("=" * 50)
    print("🎯 ТОЧКА ВХОДА БОТА")
    print("=" * 50)
    
    try:
        print("🔄 Запуск асинхронной функции main()...")
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n⚠️ Бот остановлен пользователем (Ctrl+C)")
    except SystemExit as e:
        print(f"\n⚠️ Бот завершил работу с кодом: {e}")
        sys.exit(e.code if hasattr(e, 'code') else 1)
    except Exception as e:
        print("=" * 50)
        print(f"❌ КРИТИЧЕСКАЯ ОШИБКА В ТОЧКЕ ВХОДА: {type(e).__name__}")
        print(f"   Сообщение: {str(e)}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
    finally:
        print("=" * 50)
        print("🧹 Очистка ресурсов...")
        # Убеждаемся, что бот закрыт
        try:
            loop = asyncio.get_event_loop()
            if not bot.is_closed():
                print("🔒 Закрытие соединения с Discord...")
                loop.run_until_complete(bot.close())
                print("✅ Соединение закрыто")
        except Exception as e:
            print(f"⚠️ Ошибка при закрытии: {e}")
        print("=" * 50)
