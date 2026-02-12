import discord
from discord.ui import View, Button, Modal, TextInput
import requests
from modules.config import PUBG_API_KEY, PUBG_PLATFORM, bot
from modules.database import supabase

CLAN_ID = "clan.bb296787b8e144959802df1ab9a594da"
CLAN_ROLE_ID = 1159121098965786634
REGISTRATION_CHANNEL_ID = 1183130293545222205

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
        
        # Получаем информацию об игроке по нику (player_id, актуальный ник, статус в клане)
        player_id, current_nickname, is_in_clan = await get_player_info(nickname)
        
        if not player_id:
            await interaction.followup.send(
                f"❌ Игрок с ником '{nickname}' не найден в PUBG. Проверьте правильность написания ника.",
                ephemeral=True
            )
            return
        
        # Проверяем, не привязан ли уже этот player_id к другому Discord аккаунту
        existing_user = supabase.table("user_registrations").select("*").eq("player_id", player_id).execute()
        if existing_user.data:
            existing_discord_id = existing_user.data[0].get("discord_id")
            if str(existing_discord_id) != str(interaction.user.id):
                existing_nickname = existing_user.data[0].get("pubg_nickname", nickname)
                await interaction.followup.send(
                    f"❌ Игрок с ником '{existing_nickname}' (player_id: {player_id}) уже привязан к другому аккаунту Discord!", 
                    ephemeral=True
                )
                return
        
        if is_in_clan:
            # Игрок в клане - привязываем player_id к discord_id
            actual_nickname = current_nickname if current_nickname else nickname
            
            # Выдаем роль
            role = interaction.guild.get_role(CLAN_ROLE_ID)
            if role:
                try:
                    await interaction.user.add_roles(role)
                except Exception as e:
                    await interaction.followup.send(
                        f"❌ Ошибка при выдаче роли: {e}", 
                        ephemeral=True
                    )
                    return
            
            # Меняем никнейм пользователя на формат "ник (имя)"
            new_nickname = f"{actual_nickname} ({name})"
            try:
                await interaction.user.edit(nick=new_nickname)
            except discord.Forbidden:
                await interaction.followup.send(
                    f"⚠️ Не удалось изменить никнейм (нет прав). Пожалуйста, измените его вручную на: {new_nickname}",
                    ephemeral=True
                )
            except Exception as e:
                print(f"❌ Ошибка при изменении никнейма: {e}")
            
            # Сохраняем данные в базу - привязываем player_id к discord_id
            try:
                supabase.table("user_registrations").upsert({
                    "discord_id": interaction.user.id,
                    "player_id": player_id,
                    "pubg_nickname": actual_nickname,
                    "name": name,
                    "pubg_plus": pubg_plus == "да",
                    "verified": True
                }).execute()
                
                await interaction.followup.send(
                    f"✅ Регистрация успешна! Игрок привязан к вашему аккаунту. Вам выдана роль клана. Никнейм изменен на: {new_nickname}. Добро пожаловать, {name}!",
                    ephemeral=True
                )
            except Exception as e:
                await interaction.followup.send(
                    f"❌ Ошибка при сохранении данных: {e}",
                    ephemeral=True
                )
        else:
            # Игрок НЕ в клане - НЕ привязываем player_id, НЕ меняем никнейм
            await interaction.followup.send(
                f"❌ Игрок с ником '{nickname}' не состоит в клане. Привязка не выполнена. Если вы только что вступили в клан, подождите несколько минут и попробуйте снова.",
                ephemeral=True
            )

class RegistrationView(View):
    def __init__(self):
        super().__init__(timeout=None)
    
    async def on_error(self, interaction: discord.Interaction, error: Exception, item):
        print(f"❌ Ошибка в RegistrationView: {error}")
        try:
            await interaction.response.send_message(
                "❌ Произошла ошибка при обработке запроса. Попробуйте позже.",
                ephemeral=True
            )
        except:
            pass
    
    @discord.ui.button(label="Логин", style=discord.ButtonStyle.primary, emoji="🔐")
    async def login_button(self, interaction: discord.Interaction, button: Button):
        modal = RegistrationModal()
        await interaction.response.send_modal(modal)

async def get_player_info(nickname: str):
    """Получает информацию об игроке по нику. Возвращает (player_id, current_nickname, is_in_clan)"""
    try:
        headers = {
            "Authorization": f"Bearer {PUBG_API_KEY}",
            "Accept": "application/vnd.api+json"
        }
        
        # Получаем player_id по нику
        url_player = f"https://api.pubg.com/shards/{PUBG_PLATFORM}/players?filter[playerNames]={nickname}"
        resp_player = requests.get(url_player, headers=headers, timeout=10)
        
        if resp_player.status_code != 200:
            print(f"❌ Ошибка при получении данных игрока: {resp_player.status_code}")
            return None, None, False
        
        player_data = resp_player.json()
        
        if "data" not in player_data or not player_data["data"]:
            return None, None, False
        
        player_info = player_data["data"][0]
        player_id = player_info["id"]
        attributes = player_info.get("attributes", {})
        current_nickname = attributes.get("name", nickname)
        
        # Проверяем clanId прямо из attributes
        clan_id = attributes.get("clanId")
        is_in_clan = clan_id == CLAN_ID if clan_id else False
        
        return player_id, current_nickname, is_in_clan
        
    except requests.exceptions.Timeout:
        print(f"❌ Таймаут при проверке клана для игрока {nickname}")
        return None, None, False
    except Exception as e:
        print(f"❌ Ошибка при проверке клана для игрока {nickname}: {e}")
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
        
        for registration in registrations.data:
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
                
            except Exception as e:
                print(f"❌ Ошибка при проверке пользователя {discord_id}: {e}")
                continue
        
        print(f"📊 Проверка клана завершена: проверено {checked_count} пользователей, удалено ролей: {removed_count}")
        
    except Exception as e:
        print(f"❌ Ошибка при проверке участников клана: {e}")

