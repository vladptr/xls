import os
import asyncio
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
    
    await bot.start(token)

if __name__ == "__main__":
    asyncio.run(main())

