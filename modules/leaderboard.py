import discord
from discord.ui import View, Button
import math
import asyncio
from modules.database import supabase
from modules.config import bot

class LeaderboardView(View):
    def __init__(self, data, ctx):
        super().__init__(timeout=60)
        self.data = data
        self.ctx = ctx
        self.page = 0
        self.items_per_page = 10
        self.max_page = math.ceil(len(data) / self.items_per_page) - 1

        self.prev_button = Button(label="⬅️ Назад", style=discord.ButtonStyle.primary)
        self.next_button = Button(label="➡️ Вперед", style=discord.ButtonStyle.primary)
        self.prev_button.callback = self.prev_page
        self.next_button.callback = self.next_page
        self.add_item(self.prev_button)
        self.add_item(self.next_button)

    async def prev_page(self, interaction):
        if interaction.user != self.ctx.author:
            await interaction.response.send_message("Это меню не для тебя!", ephemeral=True)
            return
        if self.page > 0:
            self.page -= 1
            await self.update_message(interaction)

    async def next_page(self, interaction):
        if interaction.user != self.ctx.author:
            await interaction.response.send_message("Это меню не для тебя!", ephemeral=True)
            return
        if self.page < self.max_page:
            self.page += 1
            await self.update_message(interaction)

    async def update_message(self, interaction):
        embed = await self.generate_embed()
        await interaction.response.edit_message(embed=embed, view=self)

    async def generate_embed(self):
        start = self.page * self.items_per_page
        end = start + self.items_per_page
        page_data = self.data[start:end]

        embed = discord.Embed(
            title=f"🏆 Топ по времени в голосовых (Страница {self.page + 1}/{self.max_page + 1})",
            color=discord.Color.gold()
        )

        for i, row in enumerate(page_data, start=start + 1):
            user_id = row['user_id']
            total_seconds = row['total_seconds']
            member = self.ctx.guild.get_member(user_id)
            if member is None:
                try:
                    member = await self.ctx.guild.fetch_member(user_id)
                except discord.NotFound:
                    member = None

            name = member.display_name if member else f"User {user_id}"
            hours, remainder = divmod(total_seconds, 3600)
            minutes, seconds = divmod(remainder, 60)
            embed.add_field(name=f"{i}. {name}", value=f"{hours}ч {minutes}м {seconds}с", inline=False)

        return embed

async def leaderboard(ctx):
    try:
        response = supabase.table("voice_time")\
            .select("user_id,total_seconds")\
            .order("total_seconds", desc=True)\
            .limit(50)\
            .execute()
        data = response.data

        if not data:
            await ctx.send("Нет данных по времени в голосовых!")
            return

        view = LeaderboardView(data, ctx)
        embed = await view.generate_embed()
        message = await ctx.send(embed=embed, view=view)
        
        await asyncio.sleep(300)
        await message.delete()
        try:
            await ctx.message.delete()
        except discord.errors.Forbidden:
            pass

    except Exception as e:
        print(f"Ошибка при получении таблицы лидеров: {e}")
        await ctx.send("Произошла ошибка при получении таблицы лидеров.")

