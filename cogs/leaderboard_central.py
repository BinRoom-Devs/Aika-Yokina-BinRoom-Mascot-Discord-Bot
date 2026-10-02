import discord
from discord import SeparatorSpacing
from discord.ext import commands
from discord.ui import Container, LayoutView, Separator, TextDisplay

from cogs.binroom_gd_leaderboard._config import META_KATEGORI_LEADERBOARD
from cogs.binroom_gd_leaderboard._utils import (
    load_daftar_player_async,
    normalisasi_kategori_gd,
)
from cogs.binroom_gd_leaderboard.views._categories import GDLeaderboardCategoryView
from database import baca_leaderboard_streak


class LeaderboardCentral(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
    
    @commands.hybrid_group(
        name="leaderboard",
        aliases=["lb", "top"],
        description="Pusat papan peringkat (leaderboard) di BinRoom."
    )
    async def leaderboard(self, ctx: commands.Context):
        if ctx.invoked_subcommand is None:
            await ctx.defer()
            
            container = Container(accent_color=0xDE82CF)
            container.add_item(TextDisplay(content="### 📊 Pusat Leaderboard BinRoom"))
            container.add_item(Separator(spacing=SeparatorSpacing.small))
            
            cmd_induk = ctx.command
            
            if isinstance(cmd_induk, commands.HybridGroup) and cmd_induk.commands:
                list_info = ["Mau cek leaderboard tentang apa?\n"]
                
                for sub_cmd in cmd_induk.commands:
                    deskripsi = sub_cmd.description or "Papan peringkat BinRoom."
                    list_info.append(f"• `/leaderboard {sub_cmd.name}` — {deskripsi}")
                
                info = "\n".join(list_info)
            else:
                info = "_Belum ada kategori leaderboard yang tersedia saat ini._"
            
            container.add_item(TextDisplay(content=info))
            container.add_item(Separator(spacing=SeparatorSpacing.small))
            container.add_item(TextDisplay(content="-# Pilih salah satu command di atas untuk melihat detailnya!"))
            
            await ctx.send(
                view=LayoutView().add_item(container),
                allowed_mentions=discord.AllowedMentions.none()
            )
    
    @leaderboard.command(
        name="streak",
        aliases=["nimbrung"],
        description="Papan peringkat streak nimbrung tertinggi di BinRoom."
    )
    async def streak_leaderboard(self, ctx: commands.Context):
        await ctx.defer()
        top_members = await baca_leaderboard_streak(limit=10)
        
        container = Container(accent_color=0xDE82CF)
        
        container.add_item(TextDisplay(content="### 🏆 Leaderboard Streak Nimbrung BinRoom"))
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
    
    @leaderboard.command(
        name="geometry-dash",
        aliases=["gd"],
        description="Nampilin leaderboard player GD BinRoom."
    )
    async def gd_leaderboard(self, ctx:commands.Context, category:str="stars"):
        await ctx.defer(ephemeral=False)
        
        gd_cog = self.bot.get_cog("BinrumLeaderboard")
        if not gd_cog:
            await ctx.send("<:GD_x:1543409414843662346> Fitur GD Leaderboard sedang tidak aktif/tersedia.")
            return
        
        normalized = normalisasi_kategori_gd(category)
        if normalized not in META_KATEGORI_LEADERBOARD:
            normalized = "stars"
        
        daftar_player = await load_daftar_player_async()
        view = GDLeaderboardCategoryView(gd_cog, daftar_player, normalized, timeout_seconds=180.0)
        embed = view.build_embed()
        pesan = await ctx.send(embed=embed, view=view)
        view.message = pesan


async def setup(bot: commands.Bot):
    await bot.add_cog(LeaderboardCentral(bot))