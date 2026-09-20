import datetime

import discord
from discord.ext import commands


class Uptime(commands.Cog):
    def __init__(self, bot:commands.Bot):
        self.bot = bot
        self.start_time = datetime.datetime.now(datetime.timezone.utc)

    def format_stopwatch(self, delta:datetime.timedelta) -> str:
        hari = delta.days
        jam, remainder = divmod(delta.seconds,3600)
        menit, detik = divmod(remainder,60)
        
        if hari > 0:
            return f"{hari}:{jam:02d}:{menit:02d}:{detik:02d}"
        elif jam >= 10:
            return f"{jam:02d}:{menit:02d}:{detik:02d}"
        elif jam > 0:
            return f"{jam}:{menit:02d}:{detik:02d}"
        else:
            return f"{menit:02d}:{detik:02d}"
    
    @commands.hybrid_command(name="uptime", description="Menampilkan waktu aktif Aika.")
    async def uptime(self, ctx:commands.Context):
        now = datetime.datetime.now(datetime.timezone.utc)
        delta = now - self.start_time
        
        waktu_aktif = self.format_stopwatch(delta)
        timestamp_awal = int(self.start_time.timestamp())
        
        container = discord.ui.Container(accent_color=0xD675C1)
        container.add_item(discord.ui.TextDisplay(
            content=("**⏲️ Waktu Aktif Aika**\n"
                     f"# {waktu_aktif}")
        ))
        container.add_item(discord.ui.Separator(spacing=discord.SeparatorSpacing.small))
        container.add_item(discord.ui.TextDisplay(
            content=f"-# Terakhir restart: <t:{timestamp_awal}:D> <t:{timestamp_awal}:T>")
        )
        
        await ctx.send(view=discord.ui.LayoutView().add_item(container))


async def setup(bot:commands.Bot):
    await bot.add_cog(Uptime(bot))