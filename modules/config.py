import os
import subprocess
import discord
from discord.ext import commands

# PUBG API
PUBG_API_KEY = "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9.eyJqdGkiOiJjZmMyNDMyMC01NzZlLTAxM2UtMjAyNS0yYTI4ZjY0MjU0ZDEiLCJpc3MiOiJnYW1lbG9ja2VyIiwiaWF0IjoxNzU0NzU4MTk5LCJwdWIiOiJibHVlaG9sZSIsInRpdGxlIjoicHViZyIsImFwcCI6InhsczIifQ.C74qapztROZBtCVEWdob2w4B0-omdLJ-aaBfdfFK91E"
PUBG_PLATFORM = "steam"
print("PUBG API key:", repr(PUBG_API_KEY))

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
MAIN_GUILD_ID = int(os.getenv("MAIN_GUILD_ID", "1371926685435428924"))

# FFmpeg setup (только для Linux/Mac, на Windows пропускается)
try:
    subprocess.run(["chmod", "+x", "./ffmpeg"], check=False)
except:
    pass  # Игнорируем ошибку на Windows


