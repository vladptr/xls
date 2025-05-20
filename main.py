
import discord 
from discord.ext import commands
from discord.ui import View, Select
import discord
import random
import yt_dlp
import asyncio
from dotenv import load_dotenv
import os
import nacl

#from webserver import keep_alive

setup_messages = {}
channel_locks = {}


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
    "🔴・Создать ранкед руму": {"base": "🏆・Ранкед рума", "category": "Ранкед🔴"},
    "🔴・Создать паблик руму": {"base": "🟢・Паблик рума", "category": "Паблик🔴"},
    "🔴・Создать кастомную комнату": {"base": "🎮・Кастом игра", "category": "Кастомки🔴"}
}

created_channels = {}
channel_bases = {}

# Муз функции
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
async def gonki(ctx):
    await ctx.send("поехали! я беру гоночную каляску ♿")

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

# Выпадающие списки для выбора типа комнаты и количества участников
class RoomTypeSelect(Select):
    def __init__(self, user_id, channel_id, mode="default"):
        # mode: "default" для ранкед/паблик, "custom" для кастомок
        if mode == "custom":
            options = [
                discord.SelectOption(label="Valorant", value="🎮・Valorant"),
                discord.SelectOption(label="Among Us", value="🎮・Among Us"),
                discord.SelectOption(label="CS:GO", value="🎮・CS:GO"),
                discord.SelectOption(label="Pummel party", value="🎮・Pummel party"),
                discord.SelectOption(label="PICO PACK", value="🎮・PICO PACK"),
                discord.SelectOption(label="Dota 2", value="♿・Dota 2"),
                discord.SelectOption(label="Apex Legends", value="🎮・Apex Legends"),
                discord.SelectOption(label="WARZONE", value="🎮・WARZONE"),
                discord.SelectOption(label="Rocket League", value="🎮・Rocket League"),
                discord.SelectOption(label="Helldivers 2", value="🎮・Helldivers 2"),
            ]
        else:
            options = [
                discord.SelectOption(label="Дуо", value="👥・Дуо"),
                discord.SelectOption(label="Сквад", value="👥・Сквад"),
                discord.SelectOption(label="Без ограничений", value="👥・Сквад+")
            ]
        super().__init__(placeholder="Выберите тип комнаты", min_values=1, max_values=1, options=options)
        self.user_id = user_id
        self.channel_id = channel_id
        self.mode = mode

    async def callback(self, interaction: discord.Interaction):
        if interaction.user.id != self.user_id:
            await interaction.response.send_message("Ты не создавал эту комнату!", ephemeral=True)
            return
        channel = interaction.guild.get_channel(self.channel_id)
        if channel:
            await channel.edit(name=self.values[0])
            await interaction.response.send_message(f"Название канала изменено на: **{self.values[0]}**", ephemeral=True)
        else:
            await interaction.response.send_message("Канал не найден!", ephemeral=True)

class PlayerCountSelect(Select):
    def __init__(self, user_id, channel_id, mode="default"):
        if mode == "custom":
            options = [
                discord.SelectOption(label=f"+{i}", value=str(i)) for i in range(1, 11)
            ] + [discord.SelectOption(label="не искать", value="none")]
        else:
            options = [
                discord.SelectOption(label="1️⃣", value="1"),
                discord.SelectOption(label="2️⃣", value="2"),
                discord.SelectOption(label="3️⃣", value="3"),
                discord.SelectOption(label="не искать", value="none")
            ]
        super().__init__(placeholder="Сколько игроков нужно?", min_values=1, max_values=1, options=options)
        self.user_id = user_id
        self.channel_id = channel_id
        self.mode = mode

    async def callback(self, interaction: discord.Interaction):
        if interaction.user.id != self.user_id:
            await interaction.response.send_message("Ты не создавал эту комнату!", ephemeral=True)
            return

        selection = self.values[0]
        if selection == "none":
            await interaction.response.send_message("Выбран вариант 'Не искать', сообщение не отправлено.", ephemeral=True)
            return
            
        guild = interaction.guild
        voice_channel = guild.get_channel(self.channel_id)
        if not voice_channel:
            await interaction.response.send_message("Голосовой канал не найден!", ephemeral=True)
            return

        text_channel = discord.utils.get(guild.text_channels, name="🔍・поиск-тимы")
        if not text_channel:
            await interaction.response.send_message("Текстовый канал 'поиск' не найден!", ephemeral=True)
            return

        count = self.values[0]
        msg = f"+{count} <@&1159121098965786634> <#{voice_channel.id}>"
        sent_msg = await text_channel.send(msg)
        await interaction.response.send_message("Сообщение отправлено в канал 'поиск'.", ephemeral=True)

        # Удаление сообщения через 30 минут
        await asyncio.sleep(1800)
        await sent_msg.delete()


class RoomSetupView(View):
    def __init__(self, user_id, channel_id, mode="default"):
        super().__init__(timeout=300)
        self.add_item(RoomTypeSelect(user_id, channel_id, mode))
        self.add_item(PlayerCountSelect(user_id, channel_id, mode))

async def get_channel_lock(channel_id):
    if channel_id not in channel_locks:
        channel_locks[channel_id] = asyncio.Lock()
    return channel_locks[channel_id]

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
        
    


    #////////////////////////
    if before.channel and before.channel.id in created_channels:
        lock = await get_channel_lock(before.channel.id)
        async with lock:
          owner_id = created_channels[before.channel.id]
        # Если вышел текущий владелец комнаты
          if member.id == owner_id:
            members = before.channel.members
            if len(members) > 0:
                # Выбираем нового владельца случайно
                new_owner = random.choice(members)
                # Переназначаем владельца в словаре
                created_channels[before.channel.id] = new_owner.id

                # Удаляем старое сообщение с настройками (если есть)
                old_msg = setup_messages.get(before.channel.id)
                if old_msg:
                    try:
                        await old_msg.delete()
                    except:
                        pass  # если уже удалено или нет прав, игнорируем

                # Назначаем права новому владельцу (примерно, дай права на управление каналом)
                overwrite = before.channel.overwrites_for(new_owner)
                overwrite.manage_channels = True
                overwrite.move_members = True
                overwrite.connect = True
                await before.channel.set_permissions(new_owner, overwrite=overwrite)

                # Определяем mode для селектов, можно взять из channel_bases
                base_name = channel_bases.get(before.channel.id, "")
                if base_name == "тест кастомки":
                    mode = "custom"
                else:
                    mode = "default"

                # Отправляем новое сообщение с настройками и сохраняем его
                view = RoomSetupView(new_owner.id, before.channel.id, mode)
                new_msg = await before.channel.send(
                    f"Владелец комнаты вышел. Новый владелец: {new_owner.mention}\n"
                    f"{new_owner.mention}, настройте комнату:",
                    view=view
                )
                setup_messages[before.channel.id] = new_msg

               

            else:
                # Если никого нет — удалить канал и очистить словари
                await before.channel.delete()
                created_channels.pop(before.channel.id, None)
                channel_bases.pop(before.channel.id, None)
                setup_messages.pop(before.channel.id, None)
                print(f"Удалён пустой канал (после ухода владельца): {before.channel.name}")

    #//////////////////////////////////////////////////////

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

    # Определяем mode для селектов
    if conf["category"] == "тест кастомки":
        mode = "custom"
    else:
        mode = "default"
    

    view = RoomSetupView(member.id, new_channel.id, mode)
    msg = await new_channel.send(f"{member.mention}, настройте комнату:", view=view)

token = os.getenv("TOKEN")

if not token:
    print("❌ TOKEN is missing!")
else:
    print("✅ Token loaded!")


async def main():
    keep_alive()
    await bot.start(token)

asyncio.run(main())
#await bot.start("")
