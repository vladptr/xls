import os
from supabase import create_client

def get_connection():
    url = "https://qyqicdyzaagumqjlczoj.supabase.co"
    key = os.getenv("keykey")
    return create_client(url, key)

supabase = get_connection()
