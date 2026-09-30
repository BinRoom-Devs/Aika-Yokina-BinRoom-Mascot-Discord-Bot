import asyncio
import io
import re
from functools import lru_cache

import discord
from discord.ext import commands
from PIL import Image, ImageSequence


class Emoji(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.REGEX_EMOJI = re.compile(r'<(a)?:(\w+):(\d+)>')
    
    @staticmethod
    @lru_cache(maxsize=128)
    def _proses_gambar_blocking(byte_gambar:bytes) -> tuple[int, int, int, bool, int, io.BytesIO]:
        """
        Ngeproses gambar di thread terpisah (Blocking Task):
        - Ngebaca warna dominan (Quantization 1 warna)
        - Ngehitung metadata ukuran gambar & total frame kalo animated
        - Ngegedein gambarnya (Upscaling)
        """
        try:
            with Image.open(io.BytesIO(byte_gambar)) as img:
                lebar_asli, tinggi_asli = img.size
                total_frame = getattr(img, "n_frames", 1)
                beranimasi = getattr(img, "is_animated", False) and total_frame > 1
                format_gmbr = img.format if img.format else 'PNG'
                
                thumb = img.convert("RGB").resize((32, 32), Image.Resampling.NEAREST)
                quantized = thumb.quantize(colors=1)
                palette = quantized.getpalette()
                
                warna = 0xD675C1 
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
                        frame.convert('RGBA').resize(ukuran_baru, resample=Image.Resampling.NEAREST)
                        for frame in ImageSequence.Iterator(img)
                    ]
                    frames[0].save(
                        buffer_hasil,
                        format='GIF',
                        save_all=True,
                        append_images=frames[1:],
                        loop=loop_asli,
                        duration=durasi_asli,
                        disposal=2
                    )
                else:
                    diperbesar = img.resize(ukuran_baru, resample=Image.Resampling.BILINEAR)
                    diperbesar.save(buffer_hasil, format=format_gmbr)
                
                buffer_hasil.seek(0)
                return warna, ukuran_baru[0], ukuran_baru[1], beranimasi, total_frame, buffer_hasil
        
        except (Image.UnidentifiedImageError, OSError, ValueError):
            pass
        
        return 0xD675C1, 0, 0, False, 1, io.BytesIO(byte_gambar)
    
    async def proses_pembesaran(self, emoji_str:str):
        """Ngekstrak data emoji dari teks, trus ngedownload dari CDN, abis itu dioper ke Thread Pool."""
        cocok = self.REGEX_EMOJI.match(emoji_str)
        if not cocok:
            return None
        
        bergerak = bool(cocok.group(1))
        nama_emoji = cocok.group(2)  
        id_emoji = cocok.group(3)    
        format_ext = 'gif' if bergerak else 'png'
        
        link_emoji = f'https://cdn.discordapp.com/emojis/{id_emoji}.{format_ext}?size=1024'
        
        async with self.bot.http._HTTPClient__session.get(link_emoji) as respon:
            if respon.status != 200:
                return None
            byte_gambar = await respon.read()
        
        hasil_blocking = await asyncio.to_thread(self._proses_gambar_blocking, byte_gambar)
        
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
            warna, lebar, Component_tinggi, beranimasi, total_frame, buffer_file = hasil
            
            str_format = "GIF" if beranimasi else "PNG"
            file_name = f"emoji_diperbesar.{str_format.lower()}"
            file_discord = discord.File(fp=buffer_file, filename=file_name)
            
            link_attachment = f"attachment://{file_name}"
            
            container = discord.ui.Container(accent_color=warna)
            
            container.add_item(discord.ui.TextDisplay(content=f"## Emoji :{nama_emoji}:"))
            
            container.add_item(discord.ui.Separator(spacing=discord.SeparatorSpacing.small))
            
            container.add_item(discord.ui.MediaGallery(discord.MediaGalleryItem(link_attachment)))
            
            container.add_item(discord.ui.Separator(spacing=discord.SeparatorSpacing.small))
            
            frames_str = f"  ·  {total_frame} frames" if beranimasi else ''
            ukuran_str = f"  ·  {lebar}x{Component_tinggi}p"
            id_str = f"  ·  `{id_emoji}`"
            
            footer = f"-# [Link]({link_emoji})  ·  {str_format}{ukuran_str}{frames_str}{id_str}"
            container.add_item(discord.ui.TextDisplay(content=footer))
            
            await ctx.send(file=file_discord, view=discord.ui.LayoutView().add_item(container))


async def setup(bot:commands.Bot):
    await bot.add_cog(Emoji(bot))