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
        url = (
            f"https://api.pubg.com/shards/{PUBG_PLATFORM}"
            f"/players?filter[playerNames]={nickname}"
        )

        async with aiohttp.ClientSession(headers=HEADERS) as session:
            async with session.get(url) as resp:

                if resp.status != 200:
                    await ctx.send("❌ Ошибка запроса к PUBG API")
                    return

                data = (await resp.json()).get("data", [])

                if not data:
                    await ctx.send("❌ Игрок не найден")
                    return

                player = data[0]
                clan = (
                    player
                    .get("relationships", {})
                    .get("clan", {})
                    .get("data")
                )

                if clan:
                    await ctx.send(
                        f"👤 **{nickname}**\n"
                        f"🏷️ Clan ID: `{clan['id']}`"
                    )
                else:
                    await ctx.send(
                        f"👤 **{nickname}**\n"
                        f"❌ Игрок не состоит в клане"
                    )
