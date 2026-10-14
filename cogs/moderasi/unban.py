import re

import discord
from discord.ext import commands

import config


class Unban(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
    
    @commands.hybrid_command(name="unban", description="Membuka blokir Member menggunakan ID Discord.")
    @commands.has_permissions(ban_members=True)
    @commands.bot_has_permissions(ban_members=True)
    async def unban(
        self,
        ctx: commands.Context,
        user_id: str,
        *,
        reason: str | None = "*Tanpa alasan.*"
    ):
        clean_id = re.sub(r"\D", "", user_id)
        if not clean_id:
            await ctx.send("ID Member harus berupa angka.", ephemeral=True)
            return
            
        try:
            user = await self.bot.fetch_user(int(clean_id))
            await ctx.guild.unban(user, reason=reason)
            
            container = discord.ui.Container(accent_color=config.pengaturan.warna_hijau)
            container.add_item(discord.ui.TextDisplay(content=f"### 🔨✅ Ban {user.mention} telah dicabut"))
            container.add_item(discord.ui.Separator(spacing=discord.SeparatorSpacing.small))
            container.add_item(discord.ui.TextDisplay(content=f"ID User: `{clean_id}`\nAlasan: {reason}"))
            
            await ctx.send(
                view=discord.ui.LayoutView().add_item(container),
                allowed_mentions=discord.AllowedMentions.none()
            )
        except discord.NotFound:
            await ctx.send("Member ini lagi gak ke-ban.", ephemeral=True)
        except ValueError:
            await ctx.send("ID Member harus berupa angka.", ephemeral=True)

    @unban.error
    async def unban_error(self, ctx: commands.Context, error: commands.CommandError):
        if isinstance(error, commands.MissingPermissions):
            await ctx.send("Kamu tidak punya izin `Ban Members` untuk menggunakan command ini.", ephemeral=True)
        elif isinstance(error, commands.BotMissingPermissions):
            await ctx.send("Bot tidak punya izin `Ban Members` untuk melakukan aksi ini.", ephemeral=True)
        elif isinstance(error, commands.MissingRequiredArgument):
            await ctx.send("Tentukan User ID yang ingin di-unban.", ephemeral=True)


async def setup(bot: commands.Bot):
    await bot.add_cog(Unban(bot))