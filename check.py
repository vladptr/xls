import aiohttp
import requests
import json
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
            url = (
                f"https://api.pubg.com/shards/{PUBG_PLATFORM}"
                f"/players?filter[playerNames]={nickname}"
            )

            resp = requests.get(url, headers=HEADERS)

            if resp.status_code != 200:
                await ctx.send(f"❌ PUBG API error: {resp.status_code}")
                return

            data = resp.json()

            if not data.get("data"):
                await ctx.send("❌ Игрок не найден")
                return

            player = data["data"][0]

            # красиво форматируем JSON
            pretty = json.dumps(player, indent=2, ensure_ascii=False)

            # Discord лимит 2000 символов
            if len(pretty) > 1900:
                pretty = pretty[:1900] + "\n... (truncated)"

            await ctx.send(
                f"👤 **{nickname}**\n"
                f"```json\n{pretty}\n```"
            )

        except Exception as e:
            print("CHECK ERROR:", e)
            await ctx.send("❌ Ошибка при выполнении команды")

