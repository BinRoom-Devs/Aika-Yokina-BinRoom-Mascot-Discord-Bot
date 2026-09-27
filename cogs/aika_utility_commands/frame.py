import asyncio
import io
from functools import lru_cache

import aiohttp
import discord
from discord.ext import commands
from PIL import Image


class LihatFrame(discord.ui.LayoutView):
    def __init__(self, cog: "AvatarDecoration", ctx: commands.Context, user: discord.User | discord.Member):
        super().__init__(timeout=180)
        self.cog = cog
        self.ctx = ctx
        self.user = user
        self.message = None

    async def buat_container(self) -> discord.ui.Container:
        decoration = self.user.avatar_decoration

        if not decoration:
            container = discord.ui.Container()
            container.add_item(discord.ui.TextDisplay(content="## Frame Tidak Ada"))
            container.add_item(discord.ui.Separator(spacing=discord.SeparatorSpacing.small))
            container.add_item(discord.ui.TextDisplay(content=f"{self.user.mention} tidak sedang menggunakan bingkai/frame avatar (Avatar Decoration)."))
            return container

        # Mengambil asset HD (4096px) jika tersedia
        try:
            link_hd = decoration.with_size(4096).url
        except (discord.InvalidArgument, AttributeError):
            link_hd = decoration.url

        warna, _lebar_hd, tinggi_hd, beranimasi, total_frame = await self.cog.proses_aset_cached(link_hd)

        str_format = "GIF" if beranimasi else "PNG"
        
        container = discord.ui.Container(accent_color=warna)
        container.add_item(discord.ui.TextDisplay(content=f"## Frame Avatar si {self.user.mention}"))
        container.add_item(discord.ui.Separator(spacing=discord.SeparatorSpacing.small))
        container.add_item(discord.ui.MediaGallery(discord.MediaGalleryItem(link_hd)))
        container.add_item(discord.ui.Separator(spacing=discord.SeparatorSpacing.small))

        frames = f"  ·  {total_frame} frames" if beranimasi else ''
        ukuran = f"  ·  {tinggi_hd}p" if tinggi_hd else ''
        sku_id = f"  ·  `SKU: {self.user.avatar_decoration_sku_id}`" if getattr(self.user, "avatar_decoration_sku_id", None) else ''

        footer = f"-# [Link]({link_hd})  ·  {str_format}{ukuran}{frames}{sku_id}"
        container.add_item(discord.ui.TextDisplay(content=footer))

        return container


class AvatarDecoration(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self._session: aiohttp.ClientSession | None = None

    @property
    def session(self) -> aiohttp.ClientSession:
        if self._session is None or self._session.closed:
            self._session = aiohttp.ClientSession()
        return self._session

    async def cog_unload(self):
        if self._session and not self._session.closed:
            await self._session.close()

    @staticmethod
    @lru_cache(maxsize=128)
    def _proses_gambar_blocking(byte_gambar: bytes) -> tuple[int, int, int, bool, int]:
        try:
            with Image.open(io.BytesIO(byte_gambar)) as img:
                lebar, tinggi = img.size
                total_frame = getattr(img, "n_frames", 1)
                beranimasi = getattr(img, "is_animated", False) and total_frame > 1

                thumb = img.convert("RGB").resize((32, 32), Image.Resampling.NEAREST)
                quantized = thumb.quantize(colors=1)
                palette = quantized.getpalette()
                
                warna = 0
                if palette:
                    r, g, b = palette[:3]
                    warna = (r << 16) + (g << 8) + b
                if warna != 0x000000:
                    warna = 0xD675C1

                return warna, lebar, tinggi, beranimasi, total_frame
        except (Image.UnidentifiedImageError, OSError, ValueError):
            pass
        return 0xD675C1, 0, 0, False, 1

    async def proses_aset_cached(self, link_gambar: str) -> tuple[int, int, int, bool, int]:
        try:
            async with self.session.get(link_gambar) as respon:
                if respon.status != 200:
                    return 0xD675C1, 0, 0, False, 1
                byte_gambar = await respon.read()
            return await asyncio.to_thread(self._proses_gambar_blocking, byte_gambar)
        except (aiohttp.ClientError, asyncio.TimeoutError) as e:
            print(f"[Aika] Frame profil: gagal memproses gambar ({e})")
            return 0xD675C1, 0, 0, False, 1

    async def _dapatkan_user_obj(self, ctx: commands.Context, target: discord.Member | discord.User | None) -> discord.User | discord.Member:
        target_obj = target or ctx.author
        
        # Jika objek user belum terisi data dekorasi, fetch dari REST API
        if not hasattr(target_obj, "avatar_decoration") or target_obj.avatar_decoration is None:
            try:
                target_obj = await self.bot.fetch_user(target_obj.id)
            except discord.HTTPException:
                pass

        return target_obj

    @commands.hybrid_command(
        name="frame",
        description="Nampilin frame/dekorasi avatar profil orang.",
        aliases=["decoration", "bingkai", "avatarframe"]
    )
    @discord.app_commands.describe(member="Member atau user yang mau diliat framenya (opsional)")
    async def frame(self, ctx: commands.Context, member: discord.Member | discord.User = None):
        await ctx.defer()

        user_obj = await self._dapatkan_user_obj(ctx, member)

        view = LihatFrame(self, ctx, user_obj)
        container = await view.buat_container()
        view.add_item(container)

        view.message = await ctx.send(view=view, allowed_mentions=discord.AllowedMentions.none())

    @frame.error
    async def frame_error(self, ctx: commands.Context, error: commands.CommandError):
        if isinstance(error, commands.CommandInvokeError):
            error = error.original

        if isinstance(error, commands.MemberNotFound):
            judul = "❌ Member tidak ditemukan"
            pesan = "Pastikan nama, ID, atau @mention sudah benar."
        elif isinstance(error, commands.UserNotFound):
            judul = "❌ User tidak ditemukan"
            pesan = f"User `{error.argument}` tidak ditemukan. Coba lagi."
        else:
            judul = "❌ Terjadi Kesalahan"
            pesan = f"Ada error internal:\n`{type(error).__name__}: {error}`"

        container = discord.ui.Container(accent_color=0xDB2E43)
        container.add_item(discord.ui.TextDisplay(content=f"### {judul}"))
        container.add_item(discord.ui.Separator(spacing=discord.SeparatorSpacing.small))
        container.add_item(discord.ui.TextDisplay(content=pesan))

        view = discord.ui.LayoutView()
        view.add_item(container)

        try:
            await ctx.send(view=view)
        except discord.HTTPException:
            await ctx.send(f"**{judul}**\n{pesan}")


async def setup(bot: commands.Bot):
    await bot.add_cog(AvatarDecoration(bot))