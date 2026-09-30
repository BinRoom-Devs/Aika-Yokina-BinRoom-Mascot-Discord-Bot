import discord
from discord import SeparatorSpacing
from discord.ext import commands
from discord.ui import Container, LayoutView, Separator, TextDisplay

from database import baca_streak_member, proses_streak_harian


class MemberStreak(commands.Cog):
    def __init__(self, bot:commands.Bot):
        self.bot = bot
    
    @commands.Cog.listener()
    async def on_message(self, message:discord.Message):
        if message.author.bot or not message.guild:
            return
        
        hasil = await proses_streak_harian(message.author.id)
        status = hasil["status"]
        
        if status == "sudah_masuk":
            return
        
        if status == "streak_naik":
            await message.channel.send(
                content=
                    (f"Streak-mu __{hasil['streak_skrg']} hari__!\n"
                    "\n"
                    "-# Nimbrung tiap hari biar streak-mu jalan terus."),
                delete_after=10
            )
        
        elif status == "streak_reset":
            await message.channel.send(
                content=
                    (f"Hai lagi! Streak-mu hari ini balik lagi ke __{hasil['streak_skrg']} hari__, ya.\n"
                    "\n"
                    "-# Nimbrung tiap hari biar streak-mu jalan terus."),
                delete_after=10
            )
    
    @commands.hybrid_command(
        name="streak",
        aliases=["cek-streak", "check-streak"],
        description="Mengecek streak nimbrung kamu di BinRoom."
    )
    async def streak(self, ctx:commands.Context):
        data = await baca_streak_member(ctx.author.id)
        
        
        container = Container(accent_color=ctx.author.color)
        
        judul = f"🔥 Streak Nimbrung di BinRoom — {ctx.author.mention}"
        container.add_item(discord.ui.TextDisplay(content=judul))
        
        container.add_item(Separator(spacing=SeparatorSpacing.small, visible=False))
        
        isi = (
            f"## Saat ini: __{data['streak_skrg']} hari__    "
            f" Terlama: __{data['streak_terlama']} hari__"
        )
        container.add_item(TextDisplay(content=isi))
        
        container.add_item(Separator(spacing=SeparatorSpacing.small))
        
        footer = "-# Nimbrung tiap hari minimal 1 pesan biar streak-mu tetap jalan!"
        container.add_item(TextDisplay(content=footer))
        
        
        await ctx.send(
            view=LayoutView().add_item(container),
            allowed_mentions=discord.AllowedMentions.none()
        )


async def setup(bot:commands.Bot):
    await bot.add_cog(MemberStreak(bot))