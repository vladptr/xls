from discord.ext import commands

async def setup(bot: commands.Bot):

    @bot.command()
    async def check(ctx):
        await ctx.send("1")

