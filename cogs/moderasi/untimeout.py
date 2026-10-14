import discord
from discord.ext import commands

import config


class Untimeout(commands.Cog):
    def __init__(self, bot:commands.Bot):
        self.bot = bot
    
    @commands.hybrid_command(name="untimeout", aliases=["unmute"], description="Ngelepas pembungkaman (timeout) member.")
    @commands.has_permissions(moderate_members=True)
    @commands.bot_has_permissions(moderate_members=True)
    async def untimeout(
        self,
        ctx: commands.Context,
        member: discord.Member,
        *,
        reason: str | None = "*Tanpa alasan.*"
    ):
        if not member.is_timed_out():
            await ctx.send("Member ini lagi nggak di-timeout.", ephemeral=True)
            return
        
        await member.timeout(None, reason=reason)
        
        container = discord.ui.Container(accent_color=config.pengaturan.warna_hijau)
        container.add_item(discord.ui.TextDisplay(content=f"### 🔊 Timeout {member.mention} telah dicabut"))
        container.add_item(discord.ui.Separator(spacing=discord.SeparatorSpacing.small))
        container.add_item(discord.ui.TextDisplay(content=f"Alasan: {reason}"))
        
        await ctx.send(
            view=discord.ui.LayoutView().add_item(container),
            allowed_mentions=discord.AllowedMentions.none()
        )
    
    @untimeout.error
    async def untimeout_error(self, ctx:commands.Context, error:commands.CommandError):
        if isinstance(error, commands.MissingPermissions):
            await ctx.send("Kamu tidak punya izin `Moderate Members` untuk menggunakan command ini.", ephemeral=True)
        elif isinstance(error, commands.BotMissingPermissions):
            await ctx.send("Bot tidak punya izin `Moderate Members` untuk melakukan aksi ini.", ephemeral=True)
        elif isinstance(error, commands.MissingRequiredArgument):
            await ctx.send("Tentukan member yang ingin dilepas timeout-nya.", ephemeral=True)


async def setup(bot:commands.Bot):
    await bot.add_cog(Untimeout(bot))