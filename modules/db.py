import os
from supabase import create_client, Client

def get_connection() -> Client:
    """
    Подключение к Supabase. Использует переменные окружения:
    - keykey: Supabase API Key
    """
    url = "https://qyqicdyzaagumqjlczoj.supabase.co"
    key = os.getenv("keykey")

    if not url or not key:
        raise Exception("❌ Не найдены переменные окружения SUPABASE_URL или SUPABASE_KEY")

    print("🔐 URL:", url)
    print("🔐 KEY:", key[:10], "...")

    return create_client(url, key)

supabase = get_connection()
