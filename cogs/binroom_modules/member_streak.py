from datetime import datetime, timedelta, timezone

import discord
from discord import SeparatorSpacing
from discord.ext import commands
from discord.ui import Container, LayoutView, Separator, TextDisplay

from database import (
    baca_leaderboard_streak,
    baca_streak_member,
    proses_streak_harian,
    reset_streak_member,
)

WIB = timezone(timedelta(hours=7))

def str_ke_discord_timestamp(str_tgl:str|None, flag:str="D") -> str:
    if not str_tgl:
        return "-"
    try:
        dt = datetime.strptime(str_tgl, "%Y-%m-%d").replace(tzinfo=WIB)
        timestamp_unix = int(dt.timestamp())
        return f"<t:{timestamp_unix}:{flag}>"
    except ValueError:
        return str_tgl


class MemberStreak(commands.Cog):
    def __init__(self, bot:commands.Bot):
        self.bot = bot
    
    @commands.Cog.listener()
    async def on_message(self, message:discord.Message):
        if message.author.bot or not message.guild:
            return
        
        hasil = await proses_streak_harian(message.author.id)
        status = hasil["status"]
        container = discord.ui.Container(accent_color=message.author.color)
        
        if status == "sudah_masuk":
            return
        
        if status == "streak_naik":
            container.add_item(discord.ui.TextDisplay(
                content=f"### 🔥 Streak nimbrung +1! Sekarang: __{hasil['streak_skrg']} hari__")
            )
            await message.channel.reply(view=LayoutView().add_item(container), delete_after=10)
            
        elif status == "streak_reset":
            await message.channel.reply(
                content="Hai lagi! Streak nimbrungmu balik ke 0 karena kemarin absen yah.",
                delete_after=10
            )
            
            container.add_item(discord.ui.TextDisplay(
                content=f"### 🔥 Streak nimbrung +1! Sekarang: __{hasil['streak_skrg']} hari__")
            )
            await message.channel.send(view=LayoutView().add_item(container), delete_after=10)
        
    @commands.hybrid_group(
        name="streak",
        description="Mengecek atau mengelola streak nimbrung di BinRoom."
    )
    async def streak(self, ctx:commands.Context):
        if ctx.invoked_subcommand is None:
            await self.user(ctx, target=None)
    
    @streak.command(
        name="user",
        aliases=["cek", "check"],
        description="Mengecek streak nimbrung kamu atau member lain di BinRoom."
    )
    async def user(self, ctx:commands.Context, target:discord.Member|None=None):
        target = target or ctx.author
        
        if target.bot:
            await ctx.send("💢 Streak nimbrung tidak berlaku untuk bot.", ephemeral=True)
            return
        
        await ctx.defer()
        target_member = target or ctx.author
        data = await baca_streak_member(target_member.id)
        
        container = Container(accent_color=target_member.color)
        
        if target_member == ctx.author:
            judul = f"🔥 **Streak Nimbrung di BinRoom** — {target_member.mention}"
        else:
            judul = f"🔥 **Streak Nimbrung di BinRoom** — {target_member.display_name}"
        container.add_item(TextDisplay(content=judul))
        
        container.add_item(Separator(spacing=SeparatorSpacing.small, visible=False))
        
        isi = (
            f"## Saat ini: __{data['streak_skrg']} hari__    "
            f"Terlama: __{data['streak_terlama']} hari__"
        )
        container.add_item(TextDisplay(content=isi))
        
        container.add_item(Separator(spacing=SeparatorSpacing.small))
        
        tgl_berjalan = str_ke_discord_timestamp(data["mulai_skrg"])
        tgl_terlama_mulai = str_ke_discord_timestamp(data["mulai_terlama"])
        tgl_terlama_selesai = str_ke_discord_timestamp(data["selesai_terlama"])
        poin_informasi = (
            f"- Berjalan sejak: {tgl_berjalan}\n"
            f"- Terlama: {tgl_terlama_mulai} - {tgl_terlama_selesai}"
        )
        container.add_item(TextDisplay(content=poin_informasi))
        
        container.add_item(Separator(spacing=SeparatorSpacing.small))
        
        footer = "-# Nimbrung tiap hari minimal 1 pesan biar streak-mu tetap jalan!"
        container.add_item(TextDisplay(content=footer))
        
        await ctx.send(
            view=LayoutView().add_item(container),
            allowed_mentions=discord.AllowedMentions.none()
        )
    
    @streak.command(
        name="reset",
        aliases=["hapus", "clear", "flush", "delete"],
        description="Nge-reset streak nimbrungmu sendiri (Gabisa dibalikin!)."
    )
    async def hapus_streak(self, ctx:commands.Context):
        await ctx.defer(ephemeral=True)
        
        berhasil = await reset_streak_member(ctx.author.id)
        
        container = Container(accent_color=ctx.author.color)
        
        if berhasil:
            container.add_item(TextDisplay(content="🗑️ **Streak Nimbrungmu Berhasil Dihapus**"))
            container.add_item(Separator(spacing=SeparatorSpacing.small, visible=False))
            container.add_item(TextDisplay(content="Seluruh riwayat streak nimbrung milikmu telah direset ke 0 hari."))
        else:
            container.add_item(TextDisplay(content="⚠️ **Data Streak Tidak Ditemukan**"))
            container.add_item(Separator(spacing=SeparatorSpacing.small, visible=False))
            container.add_item(TextDisplay(content="Kamu belum memiliki catatan streak di BinRoom."))
            
        await ctx.send(
            view=LayoutView().add_item(container),
            ephemeral=True
        )
    
    @streak.command(
        name="leaderboard",
        aliases=["top", "lb"],
        description="Papan peringkat streak nimbrung tertinggi di BinRoom."
    )
    async def leaderboard(self, ctx:commands.Context):
        await ctx.defer()
        top_members = await baca_leaderboard_streak(limit=10)
        
        container = Container(accent_color=0xDE82CF)
        
        container.add_item(TextDisplay(content="### 🏆  Leaderboard Streak Nimbrung BinRoom"))
        container.add_item(Separator(spacing=SeparatorSpacing.small, visible=False))
        
        if not top_members:
            container.add_item(TextDisplay(content="_Belum ada member yang memiliki streak berjalan._"))
        else:
            papan_skor = []
            medals = ["🥇", "🥈", "🥉"]
            
            for index, data in enumerate(top_members, start=1):
                peringkat = medals[index - 1] if index <= 3 else f"`#{index}`"
                papan_skor.append(
                    f"- {peringkat} <@{data['user_id']}> — **{data['streak_skrg']} hari** _(rekor: {data['streak_terlama']} hari)_"
                )
            container.add_item(TextDisplay(content="\n".join(papan_skor)))
            
        container.add_item(Separator(spacing=SeparatorSpacing.small))
        container.add_item(TextDisplay(content="-# Tetap aktif nimbrung tiap hari buat mempertahankan posisi top-mu!"))
        
        await ctx.send(
            view=LayoutView().add_item(container),
            allowed_mentions=discord.AllowedMentions.none()
        )


async def setup(bot:commands.Bot):
    await bot.add_cog(MemberStreak(bot))