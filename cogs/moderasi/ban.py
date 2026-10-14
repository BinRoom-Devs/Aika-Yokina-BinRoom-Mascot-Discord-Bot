import discord
from discord.ext import commands

import config


class Ban(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
    
    @commands.hybrid_command(name="ban", description="Ngeblokir member dari server.")
    @commands.has_permissions(ban_members=True)
    @commands.bot_has_permissions(ban_members=True)
    async def ban(
        self,
        ctx: commands.Context,
        member: discord.Member,
        *,
        reason: str | None = "*Tanpa alasan.*"
    ):
        if member.top_role >= ctx.author.top_role and ctx.author != ctx.guild.owner:
            await ctx.send("💢 Posisi role member-nya setara atau lebih tinggi dari punyamu!", ephemeral=True)
            return
        
        try:
            await member.ban(reason=reason)
        except discord.Forbidden:
            await ctx.send("Gagal: Bot tidak memiliki izin/hierarki role yang cukup untuk me-ban member ini.", ephemeral=True)
            return
        
        container = discord.ui.Container(accent_color=config.pengaturan.warna_merah)
        
        header = f"### 🔨🚫 {member.mention} telah di-ban"
        container.add_item(discord.ui.TextDisplay(content=header))
        
        container.add_item(discord.ui.Separator(spacing=discord.SeparatorSpacing.small))
        
        isi = (
            "Durasi: permanen\n"
            f"Alasan: {reason}"
        )
        container.add_item(discord.ui.TextDisplay(content=isi))
        
        await ctx.send(
            view=discord.ui.LayoutView().add_item(container),
            allowed_mentions=discord.AllowedMentions.none()
        )
    
    @ban.error
    async def ban_error(self, ctx: commands.Context, error: commands.CommandError):
        if isinstance(error, commands.MissingPermissions):
            await ctx.send("Kamu tidak punya izin `Ban Members` untuk menggunakan command ini.", ephemeral=True)
        elif isinstance(error, commands.BotMissingPermissions):
            await ctx.send("Bot tidak punya izin `Ban Members` untuk melakukan aksi ini.", ephemeral=True)
        elif isinstance(error, commands.MissingRequiredArgument):
            await ctx.send("Tentukan anggota yang ingin dibanned.", ephemeral=True)
        elif isinstance(error, commands.CommandInvokeError) and isinstance(error.original, discord.Forbidden):
            await ctx.send("Gagal: Bot tidak memiliki izin/hierarki role yang cukup untuk me-ban member ini.", ephemeral=True)


async def setup(bot: commands.Bot):
    await bot.add_cog(Ban(bot))