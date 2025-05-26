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
import time
import sqlite3
from datetime import datetime, timedelta
from webserver import keep_alive
import matplotlib.pyplot as plt
import matplotlib.image as mpimg
from matplotlib import rcParams

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
#//////////////////////////////////////

LEADERBOARD_CHANNEL_ID = 1373789452463243314
conn = sqlite3.connect("voice_stats.db")
cursor = conn.cursor()
cursor.execute("""
CREATE TABLE IF NOT EXISTS voice_time (
    user_id INTEGER PRIMARY KEY,
    total_seconds INTEGER
)
""")
cursor.execute("""
CREATE TABLE IF NOT EXISTS voice_sessions (
    user_id INTEGER,
    start_time REAL
)
""")
conn.commit()

#//////////////////////////////////////
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
async def cleargraf(ctx):
    global users, weeks
    try:
        # Очищаем локальные данные
        users.clear()
        weeks.clear()

        # Очищаем базу данных
        conn = sqlite3.connect("voice_stats.db")
        cursor = conn.cursor()
        cursor.execute("DELETE FROM weekly_voice_stats")
        conn.commit()
        conn.close()

        await ctx.send("Все данные графика успешно удалены!")
    except Exception as e:
        await ctx.send(f"Произошла ошибка при очистке данных: {e}")
#//////////////////////////////////////

@bot.command()
async def leaderboard(ctx):
    cursor.execute("SELECT user_id, total_seconds FROM voice_time ORDER BY total_seconds DESC LIMIT 30")
    rows = cursor.fetchall()
    if not rows:
        await ctx.send("Нет данных по времени в голосовых!")
        return

    leaderboard_text = "**🏆 Топ 30 по времени в голосовых:**\n"
    for i, (user_id, total_seconds) in enumerate(rows, start=1):
        member = ctx.guild.get_member(user_id)
        name = member.display_name if member else f"User {user_id}"
        hours, remainder = divmod(total_seconds, 3600)
        minutes, seconds = divmod(remainder, 60)
        leaderboard_text += f"{i}. {name}: {hours}ч {minutes}м {seconds}с\n"

    await ctx.send(leaderboard_text)

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
    guild = member.guild
#//////////////////////////////////////
    user_id = member.id
    now = datetime.utcnow().timestamp()

    if after.channel and not before.channel:
        # Пользователь зашёл в голосовой
        cursor.execute("INSERT INTO voice_sessions (user_id, start_time) VALUES (?, ?)", (user_id, now))
        conn.commit()

    elif before.channel and not after.channel:
        # Пользователь вышел из голосового
        cursor.execute("SELECT start_time FROM voice_sessions WHERE user_id = ?", (user_id,))
        row = cursor.fetchone()
        if row:
            start_time = row[0]
            duration = int(now - start_time)
            cursor.execute("DELETE FROM voice_sessions WHERE user_id = ?", (user_id,))
            cursor.execute("INSERT OR IGNORE INTO voice_time (user_id, total_seconds) VALUES (?, 0)", (user_id,))
            cursor.execute("UPDATE voice_time SET total_seconds = total_seconds + ? WHERE user_id = ?", (duration, user_id))
            conn.commit()
#//////////////////////////////////////
    if before.channel and before.channel.id in created_channels:
        await asyncio.sleep(1)  # можно оставить меньше, 3 сек много
        lock = await get_channel_lock(before.channel.id)
        async with lock:
            owner_id = created_channels[before.channel.id]
            members = before.channel.members

            if len(members) == 0:
                # Комната пуста — удаляем
                await before.channel.delete()
                created_channels.pop(before.channel.id, None)
                channel_bases.pop(before.channel.id, None)
                setup_messages.pop(before.channel.id, None)
                print(f"Удалён пустой канал: {before.channel.name}")
                room_modes.pop(before.channel.id, None)
                return

            if member.id == owner_id:
                # Назначаем нового владельца
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

                mode = room_modes.get(before.channel.id, "default")  # ✅ Берём напрямую


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

    # Определяем mode для селектов
    if conf["category"] == "Кастомки🔴":
        mode = "custom"
    else:
        mode = "default"
    room_modes[new_channel.id] = mode 

    view = RoomSetupView(member.id, new_channel.id, mode)
    msg = await new_channel.send(f"{member.mention}, настройте комнату:", view=view)
    setup_messages[new_channel.id] = msg


token = os.getenv("TOKEN")

if not token:
    print("❌ TOKEN is missing!")
else:
    print("✅ Token loaded!")

#/////////////////////////////////////////////////////

async def generate_and_send_graph(bot, channel_id, cycle_number):
    conn = sqlite3.connect("voice_stats.db")
    cursor = conn.cursor()

    cursor.execute("""
        SELECT week_number, user_id, total_seconds
        FROM weekly_voice_stats
        WHERE cycle_number = ?
        ORDER BY week_number, total_seconds DESC
    """, (cycle_number,))
    data = cursor.fetchall()

    if not data:
        print("Нет данных для графика.")
        return

    users = {}
    weeks = set()
    for week_number, user_id, total_seconds in data:
        weeks.add(week_number)
        users.setdefault(user_id, {})[week_number] = total_seconds / 3600

    weeks = sorted(list(weeks))
    user_ids = list(users.keys())

    if not user_ids:
        print("Нет пользователей для построения графика.")
        return

    rcParams['font.family'] = 'Arial'
    rcParams['text.color'] = 'white'
    rcParams['axes.labelcolor'] = 'white'
    rcParams['xtick.color'] = 'white'
    rcParams['ytick.color'] = 'white'


    # Сначала вычисляем xmin, xmax, ymin, ymax
    xmin = min(weeks)
    xmax = max(weeks)
    range_x = xmax - xmin if xmax != xmin else 1  # Защита от деления на ноль
    xmax += range_x * 0.18  # Добавляем справа 15%

    max_y = max([max(users[u].values()) for u in user_ids]) * 1.1 if user_ids else 1
    ymin, ymax = 0, max_y

    fig, ax = plt.subplots(figsize=(19.2, 10.8), dpi=100)
    
    background_img = mpimg.imread('backpack.jpg')

    fig.patch.set_alpha(0.0)
    fig.patch.set_facecolor('none')
    ax.set_facecolor('none')

    # Показываем фон с учетом новых лимитов
    ax.imshow(background_img, extent=[xmin, xmax, ymin, ymax], aspect='auto', zorder=0)

    ax.set_xlim(xmin, xmax)
    ax.set_ylim(ymin, ymax)

    ax.tick_params(colors='white')
    ax.xaxis.label.set_color('white')
    ax.yaxis.label.set_color('white')
    ax.title.set_color('white')

    user_sums = {user_id: sum(users[user_id].values()) for user_id in user_ids}
    user_ids_sorted = sorted(user_ids, key=lambda u: user_sums[u], reverse=True)

    lines = []
    labels = []

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

    ax.legend(lines, labels, loc='upper center', bbox_to_anchor=(0.1, -0.07), ncol=10, fontsize=8, frameon=False)


    filename = f"graph_cycle_{cycle_number}.png"
    plt.savefig(filename, bbox_inches='tight', facecolor=fig.get_facecolor())
    plt.close()

    # Отправляем в канал
    channel = bot.get_channel(channel_id)
    if channel:
        with open(filename, 'rb') as f:
            await channel.send(content=f"📊 Статистика голосовой активности за цикл {cycle_number}:", file=discord.File(f))
    else:
        print("Канал не найден.")

    conn.close()

@bot.event
async def on_ready():
    bot.loop.create_task(weekly_reset())

#/////////////////////////////////////////////////////

def init_db():
    conn = sqlite3.connect("voice_stats.db")
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS weekly_voice_stats (
            cycle_number INTEGER,
            week_number INTEGER,
            user_id INTEGER,
            total_seconds INTEGER
        )
    """)
    conn.commit()
    conn.close()
#/////////////////////////////////////////////////////

async def weekly_reset():
    while True:
        now = datetime.utcnow()
        # Рассчитываем время до ближайшего понедельника 00:00
        next_monday = now + timedelta(days=(7 - now.weekday()))
        next_reset = datetime.combine(next_monday.date(), datetime.min.time())
        wait_time = (next_reset - now).total_seconds() #2*60
        await asyncio.sleep(wait_time)
#/////////////////////////////////////////////////////
        # Получаем текущий цикл
        conn = sqlite3.connect("voice_stats.db")
        cursor = conn.cursor()
        cursor.execute("SELECT MAX(cycle_number) FROM weekly_voice_stats")
        row = cursor.fetchone()
        cycle_number = (row[0] or 0)
        # Проверяем, если цикл >= 12 недель, увеличиваем номер цикла
        cursor.execute("SELECT COUNT(DISTINCT week_number) FROM weekly_voice_stats WHERE cycle_number = ?", (cycle_number,))
        week_count = cursor.fetchone()[0]
        if week_count >= 12:
            cycle_number += 1

        # Сохраняем текущую статистику в weekly_voice_stats
        cursor.execute("SELECT user_id, total_seconds FROM voice_time")
        for user_id, total_seconds in cursor.fetchall():
            cursor.execute("INSERT INTO weekly_voice_stats (cycle_number, week_number, user_id, total_seconds) VALUES (?, ?, ?, ?)",
                           (cycle_number, week_count + 1, user_id, total_seconds))
        conn.commit()

        # Отправляем график в канал
        await generate_and_send_graph(bot, channel_id=1373789452463243314, cycle_number=cycle_number)
#/////////////////////////////////////////////////////

        # Сброс статистики
        cursor.execute("DELETE FROM voice_time")
        conn.commit()
        print("📅 Статистика по времени в голосовых сброшена!")

@bot.event
async def on_ready():
    init_db()
    bot.loop.create_task(weekly_reset())
    print(f"Бот запущен как {bot.user}")

#//////////////////////////////////////

async def main():
    keep_alive()
    await bot.start(token)

asyncio.run(main())
#await bot.start("")
