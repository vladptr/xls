"""
Модуль для интеграции языковой модели через внешние API
Поддерживает Groq API (бесплатный и быстрый)
"""
import os
import requests
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
    api_key = api_key or os.getenv("GROQ_API_KEY")
    
    if not api_key:
        print("⚠️ GROQ_API_KEY не установлен. Получите ключ на https://console.groq.com/")
        return None
    
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
        # Используем requests в отдельном потоке для асинхронности
        loop = asyncio.get_event_loop()
        response = await loop.run_in_executor(
            None,
            lambda: requests.post(GROQ_API_URL, json=data, headers=headers, timeout=30)
        )
        
        if response.status_code == 200:
            result = response.json()
            return result["choices"][0]["message"]["content"]
        else:
            print(f"❌ Ошибка Groq API: {response.status_code} - {response.text}")
            return None
            
    except Exception as e:
        print(f"❌ Ошибка при запросе к Groq API: {e}")
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

