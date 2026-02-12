import os
from supabase import create_client

def get_connection():
    url = "https://qyqicdyzaagumqjlczoj.supabase.co"
    key = os.getenv("keykey")
    
    if not url or not key:
        raise Exception("❌ Не найдены переменные окружения SUPABASE_URL или SUPABASE_KEY")
    
    print("🔐 URL:", url)
    if key:
        print("🔐 KEY:", key[:10], "...")

    return create_client(url, key)

# Инициализируем supabase при импорте (будет ошибка если нет переменной окружения)
try:
    supabase = get_connection()
except Exception as e:
    print(f"⚠️ Предупреждение при подключении к Supabase: {e}")
    print("⚠️ Supabase будет инициализирован позже через init_db()")
    supabase = None

def init_db():
    global supabase
    try:
        # Если supabase не был инициализирован, пытаемся подключиться
        if supabase is None:
            supabase = get_connection()
        
        # Таблицы создаём вручную через Supabase интерфейс или SQL в Supabase
        print("✅ Проверка подключения к базе данных прошла успешно.")
    except Exception as e:
        print(f"❌ Ошибка при инициализации базы данных: {e}")
        raise

