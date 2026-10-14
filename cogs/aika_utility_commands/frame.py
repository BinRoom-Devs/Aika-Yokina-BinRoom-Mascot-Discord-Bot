import asyncio
import io

import aiohttp
import discord
from discord.ext import commands

from config import pengaturan


class LihatFrame(discord.ui.LayoutView):
    def __init__(
        self,
        cog: AvatarDecoration,
        ctx: commands.Context,
        user: discord.User | discord.Member,
        filename: str,
        warna: int,
        beranimasi: bool,
        total_frame: int,
        tinggi_hd: int
    ):
        super().__init__(timeout=180)
        self.cog = cog
        self.ctx = ctx
        self.user = user
        self.message = None
        
        str_format = "GIF" if beranimasi else "PNG"
        
        container = discord.ui.Container(accent_color=warna)
        container.add_item(discord.ui.TextDisplay(content=f"## Frame Avatar si {self.user.mention}"))
        container.add_item(discord.ui.Separator(spacing=discord.SeparatorSpacing.small))
        
        container.add_item(discord.ui.MediaGallery(discord.MediaGalleryItem(media=f"attachment://{filename}")))
        
        container.add_item(discord.ui.Separator(spacing=discord.SeparatorSpacing.small))
        
        frames = f"  ·  {total_frame} frames" if beranimasi else ''
        ukuran = f"  ·  {tinggi_hd}p" if tinggi_hd else ''
        sku_id = f"  ·  `SKU: {self.user.avatar_decoration_sku_id}`" if getattr(self.user, "avatar_decoration_sku_id", None) else ''
        
        decoration = self.user.avatar_decoration
        link_hd = decoration.with_size(4096).url if decoration else ""
        
        footer = f"-# [Link Asli]({link_hd})  ·  {str_format}{ukuran}{frames}{sku_id}"
        container.add_item(discord.ui.TextDisplay(content=footer))
        
        self.add_item(container)


class AvatarDecoration(commands.Cog):
    def __init__(self, bot:commands.Bot):
        self.bot = bot
        self._session: aiohttp.ClientSession | None = None
    
    @property
    def session(self) -> aiohttp.ClientSession:
        if self._session is None or self._session.closed:
            self._session = aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=10))
        return self._session
    
    async def cog_unload(self):
        if self._session and not self._session.closed:
            await self._session.close()
    
    @staticmethod
    def _proses_bingkai_blocking(frame_bytes:bytes) -> tuple[bytes, str, int, int, bool, int]:
        from PIL import Image
        
        canvas_size = 256
        
        try:
            with Image.open(io.BytesIO(frame_bytes)) as frame_img:
                _lebar, tinggi = frame_img.size
                frame_animated = getattr(frame_img, "is_animated", False)
                frame_n_frames = getattr(frame_img, "n_frames", 1) if frame_animated else 1
                frame_duration = frame_img.info.get('duration', 40)
                
                try:
                    resample = Image.Resampling.LANCZOS
                except AttributeError:
                    resample = Image.LANCZOS
                
                img_base = frame_img
                if frame_img.mode != "RGBA":
                    try:
                        img_base = frame_img.convert("RGBA")
                    except Exception:  # noqa: BLE001, S110
                        pass
                
                thumb = img_base.resize((32, 32), resample)
                quantized = thumb.quantize(colors=1)
                palette = quantized.getpalette()
                
                warna = 0
                if palette:
                    r, g, b = palette[:3]
                    warna = (r << 16) + (g << 8) + b
                if warna == 0x000000:
                    warna = pengaturan.warna_aika
                
                if not frame_animated or frame_n_frames <= 1:
                    base = Image.new("RGBA", (canvas_size, canvas_size), (0, 0, 0, 0))
                    with img_base.convert("RGBA") as f_img:
                        f_img = f_img.resize((canvas_size, canvas_size), resample)
                        base.paste(f_img, (0, 0), f_img)
                    
                    output = io.BytesIO()
                    base.save(output, format="PNG")
                    output.seek(0)
                    return output.read(), "frame_only.png", warna, tinggi, False, 1
                
                frames_output = []
                for i in range(frame_n_frames):
                    base = Image.new("RGBA", (canvas_size, canvas_size), (0, 0, 0, 0))
                    frame_img.seek(i)
                    
                    curr_source = frame_img
                    if frame_img.mode != "RGBA":
                        try:
                            curr_source = frame_img.convert("RGBA")
                        except Exception:  # noqa: BLE001, S110
                            pass
                    
                    curr_frame = curr_source.resize((canvas_size, canvas_size), resample)
                    base.paste(curr_frame, (0, 0), curr_frame)
                    
                    p_frame = base.convert("P", palette=Image.Palette.ADAPTIVE, colors=256, dither=Image.Dither.FLOYDSTEINBERG)
                    
                    alpha = base.split()[3]
                    mask_transparan = alpha.point(lambda p: 255 if p < 128 else 0)
                    p_frame.paste(255, mask_transparan)
                    
                    frames_output.append(p_frame)
                
                output = io.BytesIO()
                if frames_output:
                    frames_output[0].save(
                        output,
                        format="GIF",
                        save_all=True,
                        append_images=frames_output[1:],
                        duration=frame_duration,
                        loop=0,
                        transparency=255,
                        disposal=2
                    )
                output.seek(0)
                return output.read(), "frame_only.gif", warna, tinggi, True, frame_n_frames
            
        except Exception:  # noqa: BLE001
            return frame_bytes, "frame_error.png", pengaturan.warna_aika, 0, False, 1
    
    async def _unduh_bytes(self, url: str) -> bytes | None:
        try:
            async with self.session.get(url) as resp:
                if resp.status == 200:
                    return await resp.read()
        except Exception:  # noqa: BLE001, S110
            pass
        return None
    
    async def _baca_user_obj(
        self,
        ctx: commands.Context,
        target: discord.Member | discord.User | None
    ) -> discord.User | discord.Member:
        target_obj = target or ctx.author
        if not hasattr(target_obj, "avatar_decoration") or target_obj.avatar_decoration is None:
            try:
                target_obj = await self.bot.fetch_user(target_obj.id)
            except discord.HTTPException:
                pass
        return target_obj
    
    @commands.hybrid_command(
        name="frame",
        description="Nampilin frame/dekorasi avatar profil orang (hanya bingkai).",
        aliases=["decoration", "bingkai", "avatarframe"]
    )
    @discord.app_commands.describe(member="Member atau user yang mau diliat framenya (opsional)")
    async def frame(self, ctx:commands.Context, member:discord.Member|discord.User=None):
        async with ctx.typing():
        
            user_obj = await self._baca_user_obj(ctx, member)
            decoration = getattr(user_obj, "avatar_decoration", None)
            
            if not decoration:
                container = discord.ui.Container(accent_color=pengaturan.warna_aika)
                container.add_item(discord.ui.TextDisplay(content="## Frame Tidak Ada"))
                container.add_item(discord.ui.Separator(spacing=discord.SeparatorSpacing.small))
                container.add_item(discord.ui.TextDisplay(content=f"{user_obj.mention} tidak sedang menggunakan bingkai/frame avatar (Avatar Decoration)."))
                
                view = discord.ui.LayoutView().add_item(container)
                await ctx.send(view=view, allowed_mentions=discord.AllowedMentions.none())
                return
            
            decoration_url = decoration.with_size(4096).url
            frame_bytes = await self._unduh_bytes(decoration_url)
            
            if not frame_bytes:
                await ctx.send("Gagal mengunduh aset bingkai dari Discord.", ephemeral=True)
                return
            
            img_bytes, filename, warna, tinggi_hd, beranimasi, total_frame = await asyncio.to_thread(
                self._proses_bingkai_blocking, frame_bytes
            )
            
            file_lampiran = discord.File(io.BytesIO(img_bytes), filename=filename)
            
            view = LihatFrame(self, ctx, user_obj, filename, warna, beranimasi, total_frame, tinggi_hd)
            
            await ctx.send(
                file=file_lampiran,
                view=view,
                allowed_mentions=discord.AllowedMentions.none()
            )
    
    @frame.error
    async def frame_error(self, ctx:commands.Context, error:commands.CommandError):
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


async def setup(bot:commands.Bot):
    await bot.add_cog(AvatarDecoration(bot))