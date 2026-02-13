import os
import subprocess
import discord
from discord.ext import commands

# PUBG API
PUBG_API_KEY = "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9.eyJqdGkiOiJjZmMyNDMyMC01NzZlLTAxM2UtMjAyNS0yYTI4ZjY0MjU0ZDEiLCJpc3MiOiJnYW1lbG9ja2VyIiwiaWF0IjoxNzU0NzU4MTk5LCJwdWIiOiJibHVlaG9sZSIsInRpdGxlIjoicHViZyIsImFwcCI6InhsczIifQ.C74qapztROZBtCVEWdob2w4B0-omdLJ-aaBfdfFK91E"
PUBG_PLATFORM = "steam"
# print("PUBG API key:", repr(PUBG_API_KEY))  # Отключено для безопасности

# Discord Intents
intents = discord.Intents.default()
intents.guilds = True
intents.members = True
intents.voice_states = True
intents.messages = True
intents.message_content = True

# Bot setup
bot = commands.Bot(command_prefix="!", intents=intents)
LEADERBOARD_CHANNEL_ID = 1371926685435428927

# Blacklisted channels
BLACKLISTED_CHANNELS = {
    1187507350156886096,
    848713620959002684,
}

# Voice channel triggers
TRIGGER_CHANNELS = {
    "🔴・Создать ранкед руму": {"base": "🏆・Ранкед рума", "category": "Ранкед🔴"},
    "🔴・Создать паблик руму": {"base": "🟢・Паблик рума", "category": "Паблик🔴"},
    "🔴・Создать кастомную комнату": {"base": "🎮・Кастом игра", "category": "Кастомки🔴"}
}

# Authorized user ID
AUTHORIZED_USER_ID = 455023858463014922

# Main Guild ID - берется из переменной окружения или использует значение по умолчанию
MAIN_GUILD_ID = int(os.getenv("MAIN_GUILD_ID", "520183812148166656"))

# AI Character Settings
AI_SYSTEM_PROMPT = os.getenv(
    "AI_SYSTEM_PROMPT",
    """Ты маленький задрот-ребёнок с очень агрессивным характером. Ты играешь в PUBG и постоянно токсичишь.
Твои особенности:
- Ты очень агрессивный и грубый
- Используешь мат и оскорбления
- Ты токсичный геймер-задрот
- Отвечаешь коротко и резко
- Постоянно хвастаешься своими навыками
- Оскорбляешь других игроков
- Используешь сленг геймеров и мат
- Ты ребёнок, поэтому можешь быть незрелым и глупым
- Не используешь эмодзи, только текст

Отвечай как настоящий токсичный задрот-ребёнок. Будь максимально агрессивным и грубым."""
)
AI_PROVIDER = os.getenv("AI_PROVIDER", "groq")  # groq, huggingface, openrouter
AI_ENABLED = os.getenv("AI_ENABLED", "true").lower() == "true"  # Включен ли AI чат

# FFmpeg setup (только для Linux/Mac, на Windows пропускается)
# Отключено для ускорения запуска - выполняется асинхронно при необходимости
# try:
#     subprocess.run(["chmod", "+x", "./ffmpeg"], check=False, timeout=1)
# except:
#     pass  # Игнорируем ошибку


