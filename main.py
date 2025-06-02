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

setup_messages = {}
channel_locks = {}
room_modes = {}
last_rename_times = {}

users = {}
weeks = []

intents = discord.Intents.default()
intents.guilds = True
intents.members = True
intents.voice_states = True
intents.message_content = True

SERVICE_ACCOUNT_FILE = 'botfile.json'
SCOPES = ['https://www.googleapis.com/auth/drive.file']
credentials = service_account.Credentials.from_service_account_file(
    SERVICE_ACCOUNT_FILE, scopes=SCOPES)
drive_service = build('drive', 'v3', credentials=credentials)

bot = commands.Bot(command_prefix="!", intents=intents)
LEADERBOARD_CHANNEL_ID = 1371926685435428927

def get_connection():
    url = "https://qyqicdyzaagumqjlczoj.supabase.co"
    key = os.getenv("keykey")  
    return create_client(url, key)

supabase = get_connection()
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


@bot.event
async def on_member_join(member):
    channel_id = 1183130293545222205  # замените на ID вашего канала
    channel = bot.get_channel(channel_id)
    if channel:
        await channel.send(f"Привет, {member.mention}! Добро пожаловать на сервер! 🎉 Прочти правила сервера и замени свой ник как показано в примере: ```Ник в игре (Имя)```")
    else:
        print("Канал для приветствия не найден.")


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
        embed = self.generate_embed()
        await interaction.response.edit_message(embed=embed, view=self)

    def generate_embed(self):
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
            name = member.display_name if member else f"User {user_id}"
            hours, remainder = divmod(total_seconds, 3600)
            minutes, seconds = divmod(remainder, 60)
            embed.add_field(name=f"{i}. {name}", value=f"{hours}ч {minutes}м {seconds}с", inline=False)
        
        return embed

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
        embed = view.generate_embed()
        message = await ctx.send(embed=embed, view=view)
        
        # Удаляем сообщение с топом и командой через 5 минут (300 секунд)
        await asyncio.sleep(10)
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
    now = datetime.utcnow().timestamp()

    try:
        if after.channel and not before.channel:
            # Пользователь зашёл в голосовой — добавляем сессию
            response = supabase.table("voice_sessions").insert({
                "user_id": user_id,
                "start_time": now
            }).execute()

            # Проверяем, что данные вернулись
            if not response.data:
                print(f"❌ Ошибка при вставке сессии: пустой ответ от Supabase")

        elif before.channel and not after.channel:
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
    await guild.fetch_members(limit=None)
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
    background_img = mpimg.imread('backpack.jpg')
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
        member = bot.get_guild(1371926685435428924).get_member(user_id)
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
    ax.legend(lines, labels, loc='upper center', bbox_to_anchor=(0.1, -0.07), ncol=6, fontsize=8, frameon=False)

    filename = f"graph_cycle_{cycle_number}.png"
    plt.savefig(filename, bbox_inches='tight', facecolor=fig.get_facecolor())
    plt.close()

    # Отправляем в Discord
    channel = bot.get_channel(channel_id)
    if channel:
        with open(filename, 'rb') as f:
            await channel.send(content=f"Цикл {cycle_number}:", file=discord.File(f))
    else:
        print("Канал не найден.")

    # Загружаем на Google Drive
    await upload_to_google_drive(filename, folder_id='1XXjk7oPlijNDSLoiCf2DayVmOMRX-gyK')

@bot.event
async def on_ready():
    bot.loop.create_task(weekly_reset())

#/////////////////////////////////////////////////////

def init_db():
    try:
        # Таблицы создаём вручную через Supabase интерфейс или SQL в Supabase
        print("✅ Проверка подключения к базе данных прошла успешно.")
    except Exception as e:
        print(f"❌ Ошибка при инициализации базы данных: {e}")

#/////////////////////////////////////////////////////

async def weekly_reset():
    while True:
        now = datetime.utcnow()
        next_monday = now + timedelta(days=(2 - now.weekday() + 7) % 7)
        next_reset = datetime.combine(next_monday.date(), datetime.min.time())
        wait_time = (next_reset - now).total_seconds()
        await asyncio.sleep(wait_time)

        try:
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

            if week_data.data:
              max_week_number = week_data.data[0]["week_number"]
            else:
              max_week_number = 0

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
            await generate_and_send_graph(bot, channel_id=1373789452463243314, cycle_number=cycle_number)

            # Очищаем voice_time
            response = supabase.table("voice_time").update({"total_seconds": 0}).neq("user_id", -1).execute()

            print("📅 Статистика по времени в голосовых сброшена!")

        except Exception as e:
            print(f"❌ Ошибка при сбросе статистики: {e}")

@bot.event
async def on_ready():
    init_db()  # Подключение или проверка базы
    bot.loop.create_task(weekly_reset())  # Запуск задачи сброса
    print(f"✅ Бот запущен как {bot.user}")

#//////////////////////////////////////
token = os.getenv("TOKEN")
async def main():
    keep_alive()
    await bot.start(token)

asyncio.run(main())
#await bot.start("")
