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
    async def check(ctx, *, nickname: str):
        print("CHECK COMMAND CALLED:", nickname)

        try:
            url = (
                f"https://api.pubg.com/shards/{PUBG_PLATFORM}"
                f"/players?filter[playerNames]={nickname}"
            )

            resp = requests.get(url, headers=headers)
            print("STATUS:", resp.status_code)

            if resp.status_code != 200:
                await ctx.send("❌ PUBG API error")
                return

            data = resp.json().get("data", [])
            if not data:
                await ctx.send("❌ Игрок не найден")
                return

            clan = data[0].get("relationships", {}).get("clan", {}).get("data")

            if clan:
                await ctx.send(f"👤 **{nickname}**\n🏷️ Clan ID: `{clan['id']}`")
            else:
                await ctx.send(f"👤 **{nickname}**\n❌ Не в клане")

        except Exception as e:
            print("CHECK ERROR:", e)
            await ctx.send("❌ Ошибка")
