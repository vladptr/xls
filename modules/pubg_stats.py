import discord
import requests
import re
from PIL import Image, ImageDraw, ImageFont, ImageOps
from io import BytesIO
from modules.config import PUBG_API_KEY, PUBG_PLATFORM, bot
from modules.database import supabase
from modules.leveling import calculate_level_from_exp

def get_rank_info(rating):
    ranks = [
        ("bronze", 0, 1399),
        ("silver", 1400, 1799),
        ("gold", 1800, 2199),
        ("platinum", 2200, 2599),
        ("crystal", 2600, 2999),
        ("diamond", 3000, 3399),
        ("master", 3400, float('inf')),
    ]
    for rank, low, high in ranks:
        if low <= rating <= high:
            return rank, low, high
    return "master", 3400, 3400  # default to master если выше 3400

async def stat(ctx, member: discord.Member = None):
    try:
        member = member or ctx.author
        user_id = member.id
        
        raw_name = member.display_name
        pubg_name = re.split(r"[ \(\{\[]", raw_name, 1)[0].strip()
        print(f"PUBG поиск ника: {pubg_name}")

        headers = {
            "Authorization": f"Bearer {PUBG_API_KEY}",
            "Accept": "application/vnd.api+json"
        }

        # Получаем player_id по имени
        url_player = f"https://api.pubg.com/shards/{PUBG_PLATFORM}/players?filter[playerNames]={pubg_name}"
        resp_player = requests.get(url_player, headers=headers).json()

        player_id = None
        if "data" in resp_player and resp_player["data"]:
            player_id = resp_player["data"][0]["id"]
        else:
            await ctx.send(f"Игрок с ником {pubg_name} не найден.")
            return

        # Получаем текущий сезон
        url_seasons = f"https://api.pubg.com/shards/{PUBG_PLATFORM}/seasons"
        resp_seasons = requests.get(url_seasons, headers=headers).json()
        seasons = resp_seasons.get("data", [])
        current = next((s for s in seasons if s["attributes"].get("isCurrentSeason")), None)
        season_id = current["id"] if current else None

        if not season_id:
            await ctx.send("Не удалось получить текущий сезон PUBG.")
            return

        # Получаем рейтинговую статистику
        url_ranked_stats = f"https://api.pubg.com/shards/{PUBG_PLATFORM}/players/{player_id}/seasons/{season_id}/ranked"
        resp_ranked = requests.get(url_ranked_stats, headers=headers).json()

        ranked_stats = resp_ranked.get("data", {}).get("attributes", {}).get("rankedGameModeStats", {})
        squad_ranked = ranked_stats.get("squad-fpp", {})
        
        current_rank_point = squad_ranked.get("currentRankPoint", 0)
        rounds_played = squad_ranked.get("roundsPlayed", 0)
        damage_dealt = squad_ranked.get("damageDealt", 0)
        kda = squad_ranked.get("kda", 0)
    
        average_damage = damage_dealt / max(rounds_played, 1)
        # Обычная статистика
        url_season_stats = f"https://api.pubg.com/shards/{PUBG_PLATFORM}/players/{player_id}/seasons/{season_id}"
        resp_season_stats = requests.get(url_season_stats, headers=headers).json()

        game_mode_stats = resp_season_stats.get("data", {}).get("attributes", {}).get("gameModeStats", {})
        squad_stats = game_mode_stats.get("squad-fpp", {})

        # Определяем ранг
        rank_thresholds = [
            ("bronze", 0, 1400),
            ("silver", 1400, 1799),
            ("gold", 1800, 2199),
            ("platinum", 2200, 2599),
            ("crystal", 2600, 2999),
            ("diamond", 3000, 3399),
            ("master", 3400, 10000),
        ]

        rank_name = "bronze"
        low, high = 0, 1400
        for rname, rlow, rhigh in rank_thresholds:
            if rlow <= current_rank_point <= rhigh:
                rank_name = rname
                low, high = rlow, rhigh
                break
        else:
            if current_rank_point > 3400:
                rank_name = "master"
                low, high = 3400, 10000

        # Текст с текущими очками рейтинга
        score_text = f"{current_rank_point}/{high}" if rank_name != "master" else f"{current_rank_point}+"
                
        # Получение данных из Supabase
        row = supabase.table("user_levels").select("*").eq("user_id", user_id).limit(1).execute()
        stats = row.data[0] if row.data else {"exp": 0, "level": 1}
        level = stats["level"]
        exp = stats["exp"]

        time_row = supabase.table("voice_time").select("total_seconds_all_time").eq("user_id", user_id).limit(1).execute()
        if time_row.data and time_row.data[0].get("total_seconds_all_time") is not None:
            total_seconds_all_time = int(time_row.data[0].get("total_seconds_all_time", 0))
        else:
            total_seconds_all_time = 0

        total_hours = total_seconds_all_time / 3600.0

        # Получаем все недели пользователя для правильного расчета среднего
        weeks_rows = supabase.table("weekly_voice_stats").select("cycle_number,week_number,total_seconds").eq("user_id", user_id).order("cycle_number").order("week_number").execute()
        
        if not weeks_rows.data:
            avg_hours = 0.0
        else:
            # Суммируем все секунды из истории недель
            total_seconds_in_history = sum([week.get("total_seconds", 0) for week in weeks_rows.data])
            
            # Количество недель = количество записей (включая недели с 0 часов)
            weeks_count = len(weeks_rows.data)
            
            # Среднее время = сумма всех недель / количество недель
            avg_hours = (total_seconds_in_history / 3600.0) / weeks_count if weeks_count > 0 else 0.0
            
            # Находим первую неделю пользователя (для отображения)
            first_week = weeks_rows.data[0]
            first_cycle = first_week.get("cycle_number", 0)
            first_week_num = first_week.get("week_number", 0)
            
            # Находим текущую неделю (последнюю запись) для отображения
            last_week = weeks_rows.data[-1]
            current_cycle = last_week.get("cycle_number", 0)
            current_week_num = last_week.get("week_number", 0)
            
            # avg_hours уже рассчитан выше правильно:
            # сумма всех недель (включая 0 часов) / количество записей недель
            # Это учитывает все недели с момента первой активности пользователя
         
        # Выбор фона по уровню
        if level <= 5:
            background_path = "1-5.png"
        elif level <= 10:
            background_path = "5-10.png"
        elif level <= 25:
            background_path = "10-25.png"
        else:
            background_path = "25+.png"

        img = Image.open(background_path).convert("RGBA")
        draw = ImageDraw.Draw(img)
        width, height = img.size

        # Шрифты
        font_path = "FluffyFont.otf"
        name_font = ImageFont.truetype(font_path, 24)
        small_font = ImageFont.truetype(font_path, 16)

        # Аватар
        avatar_asset = member.avatar or member.display_avatar
        avatar_bytes = await avatar_asset.read()
        avatar = Image.open(BytesIO(avatar_bytes)).convert("RGBA")

        avatar_size = int(160 * 0.6)  # уменьшение на 20%
        avatar = avatar.resize((avatar_size, avatar_size))
        avatar = ImageOps.fit(avatar, avatar.size, centering=(0.5, 0.5))

        avatar_width, avatar_height = avatar.size
        
        mask = Image.new("L", avatar.size, 0)
        draw_mask = ImageDraw.Draw(mask)
        draw_mask.ellipse((0, 0, avatar.size[0], avatar.size[1]), fill=255)
        avatar.putalpha(mask)

        avatar_x = 50
        avatar_y = height // 2 - (avatar_size // 2)
        img.paste(avatar, (avatar_x, avatar_y), avatar)

        level, exp_in_level, next_level_exp = calculate_level_from_exp(exp)
        progress = exp_in_level / next_level_exp if next_level_exp > 0 else 1.0

        radius_level = avatar_size // 2 + 10
        thickness_level = 6
        center_level = (avatar_x + avatar_size // 2, avatar_y + avatar_size // 2)

        draw.ellipse(
            (center_level[0] - radius_level, center_level[1] - radius_level,
             center_level[0] + radius_level, center_level[1] + radius_level),
            outline=(80, 80, 80),
            width=thickness_level
        )

        start_angle = -90
        end_angle = start_angle + int(360 * progress)

        draw.arc(
            (center_level[0] - radius_level, center_level[1] - radius_level,
             center_level[0] + radius_level, center_level[1] + radius_level),
            start=start_angle,
            end=end_angle,
            fill=(0, 191, 255),  # цвет прогресса уровня (голубой)
            width=thickness_level
        )
        
        level_text = f"({exp_in_level}/{next_level_exp})"
        level_font = ImageFont.truetype(font_path, 16)
        bbox = draw.textbbox((0, 0), level_text, font=level_font)
        text_width = bbox[2] - bbox[0]
        text_x = center_level[0] - text_width // 2
        text_y = avatar_y + avatar_size + 10
        draw.text((text_x, text_y), level_text, font=level_font, fill="white", stroke_width=1, stroke_fill="black")
        # Ник пользователя по центру (можно поправить позиционирование, если нужно)
        center_x = width // 2
        center_y = height // 2
        name_bbox = draw.textbbox((0, 0), member.display_name, font=name_font)
        name_width = name_bbox[2] - name_bbox[0]
        name_height = name_bbox[3] - name_bbox[1]
        draw.text(
            (center_x - name_width // 2, center_y - name_height // 2),
            member.display_name,
            font=name_font,
            fill="white",
            stroke_width=1,
            stroke_fill="black"
        )

        # Статистика слева от аватара (с отступом 40 пикселей справа от аватара)
        stats_left_x = avatar_x + avatar_size + 40
        stats_left_y = avatar_y
        line_height = 22

        normal_squad_damage = squad_stats.get("damageDealt", 0)
        normal_squad_rounds = squad_stats.get("roundsPlayed", 1)
        normal_squad_avg_damage = normal_squad_damage / max(normal_squad_rounds, 1)
        print(f"Damage: {normal_squad_damage}, Rounds: {normal_squad_rounds}")
        
        stats_left_lines = [
            f"ADR public FPP: {normal_squad_avg_damage:.1f}",
            f"Среднее время: {avg_hours:.1f} ч.",
            f"Общее время: {total_hours:.1f} ч.",
            f"Уровень: {level}",
        ]

        for i, line in enumerate(stats_left_lines):
            y = stats_left_y + i * line_height
            draw.text((stats_left_x, y), line, font=small_font, fill="white", stroke_width=1, stroke_fill="black")

        # --- Иконка ранга справа ---
        rank_img_path = f"ranks/{rank_name}.png"
        rank_img = Image.open(rank_img_path).convert("RGBA")
        original_size = 120
        scale = 1  # 80%
        rank_img_size = int(original_size * scale)
        rank_img = rank_img.resize((rank_img_size, rank_img_size))

        mask_rank = Image.new("L", (rank_img_size, rank_img_size), 0)
        mask_draw = ImageDraw.Draw(mask_rank)
        mask_draw.ellipse((0, 0, rank_img_size, rank_img_size), fill=255)
        rank_img.putalpha(mask_rank)

        rank_x = width - 20 - rank_img_size
        rank_y = height // 2 - (rank_img_size // 2)
        img.paste(rank_img, (rank_x, rank_y), rank_img)

        # Рисуем прогресс бар рейтинга вокруг иконки ранга
        progress = 1.0 if rank_name == "master" else max(0.0, min((current_rank_point - low) / (high - low), 1.0))

        # Статистика рейтингового режима слева от иконки ранга (с отступом 40 пикселей)
        stats_right_x = rank_x - 300
        stats_right_y = rank_y - 10

        duo_ranked = ranked_stats.get("duo-fpp", {})
        squad_ranked = ranked_stats.get("squad-fpp", {})

        duo_kills = duo_ranked.get("kills", 0)
        duo_rounds = duo_ranked.get("roundsPlayed", 1)
        duo_avg_kills = duo_kills / max(duo_rounds, 1)
        duo_damage = duo_ranked.get("damageDealt", 0)
        duo_avg_damage = duo_damage / max(duo_rounds, 1)

        squad_kills = squad_ranked.get("kills", 0)
        squad_rounds = squad_ranked.get("roundsPlayed", 1)
        squad_avg_kills = squad_kills / max(squad_rounds, 1)
        squad_damage = squad_ranked.get("damageDealt", 0)
        squad_avg_damage = squad_damage / max(squad_rounds, 1)

        line_height = 22
        stats_right_lines = [
            f"Ranked:",
            f"Squad FPP:",
            f"  Убийств в среднем (KDA): {kda:.2f}",
            f"  ADR ranked FPP: {average_damage:.1f}",
            f"Duo FPP:",
            f"  Убийств в среднем (KDA): {duo_avg_kills:.2f}",
            f"  ADR ranked FPP: {duo_avg_damage:.1f}",
        ]

        for i, line in enumerate(stats_right_lines):
            y = stats_right_y + i * line_height
            draw.text((stats_right_x, y), line, font=small_font, fill="white", stroke_width=1, stroke_fill="black")

        # Прогресс бар вокруг ранга
        radius_rank = int((rank_img_size // 2 + 10)*0.8)
        thickness_rank = 6
        center_rank = (rank_x + rank_img_size // 2, rank_y + rank_img_size // 2)

        max_angle = 399  # фиксированная длина шкалы в градусах
        start_angle = -90
        progress = (current_rank_point - low) / (high - low) if high > low else 1.0
        progress = max(0.0, min(progress, 1.0))  # ограничиваем от 0 до 1
        end_angle = start_angle + int(max_angle * progress)
        
        draw.ellipse(
            (center_rank[0] - radius_rank, center_rank[1] - radius_rank,
             center_rank[0] + radius_rank, center_rank[1] + radius_rank),
            outline=(80, 80, 80),
            width=thickness_rank
        )
        
        draw.arc(
            (center_rank[0] - radius_rank, center_rank[1] - radius_rank,
             center_rank[0] + radius_rank, center_rank[1] + radius_rank),
            start=start_angle,
            end=end_angle,
            fill=(255, 215, 0),
            width=thickness_rank
        )

        score_text = f"{current_rank_point}/{high}" if rank_name != "master" else f"{current_rank_point}+"
        score_font = ImageFont.truetype(font_path, 18)
        bbox = draw.textbbox((0, 0), score_text, font=score_font)
        text_width = bbox[2] - bbox[0]
        text_x = center_rank[0] - text_width // 2
        text_y = rank_y + rank_img_size - 5
        draw.text((text_x, text_y), score_text, font=score_font, fill="white", stroke_width=1, stroke_fill="black")

        filename = f"stat_{user_id}.png"
        img.save(filename)
        stat_msg = await ctx.send(file=discord.File(filename))
        return stat_msg
        
    except Exception as e:
        await ctx.send(f"Ошибка в команде stat: {e}")

