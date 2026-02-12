import os
import asyncio
import discord
from modules.config import bot
from modules.database import init_db
from modules import commands
from modules import events
from modules.registration import RegistrationView

# Попытка импортировать webserver (если есть)
try:
    from webserver import keep_alive
    HAS_WEBSERVER = True
except ImportError:
    HAS_WEBSERVER = False
    print("⚠️ webserver.py не найден, пропускаем keep_alive")

async def main():
    # Запускаем webserver если доступен (для некоторых хостингов)
    if HAS_WEBSERVER:
        keep_alive()
    
    # Инициализируем базу данных
    init_db()
    
    # Запускаем фоновые задачи
    asyncio.create_task(events.weekly_reset())
    
    # Добавляем persistent view для регистрации
    bot.add_view(RegistrationView())
    
    # Загружаем расширение check если оно есть
    try:
        await bot.load_extension("check")
    except Exception as e:
        print(f"⚠️ Не удалось загрузить расширение 'check': {e}")
    
    # Запускаем бота
    token = os.getenv("TOKEN")
    if not token:
        raise ValueError("❌ Переменная окружения TOKEN не установлена!")
    
    print(f"🔄 Попытка подключения к Discord...")
    try:
        await bot.start(token)
        print("✅ Бот успешно подключен!")
    except discord.errors.HTTPException as e:
        print(f"❌ HTTP ошибка при подключении:")
        print(f"   Статус: {getattr(e, 'status', 'Unknown')}")
        print(f"   Код ошибки: {getattr(e, 'code', 'Unknown')}")
        print(f"   Сообщение: {str(e)[:500]}")
        raise
    except Exception as e:
        print(f"❌ Ошибка при подключении: {type(e).__name__}")
        print(f"   Сообщение: {str(e)[:500]}")
        raise

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n⚠️ Бот остановлен пользователем")
    except Exception as e:
        print(f"❌ Критическая ошибка: {e}")
        import traceback
        traceback.print_exc()
    finally:
        # Убеждаемся, что бот закрыт
        try:
            loop = asyncio.get_event_loop()
            if not bot.is_closed():
                loop.run_until_complete(bot.close())
        except:
            pass

