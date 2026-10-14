from __future__ import annotations

import asyncio
import io
import logging
import time
from dataclasses import dataclass

import aiohttp
import discord
from discord.ext import commands

from config import pengaturan

log = logging.getLogger(__name__)

UKURAN_MAKS = 15 * 1024 * 1024
CACHE_TTL = 3600
CACHE_MAKS = 256


@dataclass(frozen=True, slots=True)
class InfoAset:
    warna: int
    lebar: int = 0
    tinggi: int = 0
    animasi: bool = False
    frame: int = 1


def _info_gagal() -> InfoAset:
    return InfoAset(warna=pengaturan.warna_aika)


def _detail_aset(info:InfoAset, tipe:str) -> list[str]:
    bagian = ["GIF" if info.animasi else "PNG"]
    
    if tipe == "avatar":
        if info.tinggi:
            bagian.append(f"{info.tinggi}p")
    elif info.lebar and info.tinggi:
        bagian.append(f"{info.lebar}x{info.tinggi}p")
    
    if info.animasi and info.frame > 1:
        bagian.append(f"{info.frame} frames")
    
    return bagian


def _container_pesan(judul:str, isi:str, warna:int|None=None) -> discord.ui.Container:
    container = discord.ui.Container(accent_color=warna) \
        if warna is not None else discord.ui.Container()
    container.add_item(discord.ui.TextDisplay(content=judul))
    container.add_item(discord.ui.Separator(spacing=discord.SeparatorSpacing.small))
    container.add_item(discord.ui.TextDisplay(content=isi))
    return container


class PFP(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self._session: aiohttp.ClientSession | None = None
        self._cache: dict[str, tuple[float, InfoAset]] = {}
    
    @property
    def session(self) -> aiohttp.ClientSession:
        if self._session is None or self._session.closed:
            self._session = aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=10))
        return self._session
    
    async def cog_unload(self):
        if self._session and not self._session.closed:
            await self._session.close()
    
    # ------------------------------------------------------------------
    # Pemrosesan gambar
    # ------------------------------------------------------------------
    @staticmethod
    def _proses(data: bytes) -> InfoAset:
        from PIL import Image
        
        try:
            with Image.open(io.BytesIO(data)) as img:
                lebar, tinggi = img.size
                frame = getattr(img, "n_frames", 1)
                
                try:
                    resample_nearest = Image.Resampling.NEAREST
                    resample_box = Image.Resampling.BOX
                except AttributeError:
                    resample_nearest = Image.NEAREST
                    resample_box = Image.BOX
                
                kecil = img.resize((64, 64), resample_nearest).convert("RGB")
                r, g, b = kecil.resize((1, 1), resample_box).getpixel((0, 0))
                
                return InfoAset((r << 16) | (g << 8) | b, lebar, tinggi, frame > 1, frame)
            
        except (Image.UnidentifiedImageError, Image.DecompressionBombError, OSError, ValueError):
            return _info_gagal()
    
    async def _unduh_dan_proses(self, url:str) -> InfoAset:
        try:
            async with self.session.get(url) as respon:
                if respon.status != 200:
                    return _info_gagal()
                if respon.content_length and respon.content_length > UKURAN_MAKS:
                    return _info_gagal()
                data = await respon.read()
            if len(data) > UKURAN_MAKS:
                return _info_gagal()
            return await asyncio.to_thread(self._proses, data)
        except (TimeoutError, aiohttp.ClientError) as e:
            log.warning("Foto profil: gagal memproses gambar (%s)", e)
            return _info_gagal()
    
    async def info_aset(self, url:str|None) -> InfoAset | None:
        if not url:
            return None
        
        hit = self._cache.get(url)
        if hit and hit[0] > time.monotonic():
            return hit[1]
        
        info = await self._unduh_dan_proses(url)
        
        if info.lebar:
            if len(self._cache) >= CACHE_MAKS:
                self._cache.pop(next(iter(self._cache)))
            self._cache[url] = (time.monotonic() + CACHE_TTL, info)
        return info
    
    # ------------------------------------------------------------------
    # Pembuat tampilan
    # ------------------------------------------------------------------
    async def buat_container(
        self,
        user: discord.User,
        member: discord.Member | None,
        tipe: str,
    ) -> discord.ui.Container:
        if tipe == "avatar":
            utama = user.avatar or user.default_avatar
            server = member.guild_avatar if member else None
            jenis_label = "Foto Profilnya"
        else:
            utama = getattr(user, "banner", None)
            server = getattr(member, "guild_banner", None)
            jenis_label = "Foto Sampulnya"
        
        if utama is None and server is None:
            accent = getattr(user, "accent_color", None)
            if accent:
                hex_str = f"#{accent.value:06X}"
                return _container_pesan(
                    "## Banner Tidak Ada",
                    f"{user.mention} tidak punya gambar banner, tetapi menggunakan warna solid **{hex_str}**.",
                    warna=accent.value,
                )
            return _container_pesan(
                "## Banner Tidak Ada",
                f"{user.mention} tidak memiliki banner custom maupun warna aksen.",
            )
        
        link_u = utama.with_size(4096).url if utama is not None else None
        link_s = server.with_size(4096).url if server is not None else None
        
        info_u, info_s = await asyncio.gather(self.info_aset(link_u), self.info_aset(link_s))
        
        if link_u and link_s:
            container = discord.ui.Container()
        else:
            warna_info = info_u or info_s
            container = discord.ui.Container(accent_color=warna_info.warna if warna_info else None)
        
        container.add_item(discord.ui.TextDisplay(content=f"## {jenis_label} si {user.mention}"))
        container.add_item(discord.ui.Separator(spacing=discord.SeparatorSpacing.small))
        
        items = [discord.MediaGalleryItem(link) for link in (link_u, link_s) if link]
        if tipe == "banner" and len(items) > 1:
            for item in items:
                container.add_item(discord.ui.MediaGallery(item))
        else:
            container.add_item(discord.ui.MediaGallery(*items))
        
        container.add_item(discord.ui.Separator(spacing=discord.SeparatorSpacing.small))
        
        if info_u and info_s:
            kiri, kanan = ("Atas", "Bawah") if tipe == "banner" else ("Kiri", "Kanan")
            footer = (
                f"-# {kiri}: global ({', '.join(_detail_aset(info_u, tipe))})"
                f"  ·  {kanan}: server ({', '.join(_detail_aset(info_s, tipe))})"
            )
        elif info_s:
            footer = f"-# Server: {', '.join(_detail_aset(info_s, tipe))}"
        else:
            bagian = [f"[Link Utama]({link_u})", *_detail_aset(info_u, tipe)]
            key = getattr(utama, "key", None)
            if key and (tipe == "avatar" or info_u.lebar > 500):
                bagian.append(f"`{key}`")
            footer = "-# " + "  ·  ".join(bagian)
        
        container.add_item(discord.ui.TextDisplay(content=footer))
        return container
    
    # ------------------------------------------------------------------
    # Helper command
    # ------------------------------------------------------------------
    async def _putuskan_user_dan_member(
        self,
        target: discord.Member | discord.User | None,
        ctx: commands.Context,
        perlu_banner: bool,
    ) -> tuple[discord.User, discord.Member | None]:
        target_obj = target or ctx.author
        member_obj = target_obj if isinstance(target_obj, discord.Member) else None
        
        if isinstance(target_obj, discord.User):
            user_obj = target_obj
        else:
            user_obj = getattr(target_obj, "_user", target_obj)
        
        if perlu_banner and getattr(user_obj, "banner", None) is None:
            try:
                user_obj = await self.bot.fetch_user(target_obj.id)
            except discord.HTTPException:
                pass
        
        return user_obj, member_obj
    
    async def _kirim(
        self,
        ctx: commands.Context,
        target: discord.Member | discord.User | None,
        tipe: str,
    ):
        await ctx.defer()
        
        user_obj, member_obj = await self._putuskan_user_dan_member(
            target, ctx, perlu_banner=(tipe == "banner")
        )
        container = await self.buat_container(user_obj, member_obj, tipe)
        
        view = discord.ui.LayoutView(timeout=None)
        view.add_item(container)
        await ctx.send(view=view, allowed_mentions=discord.AllowedMentions.none())
    
    # ------------------------------------------------------------------
    # Command
    # ------------------------------------------------------------------
    @commands.hybrid_command(
        name="avatar",
        description="Nampilin foto profil orang.",
        aliases=["pfp", "pp", "icon"],
    )
    @discord.app_commands.describe(member="Member atau user yang mau diliat foto profilnya (opsional)")
    async def avatar(self, ctx:commands.Context, member:discord.Member|discord.User=None):
        await self._kirim(ctx, member, "avatar")
    
    @commands.hybrid_command(
        name="banner",
        description="Nampilin foto sampul/banner profil orang.",
        aliases=["bn"],
    )
    @discord.app_commands.describe(member="Member atau user yang mau diliat bannernya (opsional)")
    async def banner(self, ctx:commands.Context, member:discord.Member|discord.User=None):
        await self._kirim(ctx, member, "banner")
    
    # ------------------------------------------------------------------
    # Error handler (berlaku untuk semua command di cog ini)
    # ------------------------------------------------------------------
    async def cog_command_error(self, ctx:commands.Context, error:Exception):
        while hasattr(error, "original"):
            error = error.original
        
        if isinstance(error, commands.MemberNotFound):
            judul = "❌ Member tidak ditemukan"
            pesan = "Pastikan nama, ID, atau @mention sudah benar."
        elif isinstance(error, commands.UserNotFound):
            judul = "❌ User tidak ditemukan"
            pesan = f"User `{error.argument}` tidak ditemukan. Coba lagi."
        elif isinstance(error, commands.BadUnionArgument):
            judul = "❌ User tidak ditemukan"
            pesan = "Pastikan nama, ID, atau @mention sudah benar."
        else:
            log.error(
                "Error tak terduga di command %s",
                ctx.command,
                exc_info=(type(error), error, error.__traceback__),
            )
            judul = "❌ Terjadi Kesalahan"
            pesan = "Ada error internal. Coba lagi sebentar lagi ya."
        
        view = discord.ui.LayoutView(timeout=None)
        view.add_item(_container_pesan(f"### {judul}", pesan, warna=pengaturan.warna_merah))
        
        try:
            await ctx.send(view=view)
        except discord.HTTPException:
            await ctx.send(f"**{judul}**\n{pesan}")


async def setup(bot:commands.Bot):
    await bot.add_cog(PFP(bot))