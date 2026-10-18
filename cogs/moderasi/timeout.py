import datetime
import re

import discord
from discord.ext import commands

import config


def parse_duration(duration_str: str) -> datetime.timedelta | None:
    match = re.match(r"^(\d+)([smhd])$", duration_str.lower())
    if not match:
        return None
    value, unit = int(match.group(1)), match.group(2)
    units = {'s': 'seconds', 'm': 'minutes', 'h': 'hours', 'd': 'days'}
    return datetime.timedelta(**{units[unit]: value})


class Timeout(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
    
    @commands.hybrid_command(
        name="timeout",
        description="Ngebungkam member untuk durasi tertentu (contoh: 10m, 1h).",
        aliases=["mute"]
    )
    @commands.has_permissions(moderate_members=True)
    @commands.bot_has_permissions(moderate_members=True)
    async def timeout(
        self,
        ctx: commands.Context,
        member: discord.Member,
        duration: str,
        *,
        reason: str | None = "*Tanpa alasan.*"
    ):
        if member.top_role >= ctx.author.top_role and ctx.author != ctx.guild.owner:
            await ctx.reply("💢 Posisi role member-nya setara atau lebih tinggi dari punyamu!", ephemeral=True)
            return
        
        td = parse_duration(duration)
        if not td or td > datetime.timedelta(days=28):
            await ctx.reply("Durasi tidak valid atau melebihi batas maksimal Discord (28 hari). Contoh format: `15m`, `2h`.", ephemeral=True)
            return
        
        await member.timeout(td, reason=reason)
        
        container = discord.ui.Container(accent_color=config.pengaturan.warna_kuning)
        container.add_item(discord.ui.TextDisplay(content=f"### 🔇 {member.mention} dibisukan"))
        container.add_item(discord.ui.Separator(spacing=discord.SeparatorSpacing.small))
        container.add_item(discord.ui.TextDisplay(content=f"Durasi: {duration}\nAlasan: {reason}"))
        
        await ctx.reply(
            view=discord.ui.LayoutView().add_item(container),
            allowed_mentions=discord.AllowedMentions.none()
        )
    
    @timeout.error
    async def timeout_error(self, ctx: commands.Context, error: commands.CommandError):
        if isinstance(error, commands.MissingPermissions):
            await ctx.reply("Kamu tidak punya izin `Moderate Members` untuk menggunakan command ini.", ephemeral=True)
        elif isinstance(error, commands.BotMissingPermissions):
            await ctx.reply("Bot tidak punya izin `Moderate Members` untuk melakukan aksi ini.", ephemeral=True)
        elif isinstance(error, commands.MissingRequiredArgument):
            await ctx.reply("Gunakan format: `/timeout [member] [durasi] [alasan]`", ephemeral=True)


async def setup(bot: commands.Bot):
    await bot.add_cog(Timeout(bot))