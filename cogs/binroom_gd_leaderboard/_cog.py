import asyncio

import aiohttp
import discord
from discord import app_commands
from discord.ext import commands, tasks

from cogs.leaderboard_central import META_KATEGORI_LEADERBOARD, normalisasi_kategori_gd

from ._config import GAMBAR_HEADER, ID_CHANNEL_LEADERBOARD
from ._models import GDPlayer
from ._utils import (
    baca_data_tunggal_player_async,
    buat_embed_gd,
    cari_profil_gd,
    load_daftar_player_async,
    simpan_daftar_player_async,
)
from .views import (
    GDLeaderboardCategoryView,
    MenuPilihHapusPlayer,
    TampilanKategoriLeaderboard,
    TampilanRegistrasiContainer,
)


class BinrumLeaderboard(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.session = aiohttp.ClientSession()
        self.semaphore = asyncio.Semaphore(6)
        self.update_otomatis.start()
    
    async def cog_unload(self):
        self.update_otomatis.cancel()
        await self.session.close()
    
    async def cog_load(self):
        self.bot.add_view(TampilanRegistrasiContainer(self))
    
    async def cog_app_command_error(self, interaction:discord.Interaction, error:app_commands.AppCommandError):
        msg = "<:GD_x:1543409414843662346> Hanya atmint yang bisa pakai fitur ini!" if isinstance(error, (app_commands.MissingPermissions, app_commands.CheckFailure)) else f"<:GD_x:1543409414843662346> Terjadi kesalahan: `{error}`"
        try:
            if interaction.response.is_done():
                await interaction.followup.send(msg, ephemeral=True)
            else:
                await interaction.response.send_message(msg, ephemeral=True)
        except discord.HTTPException:
            pass
    
    async def cog_command_error(self, ctx:commands.Context, error:commands.CommandError):
        msg = "<:GD_x:1543409414843662346> Hanya atmint yang bisa pakai fitur ini!" if isinstance(error, (commands.MissingPermissions, commands.CheckFailure)) else f"<:GD_x:1543409414843662346> Terjadi kesalahan: `{error}`"
        if ctx.interaction:
            try:
                if ctx.interaction.response.is_done():
                    await ctx.interaction.followup.send(msg, ephemeral=True)
                else:
                    await ctx.interaction.response.send_message(msg, ephemeral=True)
            except discord.HTTPException:
                pass
        else:
            await ctx.send(msg)
    
    async def refresh_data_only(self) -> tuple[int, int]:
        daftar_id_player = await load_daftar_player_async()
        if not daftar_id_player:
            return 0, 0
        
        updated_count = 0
        failed_count = 0
        
        async def fetch_with_semaphore(p_dict):
            async with self.semaphore:
                obj, updated_dict = await baca_data_tunggal_player_async(self.session, p_dict)
                return obj, updated_dict
        
        tugas_fetch = [fetch_with_semaphore(p) for p in daftar_id_player]
        hasil = await asyncio.gather(*tugas_fetch)
        
        updated_players = [p_dict for _, p_dict in hasil]
        await simpan_daftar_player_async(updated_players)
        return updated_count, failed_count
    
    async def update_tampilan_leaderboard(self, target_channel=None):
        channel_leaderboard = target_channel or self.bot.get_channel(ID_CHANNEL_LEADERBOARD)
        if not channel_leaderboard:
            return
        
        daftar_id_player = await load_daftar_player_async()
        
        if not daftar_id_player:
            await channel_leaderboard.purge(limit=10)
            reg_view = TampilanRegistrasiContainer(self)
            embed_reg = await reg_view.generate_embed_async()
            await channel_leaderboard.send(embed=embed_reg, view=reg_view)
            return
        
        async def fetch_with_semaphore(p_dict):
            async with self.semaphore:
                obj, updated_dict = await baca_data_tunggal_player_async(self.session, p_dict)
                return (obj, updated_dict) if obj is not None else None
        
        tugas_fetch = [fetch_with_semaphore(p) for p in daftar_id_player]
        hasil = await asyncio.gather(*tugas_fetch, return_exceptions=True)
        
        player_valid = []
        updated_players_dict = []
        
        for original_dict, res in zip(daftar_id_player, hasil):
            if isinstance(res, tuple) and res[0] is not None:
                player_obj, updated_dict = res
                player_valid.append((player_obj, updated_dict))
                updated_players_dict.append(updated_dict)
            else:
                updated_players_dict.append(original_dict)
        
        await simpan_daftar_player_async(updated_players_dict)
        
        data_demons = sorted(player_valid, key=lambda pair: getattr(pair[0], "demons", 0), reverse=True)
        data_stars = sorted(player_valid, key=lambda pair: getattr(pair[0], "stars", 0), reverse=True)
        data_cp = sorted([pair for pair in player_valid if getattr(pair[0], "creatorPoints", 0) > 0], \
            key=lambda pair: getattr(pair[0], "creatorPoints", 0), reverse=True)
        
        try:
            await channel_leaderboard.purge(limit=10)
            
            view_demons = TampilanKategoriLeaderboard(
                judul_kategori="<:GD_harddemon:1543546992234598490> BinRoom GD Players Leaderboard — Kategori Demons",
                data_player=data_demons,
                kunci_stat="demons",
                emoji_stat="<:hard_demon:1285063566742781984>",
                warna_aksen=discord.Colour.red(),
                gambar_banner=GAMBAR_HEADER
            )
            await channel_leaderboard.send(view=view_demons)
            
            view_stars = TampilanKategoriLeaderboard(
                judul_kategori="<:GD_star:1543545805888295012> BinRoom GD Players Leaderboard — Kategori Stars",
                data_player=data_stars,
                kunci_stat="stars",
                emoji_stat="<:gd_star:1285063657839136869>",
                warna_aksen=discord.Colour.gold()
            )
            await channel_leaderboard.send(view=view_stars)
            
            if data_cp:
                view_cp = TampilanKategoriLeaderboard(
                    judul_kategori="<:GD_creator:1543546308848132106> BinRoom GD Players Leaderboard — Kategori Creator Points",
                    data_player=data_cp,
                    kunci_stat="creatorPoints",
                    emoji_stat="<:creator_icon:1543402506355212409>",
                    warna_aksen=discord.Colour.light_grey()
                )
                await channel_leaderboard.send(view=view_cp)
            
            view_reg = TampilanRegistrasiContainer(self)
            embed_reg = await view_reg.generate_embed_async()
            await channel_leaderboard.send(embed=embed_reg, view=view_reg)
            
        except discord.DiscordException as galat:
            print(f"[Aika] GD Leaderboard: gagal mengirim pesan: {galat}")
    
    async def render_tampilan_leaderboard_lokal(self, target_channel=None):
        channel_leaderboard = target_channel or self.bot.get_channel(ID_CHANNEL_LEADERBOARD)
        if not channel_leaderboard:
            return
        
        daftar_db = await load_daftar_player_async()
        if not daftar_db:
            await channel_leaderboard.purge(limit=10)
            reg_view = TampilanRegistrasiContainer(self)
            embed_reg = await reg_view.generate_embed_async()
            await channel_leaderboard.send(embed=embed_reg, view=reg_view)
            return
        
        player_valid = []
        for p in daftar_db:
            stats = p.get("statistik") or {}
            mock_data = {
                "username": p.get("nama_user_gd", "Tidak Diketahui"),
                "accountID": p.get("account_id_gd", 0),
                "playerID": p.get("player_id_gd", 0),
                "stars": stats.get("stars", p.get("stars", 0)),
                "moons": stats.get("moons", p.get("moons", 0)),
                "diamonds": stats.get("diamonds", p.get("diamonds", 0)),
                "coins": stats.get("secret_coins", p.get("secret_coins", 0)),
                "userCoins": stats.get("user_coins", p.get("user_coins", 0)),
                "demons": stats.get("demons", p.get("demons", 0)),
                "cp": stats.get("creator_points", p.get("creator_points", 0)),
                "icon": p.get("icon", stats.get("icon", 1)),
                "col1": p.get("col1", p.get("color1", stats.get("color1", 0))),
                "col2": p.get("col2", p.get("color2", stats.get("color2", 0))),
                "glow": p.get("glow", stats.get("glow", 0)),
            }
            player_valid.append((GDPlayer(mock_data), p))
        
        data_demons = sorted(player_valid, key=lambda pair: getattr(pair[0], "demons", 0), reverse=True)
        data_stars = sorted(player_valid, key=lambda pair: getattr(pair[0], "stars", 0), reverse=True)
        data_cp = sorted([pair for pair in player_valid if getattr(pair[0], "creatorPoints", 0) > 0], \
            key=lambda pair: getattr(pair[0], "creatorPoints", 0), reverse=True)
        
        try:
            await channel_leaderboard.purge(limit=10)
            
            view_demons = TampilanKategoriLeaderboard(
                judul_kategori="<:GD_harddemon:1543546992234598490> BinRoom GD Players Leaderboard — Kategori Demons",
                data_player=data_demons,
                kunci_stat="demons",
                emoji_stat="<:hard_demon:1285063566742781984>",
                warna_aksen=discord.Colour.red(),
                gambar_banner=GAMBAR_HEADER
            )
            await channel_leaderboard.send(view=view_demons)
            
            view_stars = TampilanKategoriLeaderboard(
                judul_kategori="<:GD_star:1543545805888295012> BinRoom GD Players Leaderboard — Kategori Stars",
                data_player=data_stars,
                kunci_stat="stars",
                emoji_stat="<:gd_star:1285063657839136869>",
                warna_aksen=discord.Colour.gold()
            )
            await channel_leaderboard.send(view=view_stars)
            
            if data_cp:
                view_cp = TampilanKategoriLeaderboard(
                    judul_kategori="<:GD_creator:1543546308848132106> BinRoom GD Players Leaderboard — Kategori Creator Points",
                    data_player=data_cp,
                    kunci_stat="creatorPoints",
                    emoji_stat="<:creator_icon:1543402506355212409>",
                    warna_aksen=discord.Colour.light_grey()
                )
                await channel_leaderboard.send(view=view_cp)
            
            view_reg = TampilanRegistrasiContainer(self)
            embed_reg = await view_reg.generate_embed_async()
            await channel_leaderboard.send(embed=embed_reg, view=view_reg)
            
        except discord.DiscordException as galat:
            print(f"[Aika] GD Leaderboard: gagal memperbarui tampilan lokal: {galat}")
    
    @tasks.loop(hours=24)
    async def update_otomatis(self):
        await self.update_tampilan_leaderboard()
    
    @update_otomatis.before_loop
    async def sebelum_update_otomatis(self):
        await self.bot.wait_until_ready()
    
    @commands.hybrid_group(
        name="gd-leaderboard",
        description="Nampilin leaderboard player GD BinRoom.",
        hidden=True
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
    
    @gd_leaderboard.command(
        name="refresh",
        description="Memperbarui tampilan leaderboard GD secara manual.",
        aliases=["flush", "update"],
        hidden=True
    )
    @commands.has_permissions(administrator=True)
    @app_commands.default_permissions(administrator=True)
    async def reset_leaderboard(self, ctx:commands.Context):
        await ctx.defer(ephemeral=False)
        try:
            await self.update_tampilan_leaderboard(target_channel=ctx.channel)
            await ctx.send("<:GD_complete:1543409457940267078> Leaderboard berhasil diperbarui.")
        except Exception as e:  # noqa: BLE001
            await ctx.send(f"Gagal, coba lagi.\n`{e}`")
    
    @gd_leaderboard.command(
        name="rebuild",
        description="Merender ulang leaderboard dari database lokal tanpa memanggil API GD.",
        aliases=["rerender", "repost"],
        hidden=True
    )
    @commands.has_permissions(administrator=True)
    @app_commands.default_permissions(administrator=True)
    async def rebuild_leaderboard(self, ctx: commands.Context):
        await ctx.defer(ephemeral=False)
        try:
            await self.render_tampilan_leaderboard_lokal(target_channel=ctx.channel)
            await ctx.send("<:GD_complete:1543409457940267078> Berhasil merender ulang leaderboard")
        except Exception as e:  # noqa: BLE001
            await ctx.send(f"Gagal merender ulang leaderboard.\n`{e}`")
    
    @gd_leaderboard.command(
        name="daftarkan",
        description="Command admin untuk mendaftarkan player GD ke leaderboard secara manual.",
        aliases=["register", "add"],
        hidden=True
    )
    @commands.has_permissions(administrator=True)
    @app_commands.default_permissions(administrator=True)
    async def admin_register_gd(self, ctx:commands.Context, gd_username:str, discord_user:discord.User=None):
        await ctx.defer(ephemeral=False)
        nama_input = gd_username.strip()
        
        data_user = await cari_profil_gd(self.session, nama_input)
        if not data_user:
            await ctx.send("<:GD_x:1543409414843662346> Username GD tidak valid, gagal mendaftarkan...", ephemeral=True)
            return
        
        account_id, player_id, nama_asli = data_user
        id_discord = discord_user.id if discord_user else None
        
        daftar_player = await load_daftar_player_async()
        player_ada = next(
            (p for p in daftar_player if p.get("account_id_gd") == account_id or p.get("nama_user_gd").lower() == nama_asli.lower()),
            None
        )
        
        if player_ada:
            player_ada["nama_user_gd"] = nama_asli
            player_ada["account_id_gd"] = account_id
            player_ada["player_id_gd"] = player_id
            if id_discord:
                player_ada["id_user_discord"] = id_discord
        else:
            data_player_baru = {
                "nama_user_gd": nama_asli,
                "account_id_gd": account_id,
                "player_id_gd": player_id,
                "id_user_discord": id_discord,
                "statistik": {
                    "stars": 0, "moons": 0, "diamonds": 0,
                    "secret_coins": 0, "user_coins": 0, "demons": 0, "creator_points": 0
                }
            }
            daftar_player.append(data_player_baru)
        
        await simpan_daftar_player_async(daftar_player)
        
        p_target = next(p for p in daftar_player if p.get("account_id_gd") == account_id)
        _, p_updated = await baca_data_tunggal_player_async(self.session, p_target)
        
        daftar_player = [p_updated if p.get("account_id_gd") == account_id else p for p in daftar_player]
        await simpan_daftar_player_async(daftar_player)
        
        embed_sukses = buat_embed_gd(
            title="<:GD_complete:1543409457940267078> Player Didaftarkan",
            description=f"Berhasil mendaftarkan **{nama_asli}** ke leaderboard!",
            color=discord.Color.green()
        )
        if id_discord:
            embed_sukses.description += f"\nDiisikan ke akun Discord: <@{id_discord}>"
        
        await ctx.send(embed=embed_sukses)
    
    @gd_leaderboard.command(
        name="hapus-player",
        description="Command admin untuk menghapus player GD dari leaderboard.",
        aliases=["delete", "remove"],
        hidden=True
    )
    @commands.has_permissions(administrator=True)
    @app_commands.default_permissions(administrator=True)
    async def hapus_player_gd(self, ctx:commands.Context):
        await ctx.defer(ephemeral=True)
        daftar_player = await load_daftar_player_async()
        
        if not daftar_player:
            await ctx.send("<:GD_x:1543409414843662346> Belum ada player terdaftar di leaderboard.", ephemeral=True)
            return
        
        menu_view = MenuPilihHapusPlayer(daftar_player, timeout_seconds=60.0)
        pesan = await ctx.send(embed=menu_view.get_content(), view=menu_view, ephemeral=True)
        menu_view.pesan = pesan