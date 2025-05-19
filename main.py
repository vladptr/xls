import discord
from discord.ext import commands
from discord.ui import View, Button
import yt_dlp
import asyncio
from dotenv import load_dotenv
import os

from webserver import keep_alive

intents = discord.Intents.default()
intents.guilds = True
intents.members = True
intents.voice_states = True
intents.message_content = True

bot = commands.Bot(command_prefix="!", intents=intents)

# Переменные для музыки
music_queue = []
repeat_mode = False

YDL_OPTIONS = {'format': 'bestaudio'}
FFMPEG_OPTIONS = {'options': '-vn'}

# Переменные для голосовых каналов
TRIGGER_CHANNELS = {
    "🔴・Создать ранкед руму": {"base": "🟢・Ранкед рума", "category": "Ранкед🔴"}, # Первое это название канала который создаетрумки, второе это дэфолтное название румки, третье это категория в которой создаваться будут румки
    "🔴・Создать паблик руму": {"base": "🟢・Паблик рума", "category": "Паблик🔴"},
    "🔴・Создать кастомную комнату": {"base": "🟢・Кастом игра", "category": "Кастомки🔴"}
}

BUTTON_LABELS = ["CS:GO", "Dota", "Helldivers 2"] # тут крч кнопки для игр, типа можно добавить, можно удалить, можно изменить
LIMIT_BUTTONS = ["2", "4", "6", "99"] # кнопки лимитов

created_channels = {}
channel_bases = {}

limit_name_mapping = {
    "🟢・Ранкед рума": {
        "2": "🟢・Дуо ранкед рум",
        "4": "🟢・Сквад ранкед рум",
        "6": "🟢・Сквад+ ранкед рум",
        "99": "🟢・Обговорная ранкед рум" # при изменении лимита канала меняется на название, можно изменить на свое (главное циферки не трогать иначе похеришь)
    },
    "🟢・Паблик рума": {
        "2": "🟢・Дуо рум",
        "4": "🟢・Сквад рум",
        "6": "🟢・Сквад+ рум",
        "99": "🟢・Обговорная рум" # при изменении лимита канала меняется на название, можно изменить на свое (главное циферки не трогать иначе похеришь)
    }
}

# Муз функции, через команду "!" ну и пропись команды (по наитию play skip и тд.)
async def play_next(ctx):
    global music_queue, repeat_mode
    if music_queue:
        url = music_queue[0] if not repeat_mode else music_queue[-1]

        with yt_dlp.YoutubeDL(YDL_OPTIONS) as ydl:
            info = ydl.extract_info(url, download=False)
            audio_url = info['url']

        source = await discord.FFmpegOpusAudio.from_probe(audio_url, **FFMPEG_OPTIONS)
        ctx.voice_client.play(source, after=lambda e: asyncio.run_coroutine_threadsafe(play_next(ctx), bot.loop))

        if not repeat_mode:
            music_queue.pop(0)
    else:
        await asyncio.sleep(1)

@bot.event
async def on_ready():
    print(f"✅ Logged in as {bot.user}")

@bot.command()
async def ping(ctx):
    await ctx.send("пшл нх")
    
@bot.command()
async def join(ctx):
    if ctx.author.voice:
        channel = ctx.author.voice.channel
        if ctx.voice_client is None:
            await channel.connect()
            await ctx.send("Подключился к голосовому каналу.")
    else:
        await ctx.send("Ты должен быть в голосовом канале.")

@bot.command()
async def play(ctx, url):
    music_queue.append(url)
    await ctx.send(f"Добавлено: {url}")
    if not ctx.voice_client:
        await join(ctx)
    if not ctx.voice_client.is_playing():
        await play_next(ctx)

@bot.command()
async def repeat(ctx):
    global repeat_mode
    repeat_mode = not repeat_mode
    await ctx.send(f"Режим повтора {'включен' if repeat_mode else 'выключен'}")

@bot.command()
async def skip(ctx):
    if ctx.voice_client and ctx.voice_client.is_playing():
        ctx.voice_client.stop()
        await ctx.send("Пропущено.")

@bot.command()
async def queue(ctx):
    if music_queue:
        await ctx.send("Очередь:\n" + "\n".join(music_queue))
    else:
        await ctx.send("Очередь пуста.")

@bot.command()
async def playlist(ctx):
    if music_queue:
        await ctx.send("Плейлист:\n" + "\n".join(music_queue))
    else:
        await ctx.send("Плейлист пуст.")

@bot.command()
async def playlist_add(ctx, url):
    music_queue.append(url)
    await ctx.send(f"Трек добавлен в плейлист: {url}")

@bot.command()
async def playlist_delete(ctx, index: int):
    if 0 <= index < len(music_queue):
        removed_track = music_queue.pop(index)
        await ctx.send(f"Трек удален из плейлиста: {removed_track}")
    else:
        await ctx.send("Неверный индекс трека.")

@bot.command()
async def leave(ctx):
    if ctx.voice_client:
        await ctx.voice_client.disconnect()
        await ctx.send("Вышел из голосового канала.")
    else:
        await ctx.send("Я не подключен к голосовому каналу.")

# Кнопки с ограничениями и тд и тп
class GameSelectView(View):
    def __init__(self, user_id, channel_id):
        super().__init__(timeout=300)
        for label in BUTTON_LABELS:
            self.add_item(GameButton(label, user_id, channel_id))

class GameButton(Button):
    def __init__(self, label, user_id, channel_id):
        super().__init__(label=label, style=discord.ButtonStyle.primary)
        self.user_id = user_id
        self.channel_id = channel_id

    async def callback(self, interaction: discord.Interaction):
        if interaction.user.id != self.user_id:
            await interaction.response.send_message("Ты не создавал эту комнату!", ephemeral=True)
            return
        channel = interaction.guild.get_channel(self.channel_id)
        if channel:
            await channel.edit(name=self.label)
            await interaction.response.send_message(f"Название канала изменено на: **{self.label}**", ephemeral=True)
        else:
            await interaction.response.send_message("Канал не найден!", ephemeral=True)

class LimitButton(Button):
    def __init__(self, label, user_id, channel_id):
        super().__init__(label=label, style=discord.ButtonStyle.secondary)
        self.user_id = user_id
        self.channel_id = channel_id

    async def callback(self, interaction: discord.Interaction):
        if interaction.user.id != self.user_id:
            await interaction.response.send_message("Ты не создавал эту комнату!", ephemeral=True)
            return

        channel = interaction.guild.get_channel(self.channel_id)
        if not channel:
            await interaction.response.send_message("Канал не найден!", ephemeral=True)
            return

        limit = int(self.label)
        await channel.edit(user_limit=limit)

        base_name = channel_bases.get(channel.id)
        if base_name in limit_name_mapping:
            new_name = limit_name_mapping[base_name][self.label]
            await channel.edit(name=new_name)
            await interaction.response.send_message(
                f"Установлен лимит: **{limit}** участников\nНазвание канала изменено на: **{new_name}**",
                ephemeral=True
            )
        else:
            await interaction.response.send_message(f"Установлен лимит: **{limit}** участников", ephemeral=True)

class SearchButton(Button):
    def __init__(self, user_id, voice_channel_id):
        super().__init__(label="Поиск", style=discord.ButtonStyle.success)
        self.user_id = user_id
        self.voice_channel_id = voice_channel_id

    async def callback(self, interaction: discord.Interaction):
        if interaction.user.id != self.user_id:
            await interaction.response.send_message("Ты не создавал этот канал!", ephemeral=True)
            return

        guild = interaction.guild
        voice_channel = guild.get_channel(self.voice_channel_id)
        if not voice_channel:
            await interaction.response.send_message("Голосовой канал не найден!", ephemeral=True)
            return

        text_channel = discord.utils.get(guild.text_channels, name="🔍 ・поиск тимы")
        if not text_channel:
            await interaction.response.send_message("Текстовый канал 'поиск' не найден!", ephemeral=True)
            return

        member_count = len(voice_channel.members)
        user_limit = voice_channel.user_limit

        # Cообщение набора
        if user_limit in [6, 99]:
            msg = f"+очередь на замену тимейта <@&1159121098965786634> <#{voice_channel.id}>" # 1372898116877160519 id роли которую должно тегать в поиске тимы (айдишка 1159121098965786634 с сервера), можно заменить на любую другую роль
        else:
            missing = user_limit - member_count
            if missing > 0:
                msg = f"+{missing} <@&1159121098965786634> <#{voice_channel.id}>"
            else:
                msg = f"+общение <@&1159121098965786634> <#{voice_channel.id}>"

        await text_channel.send(msg)
        await interaction.response.send_message("Сообщение отправлено в канал 'поиск'.", ephemeral=True)


class LimitSelectViewWithSearch(View):
    def __init__(self, user_id, voice_channel_id):
        super().__init__(timeout=300)
        for label in LIMIT_BUTTONS:
            self.add_item(LimitButton(label, user_id, voice_channel_id))
        self.add_item(SearchButton(user_id, voice_channel_id))

@bot.event
async def on_ready():
    print(f"Бот запущен как {bot.user}") # проверка запуска бота (типа пишет если запущен, если не запустится будут ошибки, мб просто ему библ не хватает)

@bot.event
async def on_voice_state_update(member, before, after):
    guild = member.guild
    if before.channel and before.channel.id in created_channels:
        await asyncio.sleep(3)
        if len(before.channel.members) == 0:
            await before.channel.delete()
            created_channels.pop(before.channel.id, None)
            channel_bases.pop(before.channel.id, None)
            print(f"Удалён пустой канал: {before.channel.name}")

    if after.channel and after.channel.name in TRIGGER_CHANNELS:
        conf = TRIGGER_CHANNELS[after.channel.name]
        category = discord.utils.get(guild.categories, name=conf["category"])
        if not category:
            print(f"Категория {conf['category']} не найдена!")
            return

        existing = [ch for ch in guild.voice_channels if ch.name.startswith(conf["base"]) and ch.category == category]
        number = 1
        base_name = conf["base"]
        new_name = f"{base_name} #{number}"
        while any(ch.name == new_name for ch in existing):
            number += 1
            new_name = f"{base_name} #{number}"

        new_channel = await guild.create_voice_channel(new_name, category=category)
        await member.move_to(new_channel)

        created_channels[new_channel.id] = member.id
        channel_bases[new_channel.id] = base_name

        if conf["base"] == "Кастом игра":
            view = GameSelectView(member.id, new_channel.id)
            await new_channel.send(f"{member.mention}, выбери игру для **{new_channel.name}**:", view=view)
        elif conf["base"] in limit_name_mapping:
            view = LimitSelectViewWithSearch(member.id, new_channel.id)
            await new_channel.send(f"{member.mention}, выбери лимит участников для **{new_channel.name}**:", view=view)

token = os.getenv("TOKEN")

if not token:
    print("❌ TOKEN is missing!")
else:
    print("✅ Token loaded!")


async def main():
    keep_alive()

    await bot.start(token)

asyncio.run(main())
