import discord
from discord.ext import commands
from modules.config import bot, AUTHORIZED_USER_ID, AI_SYSTEM_PROMPT, AI_PROVIDER, AI_ENABLED
from modules.database import supabase
from modules.leveling import update_experience
from modules.pubg_stats import stat as pubg_stat
from modules.leaderboard import leaderboard as leaderboard_func
from modules.registration import RegistrationView, REGISTRATION_CHANNEL_ID
from modules.ai_chat import chat
from modules.ai_chat import chat

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

@commands.cooldown(1, 60, commands.BucketType.user)
@bot.command()
async def leaderboard(ctx):
    await leaderboard_func(ctx)

@bot.command()
async def stat(ctx, member: discord.Member = None):
    await pubg_stat(ctx, member)

@bot.command()
async def setexp(ctx, member: discord.Member = None):
    # Проверка ID автора
    if ctx.author.id != AUTHORIZED_USER_ID:
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

@bot.command()
@commands.has_permissions(manage_messages=True)
async def resetstat(ctx, member: discord.Member):
    try:
        user_id = member.id

        # Обнуляем опыт
        supabase.table("user_levels").upsert({"user_id": user_id, "exp": 0}).execute()
        await ctx.send(f"🔁 Статистика пользователя {member.mention} сброшена.")

    except Exception as e:
        await ctx.send(f"❌ Ошибка при сбросе: {e}")

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

        # Обнуляем voice_time
        supabase.table("voice_time").update({"total_seconds": 0}).neq("user_id", -1).execute()

        await ctx.send("📊 Статистика сброшена!")

    except Exception as e:
        await ctx.send(f"❌ Ошибка при сбросе статистики: {e}")
        print(f"❌ Ошибка в команде generatestat: {e}")

@bot.command()
@commands.has_permissions(administrator=True)
async def send_registration(ctx):
    """Отправляет форму регистрации в канал"""
    embed = discord.Embed(
        title="Регистрация в клане 🎮",
        description="Для получения доступа к серверу необходимо зарегистрироваться в клане.\nНажмите кнопку **Логин** ниже, чтобы заполнить форму регистрации.",
        color=discord.Color.blue()
    )
    embed.add_field(
        name="Информация",
        value="После заполнения формы бот проверит наличие вашего игрока в клане и выдаст соответствующую роль.",
        inline=False
    )
    
    view = RegistrationView()
    await ctx.send(embed=embed, view=view)

@bot.command(name="form")
async def form(ctx, *, member_input: str = None):
    """Отправляет форму регистрации в личные сообщения указанному пользователю
    
    Использование: !form @пользователь
    """
    print(f"🔍 Команда !form вызвана пользователем {ctx.author.id} ({ctx.author.display_name})")
    print(f"🔍 Аргументы команды: {member_input}")
    
    # Проверка ID автора - только определенный пользователь может использовать команду
    if ctx.author.id != AUTHORIZED_USER_ID:
        print(f"❌ Доступ запрещен для пользователя {ctx.author.id} (требуется {AUTHORIZED_USER_ID})")
        await ctx.send("❌ У вас нет прав на использование этой команды.")
        return
    
    # Проверка наличия упоминания пользователя
    if not member_input:
        print(f"⚠️ Пользователь не указан в команде")
        await ctx.send("❌ Укажите пользователя для отправки формы. Использование: `!form @пользователь`")
        return
    
    # Парсим упоминание пользователя
    member = None
    
    # Пытаемся найти пользователя по упоминанию
    if ctx.message.mentions:
        member = ctx.message.mentions[0]
        print(f"🔍 Найден пользователь по упоминанию: {member.id} ({member.display_name})")
    else:
        # Пытаемся найти по ID или имени
        try:
            # Пытаемся найти по ID
            if member_input.isdigit():
                member = ctx.guild.get_member(int(member_input))
                if member:
                    print(f"🔍 Найден пользователь по ID: {member.id} ({member.display_name})")
        except:
            pass
        
        # Если не нашли по ID, пытаемся найти по имени
        if not member:
            member = discord.utils.get(ctx.guild.members, name=member_input) or \
                     discord.utils.get(ctx.guild.members, display_name=member_input) or \
                     discord.utils.get(ctx.guild.members, nick=member_input)
            if member:
                print(f"🔍 Найден пользователь по имени: {member.id} ({member.display_name})")
    
    if not member:
        print(f"❌ Пользователь не найден: {member_input}")
        await ctx.send(f"❌ Пользователь '{member_input}' не найден на сервере. Используйте упоминание: `!form @пользователь`")
        return
    
    print(f"📤 Попытка отправить форму регистрации пользователю {member.id} ({member.display_name})")
    
    try:
        # Создаем embed с формой регистрации
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
        
        # Пытаемся отправить в личные сообщения
        try:
            await member.send(embed=embed, view=view)
            await ctx.send(f"✅ Форма регистрации отправлена пользователю {member.mention} в личные сообщения.")
            print(f"✅ Форма регистрации успешно отправлена пользователю {member.display_name} ({member.id}) через команду !form")
        except discord.Forbidden:
            # Если DM закрыты, отправляем в канал с упоминанием
            print(f"⚠️ Личные сообщения закрыты для пользователя {member.display_name}, отправляем в канал")
            await ctx.send(
                f"{member.mention}, привет! Я не смог отправить тебе сообщение в личку. "
                f"Пожалуйста, открой личные сообщения, чтобы пройти регистрацию.",
                embed=embed, view=view
            )
            print(f"⚠️ Форма регистрации отправлена в канал {ctx.channel.name} для {member.display_name} (DM закрыты)")
        except Exception as e:
            print(f"❌ Ошибка при отправке формы регистрации пользователю {member.id}: {e}")
            import traceback
            traceback.print_exc()
            await ctx.send(f"❌ Ошибка при отправке формы регистрации: {e}")
            
    except Exception as e:
        print(f"❌ Критическая ошибка в команде form: {e}")
        import traceback
        traceback.print_exc()
        await ctx.send(f"❌ Произошла ошибка: {e}")

@bot.command()
async def rebind(ctx, nickname: str = None):
    """Перепривязка аккаунта PUBG к вашему аккаунту Discord"""
    from modules.registration import get_player_info, CLAN_ROLE_ID
    
    if not nickname:
        await ctx.send("❌ Укажите ваш ник в PUBG. Использование: `!rebind ваш_ник`")
        return
    
    await ctx.send("⏳ Проверяю данные...")
    
    # Получаем информацию об игроке по нику (player_id, актуальный ник, статус в клане)
    player_id, current_nickname, is_in_clan = await get_player_info(nickname)
    
    if not player_id:
        await ctx.send(f"❌ Игрок с ником '{nickname}' не найден в PUBG. Проверьте правильность написания ника.")
        return
    
    # Проверяем, не привязан ли уже этот player_id к другому Discord аккаунту
    existing_registration = supabase.table("user_registrations").select("*").eq("player_id", player_id).execute()
    if existing_registration.data:
        existing_discord_id = existing_registration.data[0].get("discord_id")
        if str(existing_discord_id) != str(ctx.author.id):
            existing_nickname = existing_registration.data[0].get("pubg_nickname", nickname)
            await ctx.send(
                f"❌ Игрок с ником '{existing_nickname}' (player_id: {player_id}) уже привязан к другому аккаунту Discord. "
                f"Если это ваш аккаунт, обратитесь к администратору."
            )
            return
    
    # Получаем текущую регистрацию пользователя
    user_registration = supabase.table("user_registrations").select("*").eq("discord_id", ctx.author.id).execute()
    
    if not user_registration.data:
        await ctx.send(
            "❌ Вы не зарегистрированы. Используйте команду регистрации через форму или обратитесь к администратору."
        )
        return
    
    registration_data = user_registration.data[0]
    registration_name = registration_data.get("name", "")
    
    if not is_in_clan:
        await ctx.send(
            f"❌ Игрок с ником '{current_nickname if current_nickname else nickname}' не состоит в клане. "
            f"Привязка не выполнена. Если вы только что вступили в клан, подождите несколько минут и попробуйте снова."
        )
        return
    
    # Обновляем привязку player_id к discord_id
    try:
        actual_nickname = current_nickname if current_nickname else nickname
        
        supabase.table("user_registrations").update({
            "player_id": player_id,
            "pubg_nickname": actual_nickname,
            "verified": True
        }).eq("discord_id", ctx.author.id).execute()
        
        # Обновляем никнейм в Discord
        new_nickname = f"{actual_nickname} ({registration_name})"
        try:
            await ctx.author.edit(nick=new_nickname)
        except discord.Forbidden:
            await ctx.send(f"⚠️ Не удалось изменить никнейм (нет прав). Пожалуйста, измените его вручную на: {new_nickname}")
        except Exception as e:
            print(f"❌ Ошибка при изменении никнейма: {e}")
        
        # Обновляем роль - читаем значение заново из переменной окружения
        from modules.registration import get_clan_role_id
        current_role_id = get_clan_role_id()
        role = ctx.guild.get_role(current_role_id)
        if role:
            if role not in ctx.author.roles:
                await ctx.author.add_roles(role)
                await ctx.send(
                    f"✅ Аккаунт успешно перепривязан! Актуальный ник: **{actual_nickname}**. "
                    f"Вам выдана роль клана. Никнейм обновлен на: **{new_nickname}**"
                )
            else:
                await ctx.send(
                    f"✅ Аккаунт успешно перепривязан! Актуальный ник: **{actual_nickname}**. "
                    f"Никнейм обновлен на: **{new_nickname}**"
                )
        else:
            await ctx.send(f"✅ Аккаунт успешно перепривязан! Актуальный ник: **{actual_nickname}**")
        
    except Exception as e:
        await ctx.send(f"❌ Ошибка при перепривязке аккаунта: {e}")
        print(f"❌ Ошибка при перепривязке аккаунта для {ctx.author.id}: {e}")


@bot.command(name="chat", aliases=["ai", "ask"])
async def chat_command(ctx, *, message: str = None):
    """Чат с языковой моделью через внешний API
    
    Использование: !chat ваш вопрос
    Пример: !chat Что такое PUBG?
    """
    if not message:
        await ctx.send("❌ Укажите ваш вопрос. Использование: `!chat ваш вопрос`")
        return
    
    # Отправляем сообщение о загрузке
    loading_msg = await ctx.send("🤔 Думаю...")
    
    try:
        # Проверяем, включен ли AI
        if not AI_ENABLED:
            await loading_msg.edit(content="❌ AI чат отключен. Включите его через переменную окружения AI_ENABLED=true")
            return
        
        # Получаем ответ от AI
        response = await chat(
            message=message,
            provider=AI_PROVIDER,
            system_prompt=AI_SYSTEM_PROMPT
        )
        
        if response:
            # Удаляем сообщение о загрузке
            await loading_msg.delete()
            
            # Отправляем ответ (ограничиваем длину для Discord)
            if len(response) > 2000:
                response = response[:1997] + "..."
            
            embed = discord.Embed(
                title="🤖 Ответ AI",
                description=response,
                color=discord.Color.blue()
            )
            embed.set_footer(text=f"Запрос от {ctx.author.display_name}")
            
            await ctx.send(embed=embed)
        else:
            await loading_msg.edit(content="❌ Не удалось получить ответ от AI. Проверьте настройки API ключей.")
            
    except Exception as e:
        await loading_msg.edit(content=f"❌ Ошибка при обращении к AI: {e}")
        print(f"❌ Ошибка в команде chat: {e}")

