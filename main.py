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
    
    # Запускаем бота с обработкой rate limit
    token = os.getenv("TOKEN")
    if not token:
        raise ValueError("❌ Переменная окружения TOKEN не установлена!")
    
    # Попытки подключения с задержкой при rate limit
    max_retries = 10
    base_delay = 120  # Базовая задержка 2 минуты
    
    for attempt in range(max_retries):
        try:
            print(f"🔄 Попытка подключения {attempt + 1}/{max_retries}...")
            await bot.start(token)
            print("✅ Бот успешно подключен!")
            break
        except discord.errors.HTTPException as e:
            error_str = str(e)
            status_code = getattr(e, 'status', None)
            
            # Закрываем сессию при ошибке
            try:
                if not bot.is_closed():
                    await bot.close()
            except:
                pass
            
            # Проверяем на rate limit (429 или текст ошибки)
            if status_code == 429 or "429" in error_str or "rate limit" in error_str.lower() or "Too Many Requests" in error_str or "being blocked" in error_str.lower():
                if attempt < max_retries - 1:
                    # Экспоненциальная задержка: 2, 4, 8, 16, 32 минуты и т.д. (максимум 30 минут)
                    wait_time = min(base_delay * (2 ** attempt), 1800)  # Максимум 30 минут
                    print(f"⚠️ Rate limit обнаружен (статус: {status_code}). Ожидание {wait_time // 60} минут {wait_time % 60} секунд перед повторной попыткой ({attempt + 1}/{max_retries})...")
                    print(f"📝 Подробности ошибки: {error_str[:200]}")
                    await asyncio.sleep(wait_time)
                else:
                    print(f"❌ Не удалось подключиться после {max_retries} попыток. Rate limit слишком строгий.")
                    print(f"💡 Рекомендация: Подождите 30-60 минут и перезапустите бота вручную.")
                    raise
            else:
                # Другая HTTP ошибка - пробрасываем дальше
                print(f"❌ HTTP ошибка при подключении: {e}")
                raise
        except Exception as e:
            error_str = str(e)
            
            # Закрываем сессию при ошибке
            try:
                if not bot.is_closed():
                    await bot.close()
            except:
                pass
            
            # Проверяем на rate limit в тексте ошибки
            if "429" in error_str or "rate limit" in error_str.lower() or "Too Many Requests" in error_str or "being blocked" in error_str.lower():
                if attempt < max_retries - 1:
                    wait_time = min(base_delay * (2 ** attempt), 1800)
                    print(f"⚠️ Rate limit обнаружен в тексте ошибки. Ожидание {wait_time // 60} минут перед повторной попыткой ({attempt + 1}/{max_retries})...")
                    await asyncio.sleep(wait_time)
                else:
                    print(f"❌ Не удалось подключиться после {max_retries} попыток.")
                    raise
            else:
                # Другая ошибка - пробрасываем дальше
                print(f"❌ Неожиданная ошибка при подключении: {e}")
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

