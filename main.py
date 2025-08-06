import discord
from discord.ext import commands
from discord.ui import View, Select
from discord.ui import View, Button
import random
import time
import yt_dlp
import asyncio
from dotenv import load_dotenv
import os
import uuid
import json
import subprocess
import io
import nacl
import math
import matplotlib.pyplot as plt
import matplotlib.image as mpimg
from matplotlib import rcParams
import asyncpg
from datetime import datetime, timedelta
from supabase import create_client, Client
from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload
from webserver import keep_alive
from datetime import datetime, UTC
from PIL import Image, ImageDraw, ImageFont

setup_messages = {}
channel_locks = {}
room_modes = {}
last_rename_times = {}

users = {}
weeks = []
subprocess.run(["chmod", "+x", "./ffmpeg"])
intents = discord.Intents.default()
intents.guilds = True
intents.members = True
intents.voice_states = True
intents.messages = True
intents.message_content = True

service_account_info = json.loads(os.environ["GOOGLE_CREDS_JSON"])

credentials = service_account.Credentials.from_service_account_info(
    service_account_info,
    scopes=[
        "https://www.googleapis.com/auth/drive",  # или другие нужные тебе
    ]
)
drive_service = build('drive', 'v3', credentials=credentials)

BLACKLISTED_CHANNELS = {
    1187507350156886096,
    848713620959002684,
}



bot = commands.Bot(command_prefix="!", intents=intents)
LEADERBOARD_CHANNEL_ID = 1371926685435428927

def get_connection():
    url = "https://qyqicdyzaagumqjlczoj.supabase.co"
    key = os.getenv("keykey")
    
    if not url or not key:
        raise Exception("❌ Не найдены переменные окружения SUPABASE_URL или SUPABASE_KEY")
    
    print("🔐 URL:", os.getenv("https://qyqicdyzaagumqjlczoj.supabase.co"))
    print("🔐 KEY:", os.getenv("keykey")[:10], "...")

    return create_client(url, key)

supabase = get_connection()
# Переменные для музыки
music_queue = []
repeat_mode = True

YDL_OPTIONS = {
    'format': 'bestaudio/best',
    'noplaylist': True,
    'quiet': True,
    'extract_flat': False,
    'ffmpeg_location': './ffmpeg'
}





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
async def play_next(vc):
    global music_queue, repeat_mode

    if not vc.is_connected():
        print("❌ VoiceClient не подключен, выходим из play_next")
        return

    if music_queue:
        url = music_queue[0] if not repeat_mode else music_queue[-1]
        print(f"▶️ Воспроизведение: {url}")

        try:
            with yt_dlp.YoutubeDL(YDL_OPTIONS) as ydl:
                info = ydl.extract_info(url, download=False)
                audio_url = info['url']

            print(f"🔗 Скачанная ссылка на аудио: {audio_url}")

            source = discord.FFmpegPCMAudio(
                audio_url,
                executable="./ffmpeg",
                before_options="-reconnect 1 -reconnect_streamed 1 -reconnect_delay_max 5",
                options="-vn -loglevel quiet"
            )

            def after_playing(error):
                if error:
                    print(f"❌ Ошибка в after_playing: {error}")
                else:
                    print("✅ Трек завершился корректно.")

                fut = asyncio.run_coroutine_threadsafe(play_next(vc), bot.loop)
                try:
                    fut.result()
                except Exception as e:
                    print(f"❗ Ошибка в play_next after: {e}")

            vc.play(source, after=after_playing)
            print("▶️ Воспроизведение началось")

            if not repeat_mode:
                music_queue.pop(0)

        except Exception as e:
            print(f"❗ Ошибка загрузки или воспроизведения: {e}")
    else:
        print("🚪 Очередь пуста, отключаюсь")
        await vc.disconnect()


@bot.command()
async def testplay(ctx):
    if ctx.author.voice:
        channel = ctx.author.voice.channel
        vc = await channel.connect()

        source = discord.FFmpegPCMAudio(
            "Tokio_Machi.mp3",  # любой локальный mp3 файл
            executable="./ffmpeg",
            options="-vn -loglevel quiet"
        )

        vc.play(source)
        await ctx.send("🔊 Воспроизвожу test.mp3")
    else:
        await ctx.send("Ты не в голосовом канале.")


@bot.event
async def on_member_join(member):
    channel_id = 1183130293545222205  # замените на ID вашего канала
    channel = bot.get_channel(channel_id)
    if channel:
        await channel.send(f"Привет, {member.mention}! Добро пожаловать на сервер! 🎉 Прочти правила сервера и замени свой ник как показано в примере: ```Ник в игре (Имя)```")
    else:
        print("Канал для приветствия не найден.")

@bot.command(name="clearmsg")
@commands.has_permissions(manage_messages=False)
async def clear_bot_messages(ctx):
    """Удаляет все сообщения от бота в текущем канале."""
    deleted = 0
    async for message in ctx.channel.history(limit=1000):  # Увеличь лимит при необходимости
        if message.author == bot.user:
            try:
                await message.delete()
                deleted += 1
            except discord.Forbidden:
                await ctx.send("❌ У меня нет прав на удаление сообщений.")
                return
            except discord.HTTPException:
                continue  # Иногда Discord не позволяет удалить старые сообщения

    await ctx.send(f"🧹 Удалено {deleted} сообщений от бота.", delete_after=5)


        
@bot.command()
async def gonki(ctx):
    await ctx.send("поехали! я беру гоночную каляску ♿")
    

        
@bot.command()
async def cleargraph(ctx):
    try:
        response = supabase.table("weekly_voice_stats").delete().neq("cycle_number", -1).execute()
        response = supabase.table("voice_time").delete().gt("user_id", 0).execute()
        if response.data is None:
            await ctx.send("Не удалось очистить данные (пустой ответ).")
            return

        await ctx.send("Все данные графика успешно удалены!")
    except Exception as e:
        await ctx.send(f"Произошла ошибка при очистке данных: {e}")

class LeaderboardView(View):
    def __init__(self, data, ctx):
        super().__init__(timeout=60)
        self.data = data
        self.ctx = ctx
        self.page = 0
        self.items_per_page = 10
        self.max_page = math.ceil(len(data) / self.items_per_page) - 1

        self.prev_button = Button(label="⬅️ Назад", style=discord.ButtonStyle.primary)
        self.next_button = Button(label="➡️ Вперед", style=discord.ButtonStyle.primary)
        self.prev_button.callback = self.prev_page
        self.next_button.callback = self.next_page
        self.add_item(self.prev_button)
        self.add_item(self.next_button)

    async def prev_page(self, interaction):
        if interaction.user != self.ctx.author:
            await interaction.response.send_message("Это меню не для тебя!", ephemeral=True)
            return
        if self.page > 0:
            self.page -= 1
            await self.update_message(interaction)

    async def next_page(self, interaction):
        if interaction.user != self.ctx.author:
            await interaction.response.send_message("Это меню не для тебя!", ephemeral=True)
            return
        if self.page < self.max_page:
            self.page += 1
            await self.update_message(interaction)

    async def update_message(self, interaction):
        embed = await self.generate_embed()
        await interaction.response.edit_message(embed=embed, view=self)

    async def generate_embed(self):
        start = self.page * self.items_per_page
        end = start + self.items_per_page
        page_data = self.data[start:end]

        embed = discord.Embed(
            title=f"🏆 Топ по времени в голосовых (Страница {self.page + 1}/{self.max_page + 1})",
            color=discord.Color.gold()
        )

        for i, row in enumerate(page_data, start=start + 1):
            user_id = row['user_id']
            total_seconds = row['total_seconds']
            member = self.ctx.guild.get_member(user_id)
            if member is None:
                try:
                    member = await self.ctx.guild.fetch_member(user_id)
                except discord.NotFound:
                    member = None

            name = member.display_name if member else f"User {user_id}"
            hours, remainder = divmod(total_seconds, 3600)
            minutes, seconds = divmod(remainder, 60)
            embed.add_field(name=f"{i}. {name}", value=f"{hours}ч {minutes}м {seconds}с", inline=False)

        return embed

@commands.cooldown(1, 60, commands.BucketType.user)
@bot.command()
async def leaderboard(ctx):
    try:
        response = supabase.table("voice_time")\
            .select("user_id,total_seconds")\
            .order("total_seconds", desc=True)\
            .limit(50)\
            .execute()
        data = response.data

        if not data:
            await ctx.send("Нет данных по времени в голосовых!")
            return

        view = LeaderboardView(data, ctx)
        embed = await view.generate_embed()
        message = await ctx.send(embed=embed, view=view)
        
       
        await asyncio.sleep(300)
        await message.delete()
        try:
            await ctx.message.delete()
        except discord.errors.Forbidden:
            pass

    except Exception as e:
        print(f"Ошибка при получении таблицы лидеров: {e}")
        await ctx.send("Произошла ошибка при получении таблицы лидеров.")
#//////////////////////////////////////
@bot.command()
async def join(ctx):
    if ctx.author.voice:
        channel = ctx.author.voice.channel
        print(f"🟢 Подключение к голосовому каналу: {channel.name}")
        if ctx.voice_client is None:
            await channel.connect()
            await ctx.send("Подключился к голосовому каналу.")
        else:
            print("⚠️ Уже подключён")
    else:
        await ctx.send("Ты должен быть в голосовом канале.")
        print("❌ Пользователь не в голосовом")


@bot.command()
async def play(ctx, url):
    music_queue.append(url)
    await ctx.send(f"🎵 Добавлено: {url}")

    if not ctx.voice_client or not ctx.voice_client.is_connected():
        await join(ctx)
        await asyncio.sleep(1)

    vc = ctx.voice_client

    if vc and not vc.is_playing():
        await play_next(vc)




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

        now = time.time()
        last_time = last_rename_times.get(self.channel_id, 0)
        cooldown = 660  # секунды

        if now - last_time < cooldown:
            remaining = round(cooldown - (now - last_time), 1)
            await interaction.response.send_message(
                f"Переименовывать можно раз в {cooldown} сек. Подождите ещё {remaining} сек. Не заёбывай бота иначе будешь послан нахуй!", ephemeral=True
            )
            return

        # Обновляем время последнего переименования
        last_rename_times[self.channel_id] = now

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
        msg = f"+{count} <@&1159121098965786634> <#{voice_channel.id}> {interaction.user.mention}"
        sent_msg = await text_channel.send(msg)
        await interaction.response.send_message("Сообщение отправлено в канал 'поиск'.", ephemeral=True)

        # Удаление сообщения через 3 часа
        await asyncio.sleep(10800)
        await sent_msg.delete()


class RoomSetupView(View):
    def __init__(self, user_id, channel_id, mode="default"):
        super().__init__(timeout=300000)
        self.add_item(RoomTypeSelect(user_id, channel_id, mode))
        self.add_item(PlayerCountSelect(user_id, channel_id, mode))

async def get_channel_lock(channel_id):
    if channel_id not in channel_locks:
        channel_locks[channel_id] = asyncio.Lock()
    return channel_locks[channel_id]

@bot.event
async def on_voice_state_update(member, before, after):
    user_id = member.id
    now = datetime.now(UTC).timestamp()

    try:
        if after.channel and not before.channel:
            if after.channel.id in BLACKLISTED_CHANNELS:
                return

            # Пользователь зашёл в голосовой — добавляем сессию
            response = supabase.table("voice_sessions").insert({
                "user_id": user_id,
                "start_time": now
            }).execute()

            # Проверяем, что данные вернулись
            if not response.data:
                print(f"❌ Ошибка при вставке сессии: пустой ответ от Supabase")

        elif before.channel and not after.channel:
            if before.channel.id in BLACKLISTED_CHANNELS:
                return
            # Пользователь вышел из голосового — получаем время старта
            row = supabase.table("voice_sessions").select("start_time").eq("user_id", user_id).limit(1).execute()

            if not row.data:
                print(f"❌ Не найдена сессия для пользователя {user_id}")
                return

            start_time = row.data[0]["start_time"]
            duration = int(now - start_time)

            # Удаляем сессию
            del_resp = supabase.table("voice_sessions").delete().eq("user_id", user_id).execute()
            if not del_resp.data:
                print(f"❌ Ошибка при удалении сессии")

            # Обновляем/вставляем время в voice_time
            time_row = supabase.table("voice_time").select("total_seconds").eq("user_id", user_id).limit(1).execute()
            if time_row.data:
                total_seconds = time_row.data[0]["total_seconds"] + duration
                upd_resp = supabase.table("voice_time").update({"total_seconds": total_seconds}).eq("user_id", user_id).execute()
                if not upd_resp.data:
                    print(f"❌ Ошибка при обновлении времени для пользователя {user_id}")
            else:
                ins_resp = supabase.table("voice_time").insert({
                    "user_id": user_id,
                    "total_seconds": duration
                }).execute()
                if not ins_resp.data:
                    print(f"❌ Ошибка при вставке нового времени для пользователя {user_id}")

    except Exception as e:
        print(f"❌ Общая ошибка при обновлении статистики: {e}")

    # Оставляем остальную часть кода без изменений
    if before.channel and before.channel.id in created_channels:
        await asyncio.sleep(1)
        lock = await get_channel_lock(before.channel.id)
        async with lock:
            owner_id = created_channels[before.channel.id]
            members = before.channel.members

            if len(members) == 0:
                await before.channel.delete()
                created_channels.pop(before.channel.id, None)
                channel_bases.pop(before.channel.id, None)
                setup_messages.pop(before.channel.id, None)
                print(f"Удалён пустой канал: {before.channel.name}")
                room_modes.pop(before.channel.id, None)
                return

            if member.id == owner_id:
                new_owner = random.choice(members)
                created_channels[before.channel.id] = new_owner.id
                old_msg = setup_messages.get(before.channel.id)
                if old_msg:
                    try:
                        await old_msg.delete()
                        print("✅ Старое сообщение успешно удалено.")
                    except discord.NotFound:
                        print("⚠️ Сообщение уже было удалено ранее.")
                    except Exception as e:
                        print(f"❌ Ошибка при удалении сообщения: {e}")
                    finally:
                        setup_messages.pop(before.channel.id, None)

                overwrite = before.channel.overwrites_for(new_owner)
                overwrite.manage_channels = True
                overwrite.move_members = True
                overwrite.connect = True
                await before.channel.set_permissions(new_owner, overwrite=overwrite)

                mode = room_modes.get(before.channel.id, "default")
                view = RoomSetupView(new_owner.id, before.channel.id, mode)
                new_msg = await before.channel.send(
                    f"Владелец комнаты вышел. Новый владелец: {new_owner.mention}\n"
                    f"{new_owner.mention}, настройте комнату:",
                    view=view
                )
                setup_messages[before.channel.id] = new_msg
                print(f"Назначен новый владелец: {new_owner.name} для канала {before.channel.name}")

    if not after.channel or after.channel.name not in TRIGGER_CHANNELS:
        return

    if after.channel and after.channel.name in TRIGGER_CHANNELS:
        conf = TRIGGER_CHANNELS[after.channel.name]
        guild = member.guild
        category = discord.utils.get(guild.categories, name=conf["category"])
        if not category:
            print(f"Категория {conf['category']} не найдена!")
            return

        existing = [
            ch for ch in guild.voice_channels
            if ch.name.startswith(conf["base"]) and ch.category == category
        ]
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

        mode = "custom" if conf["category"] == "Кастомки🔴" else "default"
        room_modes[new_channel.id] = mode
        view = RoomSetupView(member.id, new_channel.id, mode)
        msg = await new_channel.send(f"{member.mention}, настройте комнату:", view=view)
        setup_messages[new_channel.id] = msg



#/////////////////////////////////////////////////////
async def upload_to_google_drive(file_path, folder_id=None):
    file_metadata = {'name': file_path.split('/')[-1]}
    if folder_id:
        file_metadata['parents'] = [folder_id]

    media = MediaFileUpload(file_path, mimetype='image/png')
    file = drive_service.files().create(
        body=file_metadata,
        media_body=media,
        fields='id, webViewLink'
    ).execute()
    print(f"Файл {file_path} загружен в Google Drive. Ссылка: {file['webViewLink']}")
    return file['id'], file['webViewLink']



async def generate_and_send_graph(bot, channel_id, cycle_number):
    try:
        response = supabase.table("weekly_voice_stats") \
            .select("week_number, user_id, total_seconds") \
            .eq("cycle_number", cycle_number) \
            .order("week_number") \
            .order("total_seconds") \
            .execute()

        data = response.data
    except Exception as e:
        print(f"❌ Ошибка при запросе данных для графика: {e}")
        return

    if not data:
        print("Нет данных для графика.")
        return

    users = {}
    weeks = set()
    for row in data:
        week_number = row['week_number']
        user_id = row['user_id']
        total_seconds = row['total_seconds']
        weeks.add(week_number)
        users.setdefault(user_id, {})[week_number] = total_seconds / 3600  # Перевод в часы

    weeks = sorted(list(weeks))
    user_ids = list(users.keys())

    if not user_ids:
        print("Нет пользователей для построения графика.")
        return

    guild = bot.get_guild(520183812148166656)   
    members_dict = {member.id: member.display_name for member in guild.members}

    rcParams['font.family'] = 'Arial'
    rcParams['text.color'] = 'white'
    rcParams['axes.labelcolor'] = 'white'
    rcParams['xtick.color'] = 'white'
    rcParams['ytick.color'] = 'white'

    xmin = min(weeks)
    xmax = max(weeks)
    range_x = xmax - xmin if xmax != xmin else 1
    xmax += range_x * 0.18

    max_y = max([max(users[u].values()) for u in user_ids]) * 1.1 if user_ids else 1
    ymin, ymax = 0, max_y

    fig, ax = plt.subplots(figsize=(19.2, 10.8), dpi=100)
    #///
    current_dir = os.path.dirname(os.path.abspath(__file__))
    image_path = os.path.join(current_dir, "backpack.jpg")

    if not os.path.exists(image_path):
        print(f"❌ Файл не найден: {image_path}")
    else:
        print(f"✅ Файл найден: {image_path}")

    background_img = mpimg.imread(image_path)
    #///
    fig.patch.set_alpha(0.0)
    fig.patch.set_facecolor('none')
    ax.set_facecolor('none')
    ax.imshow(background_img, extent=[xmin, xmax, ymin, ymax], aspect='auto', zorder=0)
    ax.set_xlim(xmin, xmax)
    ax.set_ylim(ymin, ymax)
    ax.tick_params(colors='white')
    ax.xaxis.label.set_color('white')
    ax.yaxis.label.set_color('white')
    ax.title.set_color('white')

    user_sums = {user_id: sum(users[user_id].values()) for user_id in user_ids}
    user_ids_sorted = sorted(user_ids, key=lambda u: user_sums[u], reverse=True)
    lines, labels = [], []
    for user_id in user_ids_sorted:
        member = bot.get_guild(520183812148166656).get_member(user_id)
        member_name = member.display_name if member else f"User {user_id}"
        times = [users[user_id].get(week, 0) for week in weeks]
        line, = ax.plot(weeks, times, marker='o', label=member_name, zorder=1)
        lines.append(line)
        labels.append(member_name)
        for week, time in zip(weeks, times):
            if time > 0:
                ax.text(week, time, f"{int(time)}ч {int((time % 1) * 60)}м", fontsize=8, weight='bold', color='white', zorder=2)

    ax.set_xlabel("Неделя")
    ax.set_ylabel("Время (часы)")
    ax.set_title(f"Голосовая активность - Цикл {cycle_number}")
    ax.legend(lines, labels, loc='upper center', bbox_to_anchor=(0.5, -0.07), ncol=6, fontsize=8, frameon=False)

    filename = f"graph_cycle_{cycle_number}.png"
    plt.savefig(filename, bbox_inches='tight', facecolor=fig.get_facecolor())
    plt.close()

    # Отправляем в Discord
    channel = await bot.fetch_channel(channel_id)
    if channel:
        with open(filename, 'rb') as f:
            await channel.send(content=f"Цикл {cycle_number}:", file=discord.File(f))
    else:
        print("Канал не найден.")

    # Загружаем на Google Drive
    #await upload_to_google_drive(filename, folder_id='1XXjk7oPlijNDSLoiCf2DayVmOMRX-gyK')

#/////////////////////////////////////////////////////

def init_db():
    try:
        # Таблицы создаём вручную через Supabase интерфейс или SQL в Supabase
        print("✅ Проверка подключения к базе данных прошла успешно.")
    except Exception as e:
        print(f"❌ Ошибка при инициализации базы данных: {e}")

#/////////////////////////////////////////////////////
@bot.command()
async def getgraph(ctx, cycle_number: int = None):
    try:
        # Если не передали номер цикла — получаем последний
        if cycle_number is None:
            row = supabase.table("weekly_voice_stats") \
                .select("cycle_number") \
                .order("cycle_number", desc=True) \
                .limit(1) \
                .execute()

            if row.data:
                cycle_number = row.data[0]["cycle_number"]
            else:
                await ctx.send("❌ Нет данных по голосовой активности.")
                return

        # Генерируем и отправляем график
        await generate_and_send_graph(bot, ctx.channel.id, cycle_number)

    except Exception as e:
        await ctx.send(f"❌ Ошибка при создании графика: {e}")

async def weekly_reset():
    while True:
        now = datetime.utcnow()
        days_until_wednesday = (2 - now.weekday() + 7) % 7
        if days_until_wednesday == 0:
            days_until_wednesday = 7
        next_reset = datetime.combine((now + timedelta(days=days_until_wednesday)).date(), datetime.min.time())
        wait_time = (next_reset - now).total_seconds()
        print(f"⏳ Ожидание до следующей среды: {wait_time // 3600:.0f}ч {(wait_time % 3600) // 60:.0f}м")
        await asyncio.sleep(wait_time)

        try:
            print("🔄 Запуск еженедельного сброса...")
            row = supabase.table("weekly_voice_stats").select("cycle_number").order("cycle_number", desc=True).limit(1).execute()
            cycle_number = row.data[0]["cycle_number"] if row.data else 0
            week_data = supabase.table("weekly_voice_stats").select("week_number").eq("cycle_number", cycle_number).order("week_number", desc=True).limit(1).execute()
            max_week_number = week_data.data[0]["week_number"] if week_data.data else 0
            if max_week_number >= 12:
                cycle_number += 1
                max_week_number = 0

            voice_time_rows = supabase.table("voice_time").select("user_id", "total_seconds").execute()

            user_times = []
            for record in voice_time_rows.data:
                user_id = record["user_id"]
                total_seconds = record["total_seconds"]
                user_times.append((user_id, total_seconds))

            # Сортируем по времени
            user_times.sort(key=lambda x: x[1], reverse=True)

            # Начисление опыта
            for i, (user_id, total_seconds) in enumerate(user_times):
                if total_seconds < 60:  # меньше минуты - без опыта
                    continue

                if i == 0:
                    exp = 10
                elif i in [1, 2]:
                    exp = 8
                elif 3 <= i <= 6:
                    exp = 6
                elif 7 <= i <= 9:
                    exp = 4
                else:
                    exp = 2

                # Обновляем опыт
                update_experience(user_id, exp)

                # Сохраняем статистику
                supabase.table("weekly_voice_stats").insert({
                    "cycle_number": cycle_number,
                    "week_number": max_week_number + 1,
                    "user_id": user_id,
                    "total_seconds": total_seconds
                }).execute()

            # Генерация и отправка графика
            await generate_and_send_graph(bot, channel_id=1382278788464771173, cycle_number=cycle_number)

            # Очищаем voice_time
            supabase.table("voice_time").update({"total_seconds": 0}).neq("user_id", -1).execute()

            print("📅 Статистика по времени в голосовых сброшена!")

        except Exception as e:
            print(f"❌ Ошибка при сбросе статистики: {e}")

def update_experience(user_id, added_exp):
    row = supabase.table("user_levels").select("*").eq("user_id", user_id).limit(1).execute()
    if row.data:
        exp = row.data[0]["exp"] + added_exp
        level = calculate_level(exp)
        supabase.table("user_levels").update({"exp": exp, "level": level}).eq("user_id", user_id).execute()
    else:
        supabase.table("user_levels").insert({
            "user_id": user_id,
            "exp": added_exp,
            "level": calculate_level(added_exp)
        }).execute()

def calculate_level(exp):
    if exp < 125:  # 1-5 уровни по 25
        return exp // 25 + 1
    elif exp < 375:  # 6-10 уровни по 50
        return 5 + (exp - 125) // 50 + 1
    elif exp < 1875:  # 11-25 уровни по 100
        return 10 + (exp - 375) // 100 + 1
    else:  # 26+
        return 25 + (exp - 1875) // 150 + 1

def get_next_level_exp(level: int) -> int:
    if level < 5:
        return 25 * level
    elif level < 10:
        return 125 + 50 * (level - 5)
    elif level < 25:
        return 375 + 100 * (level - 10)
    else:
        return 1875 + 150 * (level - 25)

@bot.command()
async def stat(ctx, member: discord.Member = None):
    try:
        member = member or ctx.author
        user_id = member.id

        row = supabase.table("user_levels").select("*").eq("user_id", user_id).limit(1).execute()
        stats = row.data[0] if row.data else {"exp": 0, "level": 1}
        level = stats["level"]
        exp = stats["exp"]

        time_row = supabase.table("voice_time").select("total_seconds").eq("user_id", user_id).execute()
        total_seconds = sum(r["total_seconds"] for r in time_row.data) if time_row.data else 0
        total_hours = total_seconds / 3600
        avg_hours = total_hours / max(len(time_row.data), 1) if time_row.data else 0

        if level <= 5:
            background = "lvl1-5.gif"
        elif level <= 10:
            background = "images/bg2.png"
        elif level <= 25:
            background = "images/bg3.png"
        else:
            background = "images/bg4.png"

        if not os.path.exists(background):
            img = Image.new("RGBA", (800, 500), (0, 0, 0, 255))
        else:
            img = Image.open(background).convert("RGBA")

        draw = ImageDraw.Draw(img)
        font_path = "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"
        font = ImageFont.truetype(font_path, 40)
        small_font = ImageFont.truetype(font_path, 25)

        width, height = img.size

        # Настроим размеры и положение шкалы
        margin = 10
        bar_height = 10
        bar_y = height - bar_height - margin
        bar_x = margin
        bar_w = width - 2 * margin

        next_level_exp = get_next_level_exp(level)
        progress = min(exp / next_level_exp, 1.0)
        progress_w = int(bar_w * progress)

        # Отрисовка прогресс-бара
        draw.rectangle([bar_x, bar_y, bar_x + bar_w, bar_y + bar_height], fill=(100, 100, 100, 180))  # фон
        draw.rectangle([bar_x, bar_y, bar_x + progress_w, bar_y + bar_height], fill=(0, 255, 0, 220))  # заполнение

        # Имя слева над шкалой
        name_y = bar_y - 45
        draw.text((bar_x, name_y), member.display_name, font=font, fill="white")

        # Правый текст (среднее время, общее время, уровень) в один ряд справа над шкалой
        avg_time_str = f"Среднее: {avg_hours:.1f} ч"
        total_time_str = f"Общее: {total_hours:.0f} ч"
        level_str = f"Уровень: {level}"
        right_text = f"{avg_time_str}   {total_time_str}   {level_str}"

        bbox = draw.textbbox((0, 0), right_text, font=small_font)
        text_w = bbox[2] - bbox[0]
        right_x = width - margin - text_w
        right_y = name_y + 8
        draw.text((right_x, right_y), right_text, font=small_font, fill="white")

        # Опыт под шкалой справа
        exp_str = f"Опыт: {exp} / {next_level_exp}"
        exp_bbox = draw.textbbox((0, 0), exp_str, font=small_font)
        exp_w = exp_bbox[2] - exp_bbox[0]
        exp_x = width - margin - exp_w
        exp_y = bar_y + bar_height + 5
        draw.text((exp_x, exp_y), exp_str, font=small_font, fill="white")

        filename = f"stat_{user_id}.png"
        img.save(filename)
        await ctx.send(file=discord.File(filename))

    except Exception as e:
        await ctx.send(f"❌ Ошибка в команде stat: {e}")


@bot.command()
async def setexp(ctx, member: discord.Member = None):
    # Проверка ID автора
    if ctx.author.id != 455023858463014922:
        await ctx.send("❌ У вас нет прав на использование этой команды.")
        return

    # Если не указали пользователя, по умолчанию автор
    member = member or ctx.author
    user_id = member.id

    try:
        # Добавляем опыт
        update_experience(user_id, 10)
        await ctx.send(f"✅ Пользователю {member.display_name} начислено +10 опыта!")
    except Exception as e:
        await ctx.send(f"❌ Ошибка при начислении опыта: {e}")

#//////////////////////////////////////
AUTHORIZED_USER_ID = 455023858463014922

@bot.command()
async def generatestat(ctx):
    if ctx.author.id != AUTHORIZED_USER_ID:
        await ctx.send("❌ У вас нет прав на выполнение этой команды.")
        return

    try:
        print("🔄 Ручной сброс статистики запущен...")

        # Получаем текущий cycle_number
        row = supabase.table("weekly_voice_stats").select("cycle_number").order("cycle_number", desc=True).limit(1).execute()
        cycle_number = row.data[0]["cycle_number"] if row.data else 0

        # Подсчет недель в текущем цикле
        week_data = supabase.table("weekly_voice_stats") \
            .select("week_number") \
            .eq("cycle_number", cycle_number) \
            .order("week_number", desc=True) \
            .limit(1) \
            .execute()

        max_week_number = week_data.data[0]["week_number"] if week_data.data else 0

        if max_week_number >= 12:
            cycle_number += 1
            max_week_number = 0

        # Получаем данные voice_time
        voice_time_rows = supabase.table("voice_time").select("user_id", "total_seconds").execute()
        for record in voice_time_rows.data:
            user_id = record["user_id"]
            total_seconds = record["total_seconds"]
            supabase.table("weekly_voice_stats").insert({
                "cycle_number": cycle_number,
                "week_number": max_week_number + 1,
                "user_id": user_id,
                "total_seconds": total_seconds
            }).execute()

        # Генерация и отправка графика
        await generate_and_send_graph(bot, ctx.channel.id, cycle_number)

        # Обнуляем voice_time
        supabase.table("voice_time").update({"total_seconds": 0}).neq("user_id", -1).execute()

        await ctx.send("📊 Статистика сброшена и график сгенерирован!")

    except Exception as e:
        await ctx.send(f"❌ Ошибка при сбросе статистики: {e}")
        print(f"❌ Ошибка в команде generatestat: {e}")



token = os.getenv("TOKEN")



async def main():
    keep_alive()
    asyncio.create_task(weekly_reset())
    await bot.start(token)

asyncio.run(main())
#await bot.start("")
