import requests
from discord.ext import commands

PUBG_API_KEY = "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9.eyJqdGkiOiJjZmMyNDMyMC01NzZlLTAxM2UtMjAyNS0yYTI4ZjY0MjU0ZDEiLCJpc3MiOiJnYW1lbG9ja2VyIiwiaWF0IjoxNzU0NzU4MTk5LCJwdWIiOiJibHVlaG9sZSIsInRpdGxlIjoicHViZyIsImFwcCI6InhsczIifQ.C74qapztROZBtCVEWdob2w4B0-omdLJ-aaBfdfFK91E"
PUBG_PLATFORM = "steam"

headers = {
    "Authorization": f"Bearer {PUBG_API_KEY}",
    "Accept": "application/vnd.api+json"
}

async def setup(bot: commands.Bot):
    @bot.command(name="check")
    async def check(ctx, nickname: str):
        
        try:
            url_player = (
                f"https://api.pubg.com/shards/{PUBG_PLATFORM}"
                f"/players?filter[playerNames]={nickname}"
            )
            resp = requests.get(url_player, headers=headers)

            if resp.status_code != 200:
                await ctx.send("❌ Ошибка запроса к PUBG API")
                return

            data = resp.json().get("data", [])
            if not data:
                await ctx.send("❌ Игрок не найден")
                return

            player = data[0]
            player_id = player["id"]

            relationships = player.get("relationships", {})
            clan_data = relationships.get("clan", {}).get("data")

            if clan_data:
                clan_id = clan_data["id"]
                await ctx.send(
                    f"👤 **{nickname}**\n"
                    f"🏷️ Clan ID: `{clan_id}`"
                )
            else:
                await ctx.send(
                    f"👤 **{nickname}**\n"
                    f"❌ Игрок не состоит в клане"
                )

        except Exception as e:
            await ctx.send("❌ Ошибка при выполнении команды")
            print("CHECK ERROR:", e)
