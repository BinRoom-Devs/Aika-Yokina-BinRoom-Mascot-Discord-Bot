import discord
from discord.ext import commands

import config


class Slowmode(commands.Cog):
    def __init__(self, bot:commands.Bot):
        self.bot = bot

    @commands.hybrid_command(name="slowmode", description="Atur jeda waktu slowmode channel saat ini (0 untuk mematikan).")
    @commands.has_permissions(manage_channels=True)
    @commands.bot_has_permissions(manage_channels=True)
    async def slowmode(self, ctx: commands.Context, seconds: int):
        if seconds < 0 or seconds > 21600:
            await ctx.send("Durasi slowmode harus antara 0 hingga 21600 detik (6 jam).", ephemeral=True)
            return
        
        await ctx.channel.edit(slowmode_delay=seconds)
        
        status = "dimatikan" if seconds == 0 else f"diatur ke **{seconds} detik**"
        container = discord.ui.Container(accent_color=config.pengaturan.warna_kuning)
        container.add_item(discord.ui.TextDisplay(content="### ⏳ Mode lambat"))
        container.add_item(discord.ui.Separator(spacing=discord.SeparatorSpacing.small))
        container.add_item(discord.ui.TextDisplay(content=f"Slowmode channel ini telah {status}."))
        
        await ctx.send(view=discord.ui.LayoutView().add_item(container))
    
    @slowmode.error
    async def slowmode_error(self, ctx:commands.Context, error:commands.CommandError):
        if isinstance(error, commands.MissingPermissions):
            await ctx.send("Kamu tidak punya izin `Manage Channels` untuk menggunakan command ini.", ephemeral=True)
        elif isinstance(error, commands.BotMissingPermissions):
            await ctx.send("Bot tidak punya izin `Manage Channels` untuk melakukan aksi ini.", ephemeral=True)
        elif isinstance(error, commands.MissingRequiredArgument):
            await ctx.send("Tentukan durasi slowmode dalam detik (contoh: `/slowmode 5`).", ephemeral=True)


async def setup(bot: commands.Bot):
    await bot.add_cog(Slowmode(bot))