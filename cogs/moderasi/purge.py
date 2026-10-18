import discord
from discord.ext import commands

import config


class Purge(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
    
    @commands.hybrid_command(
        name="purge",
        description="Ngehapus sejumlah pesan di channel tempat command ini dipanggil.",
        aliases=["clear"]
    )
    @commands.has_permissions(manage_messages=True)
    @commands.bot_has_permissions(manage_messages=True)
    async def purge(self, ctx: commands.Context, amount: int):
        if amount < 1:
            await ctx.reply("Jumlah pesan harus lebih dari 0.", ephemeral=True)
            return
        
        limit = amount + 1 if not ctx.interaction else amount
        deleted = await ctx.channel.purge(limit=limit)
        
        count = len(deleted) if ctx.interaction else len(deleted) - 1
        count = max(0, count)
        
        container = discord.ui.Container(accent_color=config.pengaturan.warna_kuning)
        container.add_item(discord.ui.TextDisplay(content="### 🧹 Pesan berhasil dibersihkan"))
        container.add_item(discord.ui.Separator(spacing=discord.SeparatorSpacing.small))
        container.add_item(discord.ui.TextDisplay(content=f"Jumlah pesan terhapus: **{count}**"))
        
        await ctx.reply(
            view=discord.ui.LayoutView().add_item(container),
            allowed_mentions=discord.AllowedMentions.none(),
            delete_after=5,
            ephemeral=True
        )
    
    @purge.error
    async def purge_error(self, ctx: commands.Context, error: commands.CommandError):
        if isinstance(error, commands.MissingPermissions):
            await ctx.reply("Kamu tidak punya izin `Manage Messages` untuk menggunakan command ini.", ephemeral=True)
        elif isinstance(error, commands.BotMissingPermissions):
            await ctx.reply("Bot tidak punya izin `Manage Messages` untuk melakukan aksi ini.", ephemeral=True)
        elif isinstance(error, commands.MissingRequiredArgument):
            await ctx.reply("Infokan berapa jumlah pesan yang mau dihapus.", ephemeral=True)
        elif isinstance(error, (commands.MemberNotFound, commands.UserNotFound)):
            await ctx.reply("Pakai `/purgeuser` kalau ingin menghapus pesan dari member tertentu.", ephemeral=True)
        elif isinstance(error, commands.BadArgument):
            await ctx.reply("Jumlah pesan harus berupa angka bulat.", ephemeral=True)


async def setup(bot: commands.Bot):
    await bot.add_cog(Purge(bot))