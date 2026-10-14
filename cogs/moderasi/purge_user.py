import discord
from discord.ext import commands

import config


class PurgeUser(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
    
    @commands.hybrid_command(name="purgeuser", description="Ngehapus pesan dari member spesifik di channel saat ini.")
    @commands.has_permissions(manage_messages=True)
    @commands.bot_has_permissions(manage_messages=True)
    async def purgeuser(self, ctx: commands.Context, member: discord.Member, amount: int):
        if amount < 1:
            await ctx.send("Jumlah pesan yang diperiksa harus lebih dari 0.", ephemeral=True)
            return
        
        def check(msg: discord.Message):
            return msg.author.id == member.id
        
        deleted = await ctx.channel.purge(limit=amount, check=check)
        
        container = discord.ui.Container(accent_color=config.pengaturan.warna_aika)
        container.add_item(discord.ui.TextDisplay(content=f"### 🧹 Pesan __{member.mention}__ dibersihkan"))
        container.add_item(discord.ui.Separator(spacing=discord.SeparatorSpacing.small))
        container.add_item(discord.ui.TextDisplay(content=f"Berhasil menghapus **{len(deleted)}** pesan."))
        
        await ctx.send(view=discord.ui.LayoutView().add_item(container), delete_after=5, ephemeral=True)
    
    @purgeuser.error
    async def purgeuser_error(self, ctx: commands.Context, error: commands.CommandError):
        if isinstance(error, commands.MissingPermissions):
            await ctx.send("Kamu tidak punya izin `Manage Messages` untuk menggunakan command ini.", ephemeral=True)
        elif isinstance(error, commands.BotMissingPermissions):
            await ctx.send("Bot tidak punya izin `Manage Messages` untuk melakukan aksi ini.", ephemeral=True)
        elif isinstance(error, commands.MemberNotFound):
            await ctx.send("Member tidak ditemukan.", ephemeral=True)
        elif isinstance(error, commands.MissingRequiredArgument):
            if error.param.name == "member":
                await ctx.send("Tentukan member yang pesan-pesannya ingin dihapus.", ephemeral=True)
            elif error.param.name == "amount":
                await ctx.send("Infokan berapa jumlah pesan yang mau dihapus dari member ini.", ephemeral=True)


async def setup(bot: commands.Bot):
    await bot.add_cog(PurgeUser(bot))