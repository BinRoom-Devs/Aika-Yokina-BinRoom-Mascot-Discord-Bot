import asyncio
import io
import re
import traceback
from functools import lru_cache

import aiohttp
import discord
import resvg_py
from discord.ext import commands
from PIL import Image, ImageSequence

DEFAULT_COLOR = 0xD675C1
TWEMOJI_BASE = 'https://cdn.jsdelivr.net/gh/jdecked/twemoji@15.1.0/assets/svg'


def _render_svg_resvg(byte_gambar:bytes, target_size:int=512) -> bytes:
    """Render SVG ke PNG via resvg_py (butuh string, bukan bytes)."""
    svg_string = byte_gambar.decode('utf-8')
    hasil = resvg_py.svg_to_bytes(
        svg_string=svg_string,
        width=target_size,
        height=target_size,
    )
    return bytes(hasil)


@lru_cache(maxsize=128)
def _proses_gambar_blocking(byte_gambar:bytes, is_svg:bool=False) -> tuple[int, int, int, bool, int, bytes]:
    """
    Ngeproses gambar (blocking, dijalanin di thread terpisah).
    Return bytes (bukan BytesIO) biar aman di-cache, BytesIO dibikin per-pemanggilan.
    """
    try:
        if is_svg:
            png_bytes = _render_svg_resvg(byte_gambar, target_size=512)
            img = Image.open(io.BytesIO(png_bytes))
        else:
            img = Image.open(io.BytesIO(byte_gambar))
        
        lebar_asli, tinggi_asli = img.size
        total_frame = getattr(img, "n_frames", 1)
        beranimasi = getattr(img, "is_animated", False) and total_frame > 1
        format_gmbr = getattr(img, "format", "PNG") or "PNG"
        
        rgba = img.convert("RGBA")
        bg = Image.new("RGBA", rgba.size, (255, 255, 255, 255))
        thumb = Image.alpha_composite(bg, rgba).convert("RGB").resize((32, 32), Image.Resampling.NEAREST)
        quantized = thumb.quantize(colors=1)
        palette = quantized.getpalette()
        
        warna = DEFAULT_COLOR
        if palette:
            r, g, b = palette[:3]
            warna = (r << 16) + (g << 8) + b
        
        ukuran_max = 512
        if lebar_asli > tinggi_asli:
            skala = ukuran_max / lebar_asli
            ukuran_baru = (ukuran_max, int(tinggi_asli * skala))
        else:
            skala = ukuran_max / tinggi_asli
            ukuran_baru = (int(lebar_asli * skala), ukuran_max)
        
        buffer_hasil = io.BytesIO()
        
        if beranimasi or format_gmbr == 'GIF':
            durasi_asli = img.info.get('duration', 100)
            loop_asli = img.info.get('loop', 0)
            
            frames = [
                frame.convert('RGBA').resize(ukuran_baru, resample=Image.Resampling.LANCZOS)
                for frame in ImageSequence.Iterator(img)
            ]
            frames[0].save(
                buffer_hasil,
                format='GIF',
                save_all=True,
                append_images=frames[1:],
                loop=loop_asli,
                duration=durasi_asli,
                disposal=2,
            )
        else:
            if not is_svg:
                img = img.resize(ukuran_baru, resample=Image.Resampling.LANCZOS)
            img.save(buffer_hasil, format='PNG')
        
        return warna, ukuran_baru[0], ukuran_baru[1], beranimasi, total_frame, buffer_hasil.getvalue()
    
    except Exception:  # noqa: BLE001
        print("[Emoji Cog Error]")
        traceback.print_exc()
    
    return DEFAULT_COLOR, 0, 0, False, 1, byte_gambar


class Emoji(commands.Cog):
    def __init__(self, bot:commands.Bot):
        self.bot = bot
        self.REGEX_EMOJI = re.compile(r'<(a)?:(\w+):(\d+)>')
        self.session: aiohttp.ClientSession | None = None
    
    async def cog_load(self):
        self.session = aiohttp.ClientSession()
    
    async def cog_unload(self):
        if self.session:
            await self.session.close()
    
    async def _download(self, url:str) -> bytes | None:
        async with self.session.get(url) as respon:
            if respon.status != 200:
                return None
            return await respon.read()
    
    async def proses_pembesaran(self, emoji_str:str):
        """Ngekstrak data emoji dari teks, ngedownload dari CDN, trus dioper ke Thread Pool."""
        cocok = self.REGEX_EMOJI.match(emoji_str)
        is_svg = False
        
        if cocok:
            bergerak = bool(cocok.group(1))
            nama_emoji = cocok.group(2)
            id_emoji = cocok.group(3)
            format_ext = 'gif' if bergerak else 'png'
            
            link_emoji = f'https://cdn.discordapp.com/emojis/{id_emoji}.{format_ext}?size=1024'
            byte_gambar = await self._download(link_emoji)
        else:
            emoji_str = emoji_str.strip()
            chars = [ord(c) for c in emoji_str]
            if not chars:
                return None
            
            tanpa_fe0f = "-".join(f"{c:x}" for c in chars if c != 0xFE0F)
            dengan_fe0f = "-".join(f"{c:x}" for c in chars)
            
            is_svg = True
            nama_emoji = emoji_str
            byte_gambar = None
            id_emoji = tanpa_fe0f
            link_emoji = None
            
            for kandidat in dict.fromkeys([tanpa_fe0f, dengan_fe0f]):  # unik, urutan terjaga
                if not kandidat:
                    continue
                url = f'{TWEMOJI_BASE}/{kandidat}.svg'
                data = await self._download(url)
                if data:
                    byte_gambar, id_emoji, link_emoji = data, kandidat, url
                    break
        
        if not byte_gambar:
            return None
        
        hasil_blocking = await asyncio.to_thread(_proses_gambar_blocking, byte_gambar, is_svg)
        
        return hasil_blocking, nama_emoji, id_emoji, link_emoji
    
    @commands.hybrid_command(name='emoji', description='Nampilin emoji.')
    async def emoji(self, ctx:commands.Context, emoji:str):
        await ctx.defer()
        
        async with ctx.typing():
            respons_proses = await self.proses_pembesaran(emoji)
            
            if not respons_proses:
                container = discord.ui.Container(accent_color=0xDB2E43)
                container.add_item(discord.ui.TextDisplay(content="### ❌ Emoji Tidak Valid"))
                container.add_item(discord.ui.Separator(spacing=discord.SeparatorSpacing.small))
                container.add_item(discord.ui.TextDisplay(content="Coba pastiin emoji yang dimasukin beneran valid."))
                await ctx.send(view=discord.ui.LayoutView().add_item(container))
                return
            
            hasil, nama_emoji, id_emoji, link_emoji = respons_proses
            warna, lebar, tinggi, beranimasi, total_frame, data_file = hasil
            
            if lebar == 0 or tinggi == 0:
                container = discord.ui.Container(accent_color=0xDB2E43)
                container.add_item(discord.ui.TextDisplay(content="### ❌ Gagal Memproses Gambar"))
                container.add_item(discord.ui.Separator(spacing=discord.SeparatorSpacing.small))
                container.add_item(discord.ui.TextDisplay(content="Gagal mengonversi atau membaca data gambar emoji."))
                await ctx.send(view=discord.ui.LayoutView().add_item(container))
                return
            
            str_format = "GIF" if beranimasi else "PNG"
            file_name = f"emoji_diperbesar.{str_format.lower()}"
            file_discord = discord.File(fp=io.BytesIO(data_file), filename=file_name)
            
            link_attachment = f"attachment://{file_name}"
        
            container = discord.ui.Container(accent_color=warna)
            
            title = f"## Emoji :{nama_emoji}:" if nama_emoji != emoji else f"## Emoji {emoji}"
            container.add_item(discord.ui.TextDisplay(content=title))
            
            container.add_item(discord.ui.Separator(spacing=discord.SeparatorSpacing.small))
            container.add_item(discord.ui.MediaGallery(discord.MediaGalleryItem(link_attachment)))
            container.add_item(discord.ui.Separator(spacing=discord.SeparatorSpacing.small))
            
            frames_str = f"  ·  {total_frame} frames" if beranimasi else ''
            ukuran_str = f"  ·  {lebar}x{tinggi}p"
            id_str = f"  ·  `{id_emoji}`"
            
            footer = f"-# [Link]({link_emoji})  ·  {str_format}{ukuran_str}{frames_str}{id_str}"
            container.add_item(discord.ui.TextDisplay(content=footer))
            
            await ctx.send(file=file_discord, view=discord.ui.LayoutView().add_item(container))


async def setup(bot:commands.Bot):
    await bot.add_cog(Emoji(bot))