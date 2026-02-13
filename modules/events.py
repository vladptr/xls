import discord
import asyncio
import random
from datetime import datetime, timezone, timedelta
from modules.config import bot, BLACKLISTED_CHANNELS, TRIGGER_CHANNELS
from modules.database import supabase
from modules.voice_channels import (
    setup_messages, channel_locks, room_modes, created_channels, 
    channel_bases, get_channel_lock, RoomSetupView
)
from modules.leveling import update_experience

stat_queue = asyncio.Queue()
pending_stats = set()
voice_stat_messages = {}

ADMIN_USER_ID = 455023858463014922

async def reset_channel_permissions(channel, owner_id):
    """Сбрасывает права для всех участников канала, кроме владельца и администратора"""
    try:
        # Убеждаемся, что @everyone не имеет прав на управление каналом
        everyone_overwrite = channel.overwrites_for(channel.guild.default_role)
        everyone_overwrite.manage_channels = False
        everyone_overwrite.move_members = False
        everyone_overwrite.mute_members = False
        everyone_overwrite.deafen_members = False
        await channel.set_permissions(channel.guild.default_role, overwrite=everyone_overwrite)
        
        # Сбрасываем права для всех участников канала, кроме владельца и администратора
        for member in channel.members:
            if member.id != owner_id and member.id != ADMIN_USER_ID:
                member_overwrite = channel.overwrites_for(member)
                member_overwrite.manage_channels = False
                member_overwrite.move_members = False
                member_overwrite.mute_members = False
                member_overwrite.deafen_members = False
                await channel.set_permissions(member, overwrite=member_overwrite)
        
        # Устанавливаем права для владельца
        owner = channel.guild.get_member(owner_id)
        if owner:
            owner_overwrite = channel.overwrites_for(owner)
            owner_overwrite.manage_channels = True  # Управление каналом (включая редактирование доступа по ролям)
            owner_overwrite.move_members = False    # Убрано: отключение игроков
            owner_overwrite.connect = True          # Подключение к каналу
            await channel.set_permissions(owner, overwrite=owner_overwrite)
        
        # Устанавливаем права для администратора (если он на сервере)
        admin = channel.guild.get_member(ADMIN_USER_ID)
        if admin:
            admin_overwrite = channel.overwrites_for(admin)
            admin_overwrite.manage_channels = True
            admin_overwrite.move_members = True
            admin_overwrite.mute_members = True
            admin_overwrite.deafen_members = True
            admin_overwrite.connect = True
            await channel.set_permissions(admin, overwrite=admin_overwrite)
    except Exception as e:
        print(f"❌ Ошибка при сбросе прав канала: {e}")

async def enqueue_stat(member, channel):
    user_id = member.id
    if user_id in pending_stats:
        return  # уже стоит в очереди, не добавляем
    pending_stats.add(user_id)
    await stat_queue.put((member, channel))

async def stat_worker():
    while True:
        member, channel = await stat_queue.get()
        member_id = member.id
        
        if member_id not in pending_stats:
            continue
        
        try:
            if channel.id in BLACKLISTED_CHANNELS:
                continue  # пропускаем каналы из черного списка

            temp_msg = await channel.send(".")
            ctx = await bot.get_context(temp_msg)
            command = bot.get_command("stat")
            stat_msg = await command.callback(ctx, member=member)
            if stat_msg:
                voice_stat_messages[member.id] = stat_msg
            await temp_msg.delete()
        except Exception as e:
            print(f"❌ Ошибка при отправке статистики: {e}")
        finally:
            pending_stats.discard(member.id)  # снимаем блокировку после отправки
            await asyncio.sleep(30)

@bot.event
async def on_ready():
    bot.loop.create_task(stat_worker())
    bot.loop.create_task(clan_verification_check())
    print(f"Bot ready! Logged in as {bot.user}")
    print("✅ Система регистрации и проверки клана активирована")

async def cleanup_user_data(user_id: int, guild: discord.Guild):
    """Удаляет все данные пользователя из базы данных"""
    try:
        # Проверяем, действительно ли пользователь покинул сервер
        member = guild.get_member(user_id)
        if member:
            # Пользователь все еще на сервере, не удаляем
            return False
        
        # Удаляем данные из всех таблиц
        deleted_count = 0
        
        # 1. Удаляем регистрацию
        try:
            supabase.table("user_registrations").delete().eq("discord_id", str(user_id)).execute()
            deleted_count += 1
        except Exception as e:
            print(f"⚠️ Ошибка при удалении регистрации для {user_id}: {e}")
        
        # 2. Удаляем статистику времени в голосовых
        try:
            supabase.table("voice_time").delete().eq("user_id", user_id).execute()
            deleted_count += 1
        except Exception as e:
            print(f"⚠️ Ошибка при удалении voice_time для {user_id}: {e}")
        
        # 3. Удаляем уровни и опыт
        try:
            supabase.table("user_levels").delete().eq("user_id", user_id).execute()
            deleted_count += 1
        except Exception as e:
            print(f"⚠️ Ошибка при удалении user_levels для {user_id}: {e}")
        
        # 4. Удаляем активные сессии голосовых каналов
        try:
            supabase.table("voice_sessions").delete().eq("user_id", user_id).execute()
            deleted_count += 1
        except Exception as e:
            print(f"⚠️ Ошибка при удалении voice_sessions для {user_id}: {e}")
        
        # Примечание: weekly_voice_stats не удаляем, чтобы сохранить историю
        
        if deleted_count > 0:
            print(f"🗑️ Удалены данные пользователя {user_id} из {deleted_count} таблиц")
            return True
        return False
        
    except Exception as e:
        print(f"❌ Ошибка при очистке данных пользователя {user_id}: {e}")
        return False

@bot.event
async def on_member_remove(member):
    """Удаляет запись пользователя из базы при выходе с сервера"""
    try:
        await cleanup_user_data(member.id, member.guild)
        print(f"🗑️ Обработан выход пользователя {member.display_name} ({member.id})")
    except Exception as e:
        print(f"❌ Ошибка при обработке выхода пользователя {member.id}: {e}")

@bot.event
async def on_member_join(member):
    from modules.registration import RegistrationView
    
    try:
        # Отправляем сообщение регистрации в личные сообщения пользователя
        embed = discord.Embed(
            title="Добро пожаловать на сервер! 🎉",
            description=f"Привет, {member.name}!\n\nДля получения доступа к серверу необходимо зарегистрироваться в клане.\nНажмите кнопку **Логин** ниже, чтобы заполнить форму регистрации.",
            color=discord.Color.blue()
        )
        embed.add_field(
            name="Информация",
            value="После заполнения формы бот проверит наличие вашего игрока в клане и выдаст соответствующую роль.",
            inline=False
        )
        
        view = RegistrationView()
        await member.send(embed=embed, view=view)
    except discord.Forbidden:
        # Если у пользователя закрыты личные сообщения, отправляем в канал с упоминанием
        channel = bot.get_channel(1183130293545222205)
        if channel:
            embed = discord.Embed(
                title="Добро пожаловать на сервер! 🎉",
                description=f"Привет, {member.mention}!\n\nДля получения доступа к серверу необходимо зарегистрироваться в клане.\nНажмите кнопку **Логин** ниже, чтобы заполнить форму регистрации.",
                color=discord.Color.blue()
            )
            embed.add_field(
                name="Информация",
                value="После заполнения формы бот проверит наличие вашего игрока в клане и выдаст соответствующую роль.",
                inline=False
            )
            embed.add_field(
                name="⚠️ Внимание",
                value="Рекомендуется открыть личные сообщения от участников сервера, чтобы получать важные уведомления.",
                inline=False
            )
            
            view = RegistrationView()
            await channel.send(embed=embed, view=view)
        else:
            print("Канал для регистрации не найден.")
    except Exception as e:
        print(f"❌ Ошибка при отправке сообщения регистрации пользователю {member.id}: {e}")

@bot.event
async def on_voice_state_update(member, before, after):
    user_id = member.id
    now = datetime.now(timezone.utc).timestamp()
    try:
        # --- Выход или переход: удаляем старую карточку ---
        if before.channel and (not after.channel or before.channel.id != after.channel.id):
            # Сбрасываем права участника при выходе из созданного канала
            if before.channel.id in created_channels:
                owner_id = created_channels[before.channel.id]
                # Если выходящий не владелец, сбрасываем его права
                if user_id != owner_id:
                    member_overwrite = before.channel.overwrites_for(member)
                    member_overwrite.manage_channels = False
                    member_overwrite.move_members = False
                    member_overwrite.mute_members = False
                    member_overwrite.deafen_members = False
                    try:
                        await before.channel.set_permissions(member, overwrite=member_overwrite)
                    except Exception as e:
                        print(f"❌ Ошибка при сбросе прав участника: {e}")
            
            msg = voice_stat_messages.pop(user_id, None)
            if msg:
                try:
                    await msg.delete()
                except discord.NotFound:
                    pass
            pending_stats.discard(user_id)

        # --- Заход или переход: создаём новую карточку ---
        if after.channel and (not before.channel or before.channel.id != after.channel.id):
            # Проверяем и сбрасываем права при входе в созданный канал
            if after.channel.id in created_channels:
                owner_id = created_channels[after.channel.id]
                await reset_channel_permissions(after.channel, owner_id)
            
            if after.channel.id not in BLACKLISTED_CHANNELS and after.channel.name not in TRIGGER_CHANNELS:
                if user_id not in pending_stats:
                    await enqueue_stat(member, after.channel)
        
    except Exception as e:
        print(f"❌ Ошибка при обновлении статистики: {e}")
        
    try:
        if after.channel and not before.channel:
            if after.channel.id in BLACKLISTED_CHANNELS:
                return

            # Пользователь зашёл в голосовой — добавляем сессию
            response = supabase.table("voice_sessions").insert({
                "user_id": user_id,
                "start_time": now
            }).execute()

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
            time_row = supabase.table("voice_time").select("*").eq("user_id", user_id).limit(1).execute()
            if time_row.data:
                total_seconds_week = time_row.data[0]["total_seconds"] + duration
                total_seconds_all_time = time_row.data[0].get("total_seconds_all_time", 0) + duration

                supabase.table("voice_time").update({
                    "total_seconds": total_seconds_week,
                    "total_seconds_all_time": total_seconds_all_time
                }).eq("user_id", user_id).execute()
            else:
                supabase.table("voice_time").insert({
                    "user_id": user_id,
                    "total_seconds": duration,
                    "total_seconds_all_time": duration
                }).execute()

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
                        await old_msg.edit(
                            content=(
                                f"Владелец комнаты вышел. Новый владелец: {new_owner.mention}\n"
                                f"{new_owner.mention}, настройте комнату:"
                            )
                        )
                        print("✅ Старое сообщение успешно обновлено.")
                    except discord.NotFound:
                        # Если вдруг сообщения нет, создаём новое
                        new_msg = await before.channel.send(
                            f"Владелец комнаты вышел. Новый владелец: {new_owner.mention}\n"
                            f"{new_owner.mention}, настройте комнату:"
                        )
                        setup_messages[before.channel.id] = new_msg
                        print("⚠️ Старое сообщение не найдено, создано новое.")
                    except Exception as e:
                        print(f"❌ Ошибка при редактировании сообщения: {e}")

                # Сбрасываем права для всех участников и устанавливаем права только для нового владельца
                await reset_channel_permissions(before.channel, new_owner.id)

                mode = room_modes.get(before.channel.id, "default")
                view = RoomSetupView(new_owner.id, before.channel.id, mode)
                # Привязываем view к старому/новому сообщению
                if old_msg:
                    await old_msg.edit(view=view)
                else:
                    setup_messages[before.channel.id] = new_msg

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

        new_channel = await guild.create_voice_channel(new_name, category=category, rtc_region="rotterdam")

        await member.move_to(new_channel)
        
        # Устанавливаем права только для создателя канала и сбрасываем для всех остальных
        await reset_channel_permissions(new_channel, member.id)
        
        await enqueue_stat(member, new_channel)
        
        created_channels[new_channel.id] = member.id
        channel_bases[new_channel.id] = base_name

        mode = "custom" if conf["category"] == "Кастомки🔴" else "default"
        room_modes[new_channel.id] = mode
        view = RoomSetupView(member.id, new_channel.id, mode)
        msg = await new_channel.send(f"{member.mention}, настройте комнату:", view=view)
        setup_messages[new_channel.id] = msg

async def check_and_cleanup_left_users():
    """Проверяет всех пользователей в базе и удаляет данные тех, кто покинул сервер"""
    try:
        guilds = bot.guilds
        if not guilds:
            print("⚠️ Бот не подключен ни к одному серверу")
            return
        
        # Используем первый сервер
        guild = guilds[0]
        
        # Получаем всех пользователей из базы
        all_user_ids = set()
        
        # Из user_registrations
        try:
            registrations = supabase.table("user_registrations").select("discord_id").execute()
            if registrations.data:
                for reg in registrations.data:
                    discord_id = reg.get("discord_id")
                    if discord_id:
                        all_user_ids.add(int(discord_id))
        except Exception as e:
            print(f"⚠️ Ошибка при получении user_registrations: {e}")
        
        # Из voice_time
        try:
            voice_time_users = supabase.table("voice_time").select("user_id").execute()
            if voice_time_users.data:
                for vt in voice_time_users.data:
                    all_user_ids.add(int(vt.get("user_id")))
        except Exception as e:
            print(f"⚠️ Ошибка при получении voice_time: {e}")
        
        # Из user_levels
        try:
            level_users = supabase.table("user_levels").select("user_id").execute()
            if level_users.data:
                for lu in level_users.data:
                    all_user_ids.add(int(lu.get("user_id")))
        except Exception as e:
            print(f"⚠️ Ошибка при получении user_levels: {e}")
        
        # Проверяем каждого пользователя
        cleaned_count = 0
        for user_id in all_user_ids:
            try:
                member = guild.get_member(user_id)
                if not member:
                    # Пользователь не на сервере - удаляем данные
                    if await cleanup_user_data(user_id, guild):
                        cleaned_count += 1
            except Exception as e:
                print(f"⚠️ Ошибка при проверке пользователя {user_id}: {e}")
        
        if cleaned_count > 0:
            print(f"🧹 Очищены данные {cleaned_count} пользователей, которые покинули сервер")
        else:
            print(f"✅ Все пользователи в базе присутствуют на сервере")
            
    except Exception as e:
        print(f"❌ Ошибка при проверке пользователей на сервере: {e}")
        import traceback
        traceback.print_exc()

async def clan_verification_check():
    """Проверяет всех участников с ролью клана каждые 3 часа"""
    from modules.registration import check_all_members_in_clan
    
    while True:
        await asyncio.sleep(10800)  # 3 часа = 10800 секунд
        
        try:
            # Получаем первую гильдию бота
            guilds = bot.guilds
            if guilds:
                guild = guilds[0]
                print(f"🔄 Запуск проверки участников клана на сервере {guild.id}...")
                await check_all_members_in_clan(guild)
                
                # Также проверяем и очищаем данные пользователей, которые покинули сервер
                print(f"🧹 Проверка пользователей на наличие на сервере...")
                await check_and_cleanup_left_users()
            else:
                print("⚠️ Бот не подключен ни к одному серверу")
        except Exception as e:
            print(f"❌ Ошибка в задаче проверки клана: {e}")
            import traceback
            traceback.print_exc()

async def weekly_reset():
    while True:
        now = datetime.now(timezone.utc)
        days_until_wednesday = (2 - now.weekday() + 7) % 7
        if days_until_wednesday == 0:
            days_until_wednesday = 7
        next_reset_date = (now + timedelta(days=days_until_wednesday)).date()
        next_reset = datetime.combine(next_reset_date, datetime.min.time()).replace(tzinfo=timezone.utc)
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
            # Получаем всех пользователей, которые когда-либо были в голосовых каналах
            all_users_with_stats = supabase.table("weekly_voice_stats").select("user_id").execute()
            all_user_ids = set()
            if all_users_with_stats.data:
                all_user_ids = {record["user_id"] for record in all_users_with_stats.data}
            
            # Добавляем пользователей из текущей недели
            for record in voice_time_rows.data:
                user_id = record["user_id"]
                total_seconds = record["total_seconds"]
                all_user_ids.add(user_id)
                user_times.append((user_id, total_seconds))

            # Сортируем по времени (только тех, кто был активен на этой неделе)
            user_times.sort(key=lambda x: x[1], reverse=True)

            # Начисление опыта только для активных пользователей
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

            # Сохраняем записи с 0 часов для всех пользователей, которые были активны ранее, но не на этой неделе
            for user_id in all_user_ids:
                # Проверяем, есть ли уже запись для этого пользователя на этой неделе
                existing_week = supabase.table("weekly_voice_stats").select("*").eq("user_id", user_id).eq("cycle_number", cycle_number).eq("week_number", max_week_number + 1).execute()
                if not existing_week.data:
                    # Создаем запись с 0 часов для правильного расчета среднего
                    supabase.table("weekly_voice_stats").insert({
                        "cycle_number": cycle_number,
                        "week_number": max_week_number + 1,
                        "user_id": user_id,
                        "total_seconds": 0
                    }).execute()

            # Обнуляем voice_time только для пользователей, у которых есть записи
            for record in voice_time_rows.data:
                user_id = record["user_id"]
                supabase.table("voice_time").update({"total_seconds": 0}).eq("user_id", user_id).execute()

            print("📅 Статистика по времени в голосовых сброшена!")

        except Exception as e:
            print(f"❌ Ошибка при сбросе статистики: {e}")

