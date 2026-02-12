import os
from supabase import create_client, Client

supabase: Client = None

def get_connection() -> Client:
    global supabase
    if supabase:
        return supabase

    url = os.getenv("SUPABASE_URL", "https://qyqicdyzaagumqjlczoj.supabase.co")
    key = os.getenv("SUPABASE_KEY", os.getenv("keykey"))

    if not url or not key:
        raise Exception("❌ Не найдены переменные окружения SUPABASE_URL или SUPABASE_KEY")
    
    print("🔐 URL:", url)
    print("🔐 KEY:", key[:10], "...")

    supabase = create_client(url, key)
    return supabase
