import aiohttp
from discord.ext import commands

PUBG_API_KEY = "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9.eyJqdGkiOiJjZmMyNDMyMC01NzZlLTAxM2UtMjAyNS0yYTI4ZjY0MjU0ZDEiLCJpc3MiOiJnYW1lbG9ja2VyIiwiaWF0IjoxNzU0NzU4MTk5LCJwdWIiOiJibHVlaG9sZSIsInRpdGxlIjoicHViZyIsImFwcCI6InhsczIifQ.C74qapztROZBtCVEWdob2w4B0-omdLJ-aaBfdfFK91E"
PUBG_PLATFORM = "steam"

HEADERS = {
    "Authorization": f"Bearer {PUBG_API_KEY}",
    "Accept": "application/vnd.api+json"
}

async def setup(bot: commands.Bot):

    @bot.command(name="check")
    async def check(ctx, *, nickname: str):
        try:
            # 1️⃣ Получаем игрока
            url_player = (
                f"https://api.pubg.com/shards/{PUBG_PLATFORM}"
                f"/players?filter[playerNames]={nickname}"
            )
            r_player = requests.get(url_player, headers=HEADERS)

            if r_player.status_code != 200:
                await ctx.send("❌ Ошибка запроса к PUBG API")
                return

            players = r_player.json().get("data", [])
            if not players:
                await ctx.send("❌ Игрок не найден")
                return

            player_id = players[0]["id"]

            # 2️⃣ Получаем клан по player_id
            url_clan = (
                f"https://api.pubg.com/shards/{PUBG_PLATFORM}"
                f"/clans?filter[playerIds]={player_id}"
            )
            r_clan = requests.get(url_clan, headers=HEADERS)

            clans = r_clan.json().get("data", [])

            if not clans:
                await ctx.send(
                    f"👤 **{nickname}**\n"
                    f"❌ Игрок не состоит в клане"
                )
                return

            clan = clans[0]
            clan_id = clan["id"]
            clan_name = clan["attributes"]["name"]
            clan_tag = clan["attributes"].get("tag", "—")

            await ctx.send(
                f"👤 **{nickname}**\n"
                f"🏷️ Clan: **{clan_name}** [{clan_tag}]\n"
                f"🆔 Clan ID: `{clan_id}`"
            )

        except Exception as e:
            print("CHECK ERROR:", e)
            await ctx.send("❌ Ошибка при выполнении команды")
