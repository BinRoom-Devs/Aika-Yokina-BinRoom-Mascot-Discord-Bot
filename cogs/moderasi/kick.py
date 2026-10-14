import discord
from discord.ext import commands

import config


class Kick(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
    
    @commands.hybrid_command(name="kick", description="Ngekeluarin member dari server.")
    @commands.has_permissions(kick_members=True)
    @commands.bot_has_permissions(kick_members=True)
    async def kick(
        self,
        ctx: commands.Context,
        member: discord.Member,
        *,
        reason: str | None = "*Tanpa alasan.*"
    ):
        if member.top_role >= ctx.author.top_role and ctx.author != ctx.guild.owner:
            await ctx.send("💢 Posisi role member-nya setara atau lebih tinggi dari punyamu!", ephemeral=True)
            return
        
        await member.kick(reason=reason)
        
        container = discord.ui.Container(accent_color=config.pengaturan.warna_merah)
        container.add_item(discord.ui.TextDisplay(content=f"### 🦵🏻 {member.mention} telah di-kick"))
        container.add_item(discord.ui.Separator(spacing=discord.SeparatorSpacing.small))
        container.add_item(discord.ui.TextDisplay(content=f"Alasan: {reason}"))
        
        await ctx.send(
            view=discord.ui.LayoutView().add_item(container),
            allowed_mentions=discord.AllowedMentions.none()
        )
    
    @kick.error
    async def kick_error(self, ctx:commands.Context, error:commands.CommandError):
        if isinstance(error, commands.MissingPermissions):
            await ctx.send("Kamu tidak punya izin `Kick Members` untuk menggunakan command ini.", ephemeral=True)
        elif isinstance(error, commands.BotMissingPermissions):
            await ctx.send("Bot tidak punya izin `Kick Members` untuk melakukan aksi ini.", ephemeral=True)
        elif isinstance(error, commands.MissingRequiredArgument):
            await ctx.send("Tentukan anggota yang ingin dikick.", ephemeral=True)


async def setup(bot:commands.Bot):
    await bot.add_cog(Kick(bot))