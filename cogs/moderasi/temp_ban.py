import datetime
import re

import discord
from discord.ext import commands

import config


def baca_durasi(str_durasi: str) -> datetime.timedelta | None:
    cocok = re.match(r"^(\d+)([smhd])$", str_durasi.lower())
    if not cocok:
        return None
    value, unit = int(cocok.group(1)), cocok.group(2)
    units = {'s': 'seconds', 'm': 'minutes', 'h': 'hours', 'd': 'days'}
    return datetime.timedelta(**{units[unit]: value})


class TempBan(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
    
    @commands.hybrid_command(name="tempban", description="Ngeblokir member sementara waktu (contoh durasi: 10m, 2h, 1d).")
    @commands.has_permissions(ban_members=True)
    @commands.bot_has_permissions(ban_members=True)
    async def tempban(
        self,
        ctx: commands.Context,
        member: discord.Member,
        duration: str,
        *,
        reason: str | None = "*Tanpa alasan.*"
    ):
        if member.top_role >= ctx.author.top_role and ctx.author != ctx.guild.owner:
            await ctx.send("💢 Posisi role member-nya setara atau lebih tinggi dari punyamu!", ephemeral=True)
            return
        
        td = baca_durasi(duration)
        if not td:
            await ctx.send("Format durasi tidak valid. Gunakan format seperti `10s`, `15m`, `2h`, atau `7d`.", ephemeral=True)
            return
        
        user_id = member.id
        _user_name = str(member)
        
        await member.ban(reason=f"[Tempban {duration}] {reason}")
        
        container = discord.ui.Container(accent_color=config.pengaturan.warna_merah)
        container.add_item(discord.ui.TextDisplay(content=f"### 🔨⏱️ {member.mention} telah di-ban sementara"))
        container.add_item(discord.ui.Separator(spacing=discord.SeparatorSpacing.small))
        container.add_item(discord.ui.TextDisplay(content=f"Durasi: {duration}\nAlasan: {reason}"))
        
        await ctx.send(
            view=discord.ui.LayoutView().add_item(container),
            allowed_mentions=discord.AllowedMentions.none()
        )
        
        await discord.utils.sleep_until(discord.utils.utcnow() + td)
        
        try:
            await ctx.guild.unban(discord.Object(id=user_id), reason="Masa tempban telah berakhir.")
        except discord.NotFound:
            pass
    
    @tempban.error
    async def tempban_error(self, ctx:commands.Context, error:commands.CommandError):
        if isinstance(error, commands.MissingPermissions):
            await ctx.send("Kamu tidak punya izin `Ban Members` untuk menggunakan command ini.", ephemeral=True)
        elif isinstance(error, commands.BotMissingPermissions):
            await ctx.send("Bot tidak punya izin `Ban Members` untuk melakukan aksi ini.", ephemeral=True)
        elif isinstance(error, commands.MissingRequiredArgument):
            await ctx.send("Gunakan format: `/tempban [member] [durasi] [alasan]`", ephemeral=True)


async def setup(bot:commands.Bot):
    await bot.add_cog(TempBan(bot))