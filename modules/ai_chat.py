"""
Модуль для интеграции языковой модели через внешние API
Поддерживает Groq API (бесплатный и быстрый)
"""
import os
import requests
from requests.exceptions import Timeout, RequestException
import asyncio
from typing import Optional

# Конфигурация API
GROQ_API_URL = "https://api.groq.com/openai/v1/chat/completions"
HUGGINGFACE_API_URL = "https://api-inference.huggingface.co/models"

# Доступные модели
GROQ_MODELS = {
    "llama": "llama-3.1-70b-versatile",
    "mixtral": "mixtral-8x7b-32768",
    "gemma": "gemma-7b-it"
}

HUGGINGFACE_MODELS = {
    "llama": "meta-llama/Llama-2-7b-chat-hf",
    "mistral": "mistralai/Mistral-7B-Instruct-v0.2"
}


async def chat_with_groq(
    message: str,
    system_prompt: str = "Ты полезный помощник Discord бота. Отвечай кратко и по делу.",
    model: str = "llama",
    api_key: Optional[str] = None
) -> Optional[str]:
    """
    Отправляет сообщение в Groq API и получает ответ
    
    Args:
        message: Сообщение пользователя
        system_prompt: Системный промпт для модели
        model: Название модели (llama, mixtral, gemma)
        api_key: API ключ Groq (если не указан, берется из переменной окружения)
    
    Returns:
        Ответ модели или None в случае ошибки
    """
    # Проверяем все возможные варианты названия переменной
    # Значение по умолчанию (если переменная окружения не установлена)
    default_key = "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"
    api_key = api_key or os.getenv("GROQ_API_KEY") or os.getenv("groq_api_key") or os.getenv("Groq_Api_Key") or default_key
    
    if not api_key:
        print("⚠️ GROQ_API_KEY не установлен. Получите ключ на https://console.groq.com/")
        print(f"🔍 Проверка переменных окружения: GROQ_API_KEY = {os.getenv('GROQ_API_KEY', 'НЕ НАЙДЕН')}")
        # Дополнительная диагностика
        all_groq_vars = {k: v for k, v in os.environ.items() if 'GROQ' in k.upper()}
        if all_groq_vars:
            print(f"🔍 Найдены переменные с 'GROQ': {list(all_groq_vars.keys())}")
        return None
    
    # Проверяем формат ключа
    if not api_key.startswith("gsk_"):
        print(f"⚠️ Предупреждение: GROQ_API_KEY не начинается с 'gsk_'. Проверьте правильность ключа.")
    
    model_name = GROQ_MODELS.get(model, GROQ_MODELS["llama"])
    
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json"
    }
    
    data = {
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": message}
        ],
        "model": model_name,
        "temperature": 0.7,
        "max_tokens": 500
    }
    
    try:
        print(f"🔍 Отправка запроса в Groq API...")
        print(f"   Модель: {model_name}")
        print(f"   Длина сообщения: {len(message)} символов")
        print(f"   Ключ API: {api_key[:10]}...{api_key[-5:] if len(api_key) > 15 else '***'}")
        
        # Используем requests в отдельном потоке для асинхронности
        loop = asyncio.get_event_loop()
        response = await loop.run_in_executor(
            None,
            lambda: requests.post(GROQ_API_URL, json=data, headers=headers, timeout=30)
        )
        
        print(f"📡 Ответ от Groq API: статус {response.status_code}")
        
        if response.status_code == 200:
            result = response.json()
            if "choices" in result and len(result["choices"]) > 0:
                answer = result["choices"][0]["message"]["content"]
                print(f"✅ Получен ответ от AI (длина: {len(answer)} символов)")
                return answer
            else:
                print(f"❌ Неожиданный формат ответа от Groq API: {result}")
                return None
        elif response.status_code == 401:
            print(f"❌ Ошибка авторизации Groq API (401): Неверный API ключ")
            print(f"   Проверьте правильность GROQ_API_KEY на Koyeb")
            return None
        elif response.status_code == 429:
            print(f"❌ Rate limit Groq API (429): Превышен лимит запросов")
            print(f"   Подождите минуту и попробуйте снова")
            return None
        else:
            print(f"❌ Ошибка Groq API: {response.status_code}")
            print(f"   Ответ: {response.text[:500]}")
            return None
            
    except Timeout:
        print(f"❌ Таймаут при запросе к Groq API (30 секунд)")
        return None
    except RequestException as e:
        print(f"❌ Ошибка сети при запросе к Groq API: {e}")
        return None
    except Exception as e:
        print(f"❌ Неожиданная ошибка при запросе к Groq API: {type(e).__name__}")
        print(f"   Сообщение: {str(e)}")
        import traceback
        traceback.print_exc()
        return None


async def chat_with_huggingface(
    message: str,
    model: str = "mistral",
    api_key: Optional[str] = None
) -> Optional[str]:
    """
    Отправляет сообщение в Hugging Face Inference API
    
    Args:
        message: Сообщение пользователя
        model: Название модели (llama, mistral)
        api_key: API ключ Hugging Face (опционально, для бесплатного tier не обязателен)
    
    Returns:
        Ответ модели или None в случае ошибки
    """
    model_name = HUGGINGFACE_MODELS.get(model, HUGGINGFACE_MODELS["mistral"])
    url = f"{HUGGINGFACE_API_URL}/{model_name}"
    
    headers = {
        "Content-Type": "application/json"
    }
    
    if api_key:
        headers["Authorization"] = f"Bearer {api_key}"
    
    data = {
        "inputs": message,
        "parameters": {
            "max_new_tokens": 200,
            "temperature": 0.7
        }
    }
    
    try:
        loop = asyncio.get_event_loop()
        response = await loop.run_in_executor(
            None,
            lambda: requests.post(url, json=data, headers=headers, timeout=60)
        )
        
        if response.status_code == 200:
            result = response.json()
            # Hugging Face возвращает ответ в разных форматах в зависимости от модели
            if isinstance(result, list) and len(result) > 0:
                if "generated_text" in result[0]:
                    return result[0]["generated_text"]
                elif isinstance(result[0], dict) and "generated_text" in result[0]:
                    return result[0]["generated_text"]
            return str(result)
        elif response.status_code == 503:
            # Модель загружается, нужно подождать
            print("⏳ Модель Hugging Face загружается, попробуйте через несколько секунд")
            return None
        else:
            print(f"❌ Ошибка Hugging Face API: {response.status_code} - {response.text}")
            return None
            
    except Exception as e:
        print(f"❌ Ошибка при запросе к Hugging Face API: {e}")
        return None


async def chat_with_openrouter(
    message: str,
    system_prompt: str = "Ты полезный помощник Discord бота.",
    model: str = "openai/gpt-3.5-turbo",
    api_key: Optional[str] = None
) -> Optional[str]:
    """
    Отправляет сообщение в OpenRouter API (агрегатор моделей)
    
    Args:
        message: Сообщение пользователя
        system_prompt: Системный промпт
        model: Название модели (можно использовать разные провайдеры)
        api_key: API ключ OpenRouter
    
    Returns:
        Ответ модели или None в случае ошибки
    """
    api_key = api_key or os.getenv("OPENROUTER_API_KEY")
    
    if not api_key:
        print("⚠️ OPENROUTER_API_KEY не установлен. Получите ключ на https://openrouter.ai/")
        return None
    
    url = "https://openrouter.ai/api/v1/chat/completions"
    
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
        "HTTP-Referer": "https://github.com/your-repo",  # Опционально
        "X-Title": "Discord Bot"  # Опционально
    }
    
    data = {
        "model": model,
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": message}
        ],
        "max_tokens": 500
    }
    
    try:
        loop = asyncio.get_event_loop()
        response = await loop.run_in_executor(
            None,
            lambda: requests.post(url, json=data, headers=headers, timeout=30)
        )
        
        if response.status_code == 200:
            result = response.json()
            return result["choices"][0]["message"]["content"]
        else:
            print(f"❌ Ошибка OpenRouter API: {response.status_code} - {response.text}")
            return None
            
    except Exception as e:
        print(f"❌ Ошибка при запросе к OpenRouter API: {e}")
        return None


# Универсальная функция для чата (использует Groq по умолчанию)
async def chat(
    message: str,
    provider: str = "groq",
    system_prompt: str = "Ты полезный помощник Discord бота. Отвечай кратко и по делу.",
    **kwargs
) -> Optional[str]:
    """
    Универсальная функция для чата с разными провайдерами
    
    Args:
        message: Сообщение пользователя
        provider: Провайдер (groq, huggingface, openrouter)
        system_prompt: Системный промпт
        **kwargs: Дополнительные параметры для конкретного провайдера
    
    Returns:
        Ответ модели или None
    """
    provider = provider.lower()
    
    if provider == "groq":
        return await chat_with_groq(message, system_prompt, **kwargs)
    elif provider == "huggingface":
        return await chat_with_huggingface(message, **kwargs)
    elif provider == "openrouter":
        return await chat_with_openrouter(message, system_prompt, **kwargs)
    else:
        print(f"❌ Неизвестный провайдер: {provider}")
        return None

