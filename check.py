from discord.ext import commands

async def setup(bot: commands.Bot):

    @bot.command(name="check")
    async def check(ctx):
        await ctx.send("1")
