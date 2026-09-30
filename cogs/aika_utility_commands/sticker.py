import asyncio
import io
from functools import lru_cache

import discord
from discord.ext import commands
from PIL import Image, ImageSequence


class Sticker(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
    
    @staticmethod
    @lru_cache(maxsize=128)
    def _proses_gambar_blocking(byte_gambar:bytes) -> tuple[int, int, int, bool, int, io.BytesIO]:
        """
        Ngeproses gambar stiker di thread terpisah (Blocking Task):
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
    
    async def proses_pembesaran(self, id_stiker:int, format_type:discord.StickerFormatType):
        if format_type == discord.StickerFormatType.gif:
            format_ext = 'gif'
        elif format_type in (discord.StickerFormatType.png, discord.StickerFormatType.apng):
            format_ext = 'png'
        else:
            return None
            
        link_sticker = f'https://media.discordapp.net/stickers/{id_stiker}.{format_ext}'
        
        async with self.bot.http._HTTPClient__session.get(link_sticker) as respon:
            if respon.status != 200:
                return None
            byte_gambar = await respon.read()
        
        hasil_blocking = await asyncio.to_thread(self._proses_gambar_blocking, byte_gambar)
        return hasil_blocking, link_sticker
    
    @commands.hybrid_command(
        name='sticker',
        description='Nampilin dan stiker kustom.',
        aliases=['stiker']
    )
    async def sticker(self, ctx:commands.Context, sticker_id:str|None=None):
        await ctx.defer()
        
        target_id = None
        target_format = None
        target_name = "Stiker Kustom"
        
        if not sticker_id:
            async for msg in ctx.channel.history(limit=20):
                if msg.stickers:
                    stk = msg.stickers[0]
                    target_id = stk.id
                    target_format = stk.format
                    target_name = stk.name
                    break
            
            if not target_id:
                container = discord.ui.Container(accent_color=0xDB2E43)
                container.add_item(discord.ui.TextDisplay(content="### ❌ Stiker Tidak Ditemukan"))
                container.add_item(discord.ui.Separator(spacing=discord.SeparatorSpacing.small))
                container.add_item(discord.ui.TextDisplay(content="Gak ada stiker baru-baru ini di chat. Coba masukin ID stiker secara manual."))
                await ctx.send(view=discord.ui.LayoutView().add_item(container))
                return
        else:
            if not sticker_id.isdigit():
                container = discord.ui.Container(accent_color=0xDB2E43)
                container.add_item(discord.ui.TextDisplay(content="### ❌ ID Tidak Valid"))
                container.add_item(discord.ui.Separator(spacing=discord.SeparatorSpacing.small))
                container.add_item(discord.ui.TextDisplay(content="ID Stiker harus berupa deretan angka."))
                await ctx.send(view=discord.ui.LayoutView().add_item(container))
                return
                
            target_id = int(sticker_id)
            try:
                stk = await self.bot.fetch_sticker(target_id)
                target_format = stk.format
                target_name = stk.name
            except discord.HTTPException:
                target_format = discord.StickerFormatType.png
        
        async with ctx.typing():
            respons_proses = await self.proses_pembesaran(target_id, target_format)
            
            if not respons_proses:
                container = discord.ui.Container(accent_color=0xDB2E43)
                container.add_item(discord.ui.TextDisplay(content="### ❌ Format Stiker Tidak Didukung"))
                container.add_item(discord.ui.Separator(spacing=discord.SeparatorSpacing.small))
                container.add_item(discord.ui.TextDisplay(content="Aika belum bisa memproses stiker resmi bertipe Lottie/Animasi bawaan Discord."))
                await ctx.send(view=discord.ui.LayoutView().add_item(container))
                return
            
            hasil, link_sticker = respons_proses
            warna, lebar, Component_tinggi, beranimasi, total_frame, buffer_file = hasil
            
            str_format = "GIF" if beranimasi else "PNG"
            file_name = f"sticker_diperbesar.{str_format.lower()}"
            file_discord = discord.File(fp=buffer_file, filename=file_name)
            
            link_attachment = f"attachment://{file_name}"
            
            container = discord.ui.Container(accent_color=warna)
            
            container.add_item(discord.ui.TextDisplay(content=f"## Stiker: {target_name}"))
            container.add_item(discord.ui.Separator(spacing=discord.SeparatorSpacing.small))
            
            container.add_item(discord.ui.MediaGallery(discord.MediaGalleryItem(link_attachment)))
            container.add_item(discord.ui.Separator(spacing=discord.SeparatorSpacing.small))
            
            frames_str = f"  ·  {total_frame} frames" if beranimasi else ''
            ukuran_str = f"  ·  {lebar}x{Component_tinggi}p"
            id_str = f"  ·  `{target_id}`"
            
            footer = f"-# [Link]({link_sticker})  ·  {str_format}{ukuran_str}{frames_str}{id_str}"
            container.add_item(discord.ui.TextDisplay(content=footer))
            
            await ctx.send(file=file_discord, view=discord.ui.LayoutView().add_item(container))


async def setup(bot: commands.Bot):
    await bot.add_cog(Sticker(bot))