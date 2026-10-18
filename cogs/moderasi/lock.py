import discord
from discord.ext import commands

import config


class Lock(commands.Cog):
    def __init__(self, bot:commands.Bot):
        self.bot = bot
    
    @commands.hybrid_command(
        name="lock", 
        description="Ngekunci channel supaya role `@everyone` tidak bisa kirim pesan.",
        aliases=["lockdown"]
    )
    @commands.has_permissions(manage_channels=True)
    @commands.bot_has_permissions(manage_channels=True)
    async def lock(self, ctx:commands.Context):
        overwrite = ctx.channel.overwrites_for(ctx.guild.default_role)
        if overwrite.send_messages is False:
            await ctx.reply("Channel ini sudah dalam kondisi terkunci.", ephemeral=True)
            return
        
        overwrite.send_messages = False
        await ctx.channel.set_permissions(ctx.guild.default_role, overwrite=overwrite)
        
        container = discord.ui.Container(accent_color=config.pengaturan.warna_kuning)
        container.add_item(discord.ui.TextDisplay(content="### 🔒 Channel dikunci"))
        container.add_item(discord.ui.Separator(spacing=discord.SeparatorSpacing.small))
        container.add_item(discord.ui.TextDisplay(content="Akses kirim pesan untuk `@everyone` telah ditutup."))
        
        await ctx.reply(view=discord.ui.LayoutView().add_item(container))
    
    @lock.error
    async def lock_error(self, ctx:commands.Context, error:commands.CommandError):
        if isinstance(error, commands.MissingPermissions):
            await ctx.reply("Kamu tidak punya izin `Manage Channels` untuk menggunakan command ini.", ephemeral=True)
        elif isinstance(error, commands.BotMissingPermissions):
            await ctx.reply("Bot tidak punya izin `Manage Channels` untuk melakukan aksi ini.", ephemeral=True)


async def setup(bot:commands.Bot):
    await bot.add_cog(Lock(bot))