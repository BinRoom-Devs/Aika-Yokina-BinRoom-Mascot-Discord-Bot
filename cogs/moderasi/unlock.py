import discord
from discord.ext import commands

import config


class Unlock(commands.Cog):
    def __init__(self, bot:commands.Bot):
        self.bot = bot
    
    @commands.hybrid_command(name="unlock", description="Ngebuka kembali channel yang dikunci.")
    @commands.has_permissions(manage_channels=True)
    @commands.bot_has_permissions(manage_channels=True)
    async def unlock(self, ctx:commands.Context):
        overwrite = ctx.channel.overwrites_for(ctx.guild.default_role)
        if overwrite.send_messages is True or overwrite.send_messages is None:
            await ctx.send("Channel ini tidak dalam kondisi terkunci.", ephemeral=True)
            return
        
        overwrite.send_messages = None
        await ctx.channel.set_permissions(ctx.guild.default_role, overwrite=overwrite)
        
        container = discord.ui.Container(accent_color=config.pengaturan.warna_hijau)
        container.add_item(discord.ui.TextDisplay(content="### 🔓 Channel dibuka kembali"))
        container.add_item(discord.ui.Separator(spacing=discord.SeparatorSpacing.small))
        container.add_item(discord.ui.TextDisplay(content="Akses kirim pesan untuk `@everyone` telah dipulihkan."))
        
        await ctx.send(view=discord.ui.LayoutView().add_item(container))
    
    @unlock.error
    async def unlock_error(self, ctx:commands.Context, error:commands.CommandError):
        if isinstance(error, commands.MissingPermissions):
            await ctx.send("Kamu tidak punya izin `Manage Channels` untuk menggunakan command ini.", ephemeral=True)
        elif isinstance(error, commands.BotMissingPermissions):
            await ctx.send("Bot tidak punya izin `Manage Channels` untuk melakukan aksi ini.", ephemeral=True)


async def setup(bot:commands.Bot):
    await bot.add_cog(Unlock(bot))