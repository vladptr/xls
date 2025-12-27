import aiohttp
import requests
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
            player_url = (
                f"https://api.pubg.com/shards/{PUBG_PLATFORM}"
                f"/players?filter[playerNames]={nickname}"
            )
            player_resp = requests.get(player_url, headers=HEADERS)

            if player_resp.status_code != 200:
                await ctx.send("❌ Ошибка PUBG API (player)")
                return

            players = player_resp.json().get("data", [])
            if not players:
                await ctx.send("❌ Игрок не найден")
                return

            player_id = players[0]["id"]

            # 2️⃣ Получаем клан
            clan_url = (
                f"https://api.pubg.com/shards/{PUBG_PLATFORM}"
                f"/clans?filter[playerIds]={player_id}"
            )
            clan_resp = requests.get(clan_url, headers=HEADERS)

            if clan_resp.status_code != 200:
                await ctx.send("❌ Ошибка PUBG API (clan)")
                return

            clans = clan_resp.json().get("data", [])

            if not clans:
                await ctx.send(f"👤 **{nickname}**\n❌ Игрок не состоит в клане")
                return

            clan_id = clans[0]["id"]

            await ctx.send(
                f"👤 **{nickname}**\n"
                f"🏷️ Clan ID: `{clan_id}`"
            )

        except Exception as e:
            print("CHECK ERROR:", e)
            await ctx.send("❌ Ошибка при выполнении команды")
