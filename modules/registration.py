import discord
from discord.ui import View, Button, Modal, TextInput
import requests
import asyncio
import os
from modules.config import PUBG_API_KEY, PUBG_PLATFORM, bot, MAIN_GUILD_ID
from modules.database import supabase

CLAN_ID = "clan.bb296787b8e144959802df1ab9a594da"
# ID роли клана - берется из переменной окружения или использует значение по умолчанию
CLAN_ROLE_ID = int(os.getenv("CLAN_ROLE_ID", "1159121098965786634"))
REGISTRATION_CHANNEL_ID = 1183130293545222205
# MAIN_GUILD_ID уже импортирован из config

# Логирование загруженных значений при импорте модуля
print(f"📋 Модуль registration.py загружен:")
print(f"   CLAN_ROLE_ID = {CLAN_ROLE_ID} (из {'переменной окружения CLAN_ROLE_ID' if os.getenv('CLAN_ROLE_ID') else 'значения по умолчанию'})")
print(f"   MAIN_GUILD_ID = {MAIN_GUILD_ID} (из {'переменной окружения MAIN_GUILD_ID' if os.getenv('MAIN_GUILD_ID') else 'значения по умолчанию'})")

class RegistrationModal(Modal):
    def __init__(self):
        super().__init__(title="Регистрация в клане")
        
        self.nickname_input = TextInput(
            label="Ник в PUBG",
            placeholder="Введите ваш ник в PUBG",
            required=True,
            max_length=50
        )
        
        self.name_input = TextInput(
            label="Ваше имя",
            placeholder="Введите ваше имя",
            required=True,
            max_length=50
        )
        
        self.pubg_plus_input = TextInput(
            label="PUBG+ (да/нет)",
            placeholder="Введите 'да' или 'нет'",
            required=True,
            max_length=3
        )
        
        self.add_item(self.nickname_input)
        self.add_item(self.name_input)
        self.add_item(self.pubg_plus_input)
    
    async def on_submit(self, interaction: discord.Interaction):
        nickname = self.nickname_input.value.strip()
        name = self.name_input.value.strip()
        pubg_plus = self.pubg_plus_input.value.strip().lower()
        
        # Валидация PUBG+
        if pubg_plus not in ['да', 'нет']:
            await interaction.response.send_message(
                "❌ Поле 'PUBG+' должно содержать 'да' или 'нет'", 
                ephemeral=True
            )
            return
        
        await interaction.response.defer(ephemeral=True)
        
        # Получаем сервер - либо из interaction, либо основной сервер по ID
        guild = interaction.guild
        if not guild:
            # Если форма открыта в DM, находим основной сервер по ID
            if bot.guilds:
                guild = discord.utils.get(bot.guilds, id=MAIN_GUILD_ID) or bot.guilds[0]
                print(f"⚠️ Форма открыта в DM, используем основной сервер бота: {guild.id}")
            else:
                await interaction.followup.send(
                    "❌ Бот не подключен к основному серверу. Обратитесь к администратору.",
                    ephemeral=True
                )
                return
        
        print(f"📝 Начало регистрации для пользователя {interaction.user.id} с ником '{nickname}' на сервере {guild.id}")
        
        # Получаем информацию об игроке по нику (player_id, актуальный ник, статус в клане)
        try:
            player_id, current_nickname, is_in_clan = await get_player_info(nickname)
        except Exception as e:
            print(f"❌ Критическая ошибка при получении информации об игроке: {e}")
            await interaction.followup.send(
                f"❌ Произошла ошибка при проверке игрока. Попробуйте позже или обратитесь к администратору.",
                ephemeral=True
            )
            return
        
        if not player_id:
            print(f"⚠️ Игрок '{nickname}' не найден для пользователя {interaction.user.id}")
            await interaction.followup.send(
                f"❌ Игрок с ником '{nickname}' не найден в PUBG. Проверьте правильность написания ника.",
                ephemeral=True
            )
            return
        
        # Проверяем, не привязан ли уже этот player_id к другому Discord аккаунту
        # Сначала проверяем по player_id (если колонка существует), затем по нику
        print(f"🔍 Проверка существующих привязок для player_id: {player_id}")
        try:
            # Пытаемся проверить по player_id
            try:
                existing_user = supabase.table("user_registrations").select("*").eq("player_id", player_id).execute()
                print(f"📊 Проверка по player_id: {len(existing_user.data) if existing_user.data else 0} записей найдено")
                if existing_user.data:
                    existing_discord_id = existing_user.data[0].get("discord_id")
                    print(f"🔍 Существующий discord_id: {existing_discord_id}, текущий: {interaction.user.id}")
                    if str(existing_discord_id) != str(interaction.user.id):
                        existing_nickname = existing_user.data[0].get("pubg_nickname", nickname)
                        print(f"❌ Конфликт привязки: игрок уже привязан к другому аккаунту")
                        await interaction.followup.send(
                            f"❌ Игрок с ником '{existing_nickname}' (player_id: {player_id}) уже привязан к другому аккаунту Discord!", 
                            ephemeral=True
                        )
                        return
            except Exception as e:
                # Если колонка player_id не существует, проверяем по нику
                print(f"⚠️ Колонка player_id не найдена, проверяем по нику: {e}")
                existing_user = supabase.table("user_registrations").select("*").eq("pubg_nickname", current_nickname).execute()
                print(f"📊 Проверка по нику: {len(existing_user.data) if existing_user.data else 0} записей найдено")
                if existing_user.data:
                    existing_discord_id = existing_user.data[0].get("discord_id")
                    print(f"🔍 Существующий discord_id: {existing_discord_id}, текущий: {interaction.user.id}")
                    if str(existing_discord_id) != str(interaction.user.id):
                        existing_nickname = existing_user.data[0].get("pubg_nickname", nickname)
                        print(f"❌ Конфликт привязки: игрок уже привязан к другому аккаунту")
                        await interaction.followup.send(
                            f"❌ Игрок с ником '{existing_nickname}' уже привязан к другому аккаунту Discord!", 
                            ephemeral=True
                        )
                        return
        except Exception as e:
            print(f"❌ Ошибка при проверке существующих привязок: {e}")
            import traceback
            traceback.print_exc()
            await interaction.followup.send(
                f"❌ Ошибка при проверке данных. Попробуйте позже.",
                ephemeral=True
            )
            return
        
        print(f"🔍 Проверка клана: is_in_clan = {is_in_clan}, player_id = {player_id}")
        if is_in_clan:
            # Игрок в клане - привязываем player_id к discord_id
            actual_nickname = current_nickname if current_nickname else nickname
            print(f"✅ Игрок {actual_nickname} найден в клане для пользователя {interaction.user.id}")
            
            # Проверяем, что guild существует
            if not guild:
                print(f"❌ Ошибка: guild равен None для пользователя {interaction.user.id}")
                await interaction.followup.send(
                    "❌ Ошибка: не удалось определить сервер. Регистрация возможна только на сервере.",
                    ephemeral=True
                )
                return
            
            try:
                # Получаем участника сервера (Member), чтобы работать с ролями и никнеймом
                member = guild.get_member(interaction.user.id)
                if not member:
                    # Если участник не найден в кэше, пробуем получить его напрямую
                    try:
                        member = await guild.fetch_member(interaction.user.id)
                    except Exception:
                        print(f"⚠️ Участник {interaction.user.id} не найден на сервере {guild.id}")
                        await interaction.followup.send(
                            "❌ Не удалось найти вас на сервере. Убедитесь, что вы на сервере и попробуйте снова.",
                            ephemeral=True
                        )
                        return
                
                # Выдаем роль
                print(f"🔍 [DEBUG] Текущее значение CLAN_ROLE_ID: {CLAN_ROLE_ID}")
                print(f"🔍 [DEBUG] Тип CLAN_ROLE_ID: {type(CLAN_ROLE_ID)}")
                print(f"🔍 [DEBUG] ID сервера: {guild.id}")
                role = guild.get_role(CLAN_ROLE_ID)
                print(f"🔍 Поиск роли с ID {CLAN_ROLE_ID}: {role}")
                if role:
                    try:
                        await member.add_roles(role)
                        print(f"✅ Роль выдана пользователю {interaction.user.id}")
                    except Exception as e:
                        print(f"❌ Ошибка при выдаче роли пользователю {interaction.user.id}: {e}")
                        import traceback
                        traceback.print_exc()
                        await interaction.followup.send(
                            f"❌ Ошибка при выдаче роли: {e}", 
                            ephemeral=True
                        )
                        return
                else:
                    print(f"⚠️ Роль с ID {CLAN_ROLE_ID} не найдена на сервере!")
                    await interaction.followup.send(
                        f"⚠️ Роль клана не найдена на сервере. Обратитесь к администратору.",
                        ephemeral=True
                    )
                    return
                
                # Меняем никнейм пользователя на формат "ник (имя)"
                
                new_nickname = f"{actual_nickname} ({name})"
                print(f"🔍 Попытка изменить никнейм на: {new_nickname}")
                if member:
                    try:
                        await member.edit(nick=new_nickname)
                        print(f"✅ Никнейм изменен для пользователя {interaction.user.id}: {new_nickname}")
                    except discord.Forbidden:
                        print(f"⚠️ Нет прав на изменение никнейма для пользователя {interaction.user.id}")
                        # Не возвращаемся, продолжаем сохранение данных
                    except Exception as e:
                        print(f"❌ Ошибка при изменении никнейма для пользователя {interaction.user.id}: {e}")
                        import traceback
                        traceback.print_exc()
                        # Не возвращаемся, продолжаем сохранение данных
                else:
                    print(f"⚠️ Участник не найден на сервере, пропускаем изменение никнейма")
                
                # Сохраняем данные в базу - привязываем player_id к discord_id
                print(f"💾 Сохранение данных в базу для пользователя {interaction.user.id}")
                try:
                    # Формируем данные для сохранения
                    data_to_save = {
                        "discord_id": str(interaction.user.id),
                        "pubg_nickname": actual_nickname,
                        "name": name,
                        "pubg_plus": pubg_plus == "да",
                        "verified": True
                    }
                    
                    # Пытаемся добавить player_id (если колонка существует)
                    try:
                        data_to_save["player_id"] = player_id
                        result = supabase.table("user_registrations").upsert(data_to_save).execute()
                        print(f"✅ Данные сохранены с player_id")
                    except Exception as e:
                        # Если колонка player_id не существует, сохраняем без неё
                        print(f"⚠️ Колонка player_id не найдена, сохраняем без неё: {e}")
                        data_to_save.pop("player_id", None)
                        result = supabase.table("user_registrations").upsert(data_to_save).execute()
                        print(f"✅ Данные сохранены без player_id (колонка будет добавлена позже)")
                    
                    print(f"✅ Данные сохранены в базу для пользователя {interaction.user.id}")
                    print(f"📊 Результат сохранения: {result.data if hasattr(result, 'data') else 'OK'}")
                    
                    await interaction.followup.send(
                        f"✅ Регистрация успешна! Игрок привязан к вашему аккаунту. Вам выдана роль клана. Никнейм изменен на: **{new_nickname}**. Добро пожаловать, {name}!",
                        ephemeral=True
                    )
                    print(f"✅ Сообщение об успехе отправлено пользователю {interaction.user.id}")
                except Exception as e:
                    print(f"❌ Ошибка при сохранении данных для пользователя {interaction.user.id}: {e}")
                    import traceback
                    traceback.print_exc()
                    await interaction.followup.send(
                        f"❌ Ошибка при сохранении данных: {e}",
                        ephemeral=True
                    )
            except Exception as e:
                print(f"❌ Критическая ошибка в блоке регистрации для пользователя {interaction.user.id}: {e}")
                import traceback
                traceback.print_exc()
                try:
                    await interaction.followup.send(
                        f"❌ Произошла ошибка при регистрации. Попробуйте позже или обратитесь к администратору.",
                        ephemeral=True
                    )
                except:
                    pass
        else:
            # Игрок НЕ в клане - НЕ привязываем player_id, НЕ меняем никнейм
            print(f"❌ Игрок '{nickname}' не состоит в клане для пользователя {interaction.user.id}")
            await interaction.followup.send(
                f"❌ Игрок с ником '{nickname}' не состоит в клане. Привязка не выполнена. Если вы только что вступили в клан, подождите несколько минут и попробуйте снова.",
                ephemeral=True
            )

class RegistrationView(View):
    def __init__(self):
        super().__init__(timeout=None)
        
        # Создаем кнопку с custom_id для persistent view
        login_button = Button(
            label="Логин",
            style=discord.ButtonStyle.primary,
            emoji="🔐",
            custom_id="registration_login_button"
        )
        login_button.callback = self.login_button_callback
        self.add_item(login_button)
    
    async def login_button_callback(self, interaction: discord.Interaction):
        modal = RegistrationModal()
        await interaction.response.send_modal(modal)
    
    async def on_error(self, interaction: discord.Interaction, error: Exception, item):
        print(f"❌ Ошибка в RegistrationView: {error}")
        try:
            await interaction.response.send_message(
                "❌ Произошла ошибка при обработке запроса. Попробуйте позже.",
                ephemeral=True
            )
        except:
            pass

async def get_player_info(nickname: str):
    """Получает информацию об игроке по нику. Возвращает (player_id, current_nickname, is_in_clan)"""
    try:
        headers = {
            "Authorization": f"Bearer {PUBG_API_KEY}",
            "Accept": "application/vnd.api+json"
        }
        
        # Получаем player_id по нику
        # URL-кодируем ник для безопасности
        import urllib.parse
        encoded_nickname = urllib.parse.quote(nickname)
        url_player = f"https://api.pubg.com/shards/{PUBG_PLATFORM}/players?filter[playerNames]={encoded_nickname}"
        print(f"🔍 Поиск игрока: {nickname} (URL: {url_player})")
        resp_player = requests.get(url_player, headers=headers, timeout=10)
        
        if resp_player.status_code != 200:
            error_text = resp_player.text[:200] if resp_player.text else "Нет текста ошибки"
            print(f"❌ Ошибка при получении данных игрока {nickname}: статус {resp_player.status_code}, ответ: {error_text}")
            return None, None, False
        
        player_data = resp_player.json()
        
        if "data" not in player_data or not player_data["data"]:
            print(f"⚠️ Игрок {nickname} не найден в ответе API")
            return None, None, False
        
        player_info = player_data["data"][0]
        player_id = player_info["id"]
        attributes = player_info.get("attributes", {})
        current_nickname = attributes.get("name", nickname)
        clan_id = attributes.get("clanId")
        is_in_clan = clan_id == CLAN_ID if clan_id else False
        
        print(f"✅ Найден игрок: {current_nickname} (ID: {player_id}), клан: {clan_id}, в целевом клане: {is_in_clan}")
        
        return player_id, current_nickname, is_in_clan
        
    except requests.exceptions.Timeout:
        print(f"❌ Таймаут при проверке клана для игрока {nickname}")
        return None, None, False
    except requests.exceptions.RequestException as e:
        print(f"❌ Ошибка запроса при проверке игрока {nickname}: {e}")
        return None, None, False
    except Exception as e:
        print(f"❌ Неожиданная ошибка при проверке клана для игрока {nickname}: {e}")
        import traceback
        traceback.print_exc()
        return None, None, False

async def check_player_in_clan(nickname: str) -> bool:
    """Проверяет наличие игрока в клане (старая функция для совместимости)"""
    _, _, is_in_clan = await get_player_info(nickname)
    return is_in_clan

async def check_player_by_id(player_id: str):
    """Проверяет игрока по player_id и возвращает актуальный ник и статус в клане"""
    try:
        headers = {
            "Authorization": f"Bearer {PUBG_API_KEY}",
            "Accept": "application/vnd.api+json"
        }
        
        # Получаем информацию об игроке по player_id
        url_player = f"https://api.pubg.com/shards/{PUBG_PLATFORM}/players/{player_id}"
        resp_player = requests.get(url_player, headers=headers, timeout=10)
        
        if resp_player.status_code != 200:
            print(f"❌ Ошибка при получении данных игрока по ID: {resp_player.status_code}")
            return None, False
        
        player_data = resp_player.json()
        
        if "data" not in player_data:
            return None, False
        
        attributes = player_data["data"].get("attributes", {})
        current_nickname = attributes.get("name", "")
        
        # Проверяем clanId прямо из attributes
        clan_id = attributes.get("clanId")
        is_in_clan = clan_id == CLAN_ID if clan_id else False
        
        return current_nickname, is_in_clan
        
    except requests.exceptions.Timeout:
        print(f"❌ Таймаут при проверке игрока по ID {player_id}")
        return None, False
    except Exception as e:
        print(f"❌ Ошибка при проверке игрока по ID {player_id}: {e}")
        return None, False

async def check_all_members_in_clan(guild: discord.Guild):
    """Проверяет всех участников с ролью клана и удаляет роль если игрока нет в клане"""
    try:
        role = guild.get_role(CLAN_ROLE_ID)
        if not role:
            print(f"❌ Роль с ID {CLAN_ROLE_ID} не найдена")
            return
        
        # Получаем всех зарегистрированных пользователей
        registrations = supabase.table("user_registrations").select("*").execute()
        
        if not registrations.data:
            print("ℹ️ Нет зарегистрированных пользователей для проверки")
            return
        
        checked_count = 0
        removed_count = 0
        
        total_registrations = len(registrations.data)
        
        for index, registration in enumerate(registrations.data):
            discord_id = registration.get("discord_id")
            player_id = registration.get("player_id")
            pubg_nickname = registration.get("pubg_nickname", "")
            verified = registration.get("verified", False)
            
            if not discord_id:
                continue
            
            # Пропускаем записи без player_id (не привязанные)
            if not player_id:
                continue
            
            try:
                member = guild.get_member(int(discord_id))
                if not member:
                    # Участник покинул сервер, удаляем запись
                    supabase.table("user_registrations").delete().eq("discord_id", discord_id).execute()
                    continue
                
                # Проверяем игрока по player_id (привязка по ID аккаунта в игре)
                current_nickname, is_in_clan = await check_player_by_id(player_id)
                
                if not current_nickname:
                    # Не удалось получить данные игрока
                    print(f"⚠️ Не удалось получить данные игрока с player_id {player_id}")
                    continue
                
                checked_count += 1
                has_role = role in member.roles
                
                if is_in_clan:
                    # Игрок в клане - выдаем роль если её нет
                    if not has_role:
                        await member.add_roles(role)
                        supabase.table("user_registrations").update({
                            "verified": True
                        }).eq("discord_id", discord_id).execute()
                        print(f"✅ Выдана роль пользователю {member.display_name} ({current_nickname})")
                    
                    # Проверяем, изменился ли ник в игре
                    registration_name = registration.get("name", "")
                    expected_nickname = f"{current_nickname} ({registration_name})"
                    
                    # Обновляем ник в базе если он изменился
                    if current_nickname != pubg_nickname:
                        supabase.table("user_registrations").update({
                            "pubg_nickname": current_nickname
                        }).eq("discord_id", discord_id).execute()
                        print(f"📝 Обновлен ник в базе для {member.display_name}: {pubg_nickname} -> {current_nickname}")
                    
                    # Обновляем никнейм в Discord только если он отличается от ожидаемого
                    if member.display_name != expected_nickname and member.nick != expected_nickname:
                        try:
                            await member.edit(nick=expected_nickname)
                            print(f"📝 Обновлен никнейм в Discord для {member.display_name}: {member.display_name} -> {expected_nickname}")
                        except Exception as e:
                            print(f"⚠️ Не удалось обновить никнейм пользователя {member.display_name}: {e}")
                else:
                    # Игрок не в клане - забираем роль если она есть
                    if has_role:
                        await member.remove_roles(role)
                        supabase.table("user_registrations").update({
                            "verified": False
                        }).eq("discord_id", discord_id).execute()
                        removed_count += 1
                        print(f"❌ Удалена роль у пользователя {member.display_name} ({current_nickname}) - игрок не найден в клане")
                
                # Добавляем задержку в 1 минуту между проверками участников (кроме последнего)
                if index < total_registrations - 1:
                    print(f"⏳ Ожидание 1 минуту перед проверкой следующего участника...")
                    await asyncio.sleep(60)  # 1 минута = 60 секунд
                
            except Exception as e:
                print(f"❌ Ошибка при проверке пользователя {discord_id}: {e}")
                continue
        
        print(f"📊 Проверка клана завершена: проверено {checked_count} пользователей, удалено ролей: {removed_count}")
        
    except Exception as e:
        print(f"❌ Ошибка при проверке участников клана: {e}")

