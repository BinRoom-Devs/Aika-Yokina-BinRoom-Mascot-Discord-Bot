import asyncio
import io
import re
import time
from collections import deque

import aiohttp
import discord
from discord.ext import commands, tasks

from config import pengaturan

BATAS_UKURAN_ATTACHMENT = 8 * 1024 * 1024
BATAS_UKURAN_BYTE = 15 * 1024 * 1024
BUDGET_BYTE_GLOBAL = 128 * 1024 * 1024
DOWNLOAD_TIMEOUT = 2.5
BATAS_KADALUARSA_SNIPE = 300
MAX_SNIPES_PER_CHANNEL = 5
MAX_ATTACHMENT_PER_PESAN = 10
BATAS_TEKS_KONTEN = 3500
TTL_CACHE_CDN = 300
MAX_UKURAN_CACHE = 1000

FORMAT_GAMBAR = ('.png', '.jpg', '.jpeg', '.gif', '.webp', '.bmp', '.svg')
FORMAT_VIDEO = ('.mp4', '.webm', '.mov', '.avi', '.mkv', '.flv', '.wmv', '.m4v', '.3gp', '.ogv')

CDN_LINK_RE = re.compile(r'https?://(?:cdn\.discordapp\.com|media\.discordapp\.net)/[^\s]+')
DISCORD_EMOJI_RE = re.compile(r'<a?:[a-zA-Z0-9_]+:\d+>')
EMOJI_SINGLE_RE = re.compile(
    r'(?:'
    r'[\U0001F1E6-\U0001F1FF]{2}'
    r'|'
    r'[0-9#*]\uFE0F?\u20E3'
    r'|'
    r'(?:[\U0001F600-\U0001F64F\U0001F300-\U0001F5FF\U0001F680-\U0001F6FF\U0001FA70-\U0001FAFF\U0001FA00-\U0001FA6F\U00002600-\U000027BF\U00002300-\U000023FF\U00002B00-\U00002BFF])'
    r'[\uFE0F\u200D\U0001F3FB-\U0001F3FF]*'
    r')'
)

CACHE_VALIDASI_CDN: dict[str, tuple[float, bool]] = {}
CACHE_WARNA_AVATAR: dict[str, int] = {}


def _adalah_gambar(content_type:str|None, filename:str) -> bool:
    return (content_type or "").startswith("image/") or filename.lower().endswith(FORMAT_GAMBAR)


def _adalah_video(content_type:str|None, filename:str) -> bool:
    return (content_type or "").startswith("video/") or filename.lower().endswith(FORMAT_VIDEO)


def _url_avatar_kecil(avatar: discord.Asset) -> str:
    try:
        return avatar.replace(size=32, format="png").url
    except ValueError:
        return avatar.url


def potong_teks(teks:str, batas:int=BATAS_TEKS_KONTEN) -> str:
    if len(teks) <= batas:
        return teks
    return teks[:batas - 1].rstrip() + "…"


def _proses_gambar_warnadominan(byte_gambar:bytes) -> int:
    from PIL import Image
    
    try:
        with Image.open(io.BytesIO(byte_gambar)) as img:
            img.draft("RGB", (64, 64))
            try:
                resample = Image.Resampling.NEAREST
            except AttributeError:
                resample = Image.NEAREST
            thumb = img.convert("RGB").resize((32, 32), resample)
            palette = thumb.quantize(colors=1).getpalette()
            
            if palette:
                r, g, b = palette[:3]
                return (r << 16) + (g << 8) + b
    except (Image.UnidentifiedImageError, Image.DecompressionBombError, OSError, ValueError):
        pass
    return pengaturan.warna_aika


async def cari_warna_dominan(session:aiohttp.ClientSession, url:str) -> int | None:
    try:
        async with session.get(url, timeout=aiohttp.ClientTimeout(total=DOWNLOAD_TIMEOUT)) as resp:
            if resp.status == 200:
                data = await resp.read()
                return await asyncio.to_thread(_proses_gambar_warnadominan, data)
    except (TimeoutError, aiohttp.ClientError):
        pass
    return None


async def cari_warna_avatar(session:aiohttp.ClientSession, author:dict) -> int:
    kunci = author["avatar_key"]
    warna = CACHE_WARNA_AVATAR.get(kunci)
    if warna is None:
        warna = await cari_warna_dominan(session, author["avatar_kecil_url"])
        if warna is None:
            return pengaturan.warna_aika
        CACHE_WARNA_AVATAR[kunci] = warna
    return warna


async def hitung_warna_entry(session:aiohttp.ClientSession, data:dict) -> int:
    for att in data["attachments"]:
        if att.get("bytes") and _adalah_gambar(att["content_type"], att["filename"]):
            warna = await asyncio.to_thread(_proses_gambar_warnadominan, att["bytes"])
            if warna != pengaturan.warna_aika:
                return warna
    return await cari_warna_avatar(session, data["author"])


def format_jumboji(text: str) -> str:
    if not text:
        return text
    
    stripped = text.strip()
    if not stripped:
        return text
    
    emoji_kustom = DISCORD_EMOJI_RE.findall(stripped)
    text_no_custom = DISCORD_EMOJI_RE.sub('', stripped)
    
    if any(char.isalnum() for char in text_no_custom):
        return text
    
    unicode_emojis = EMOJI_SINGLE_RE.findall(text_no_custom)
    text_no_emoji = EMOJI_SINGLE_RE.sub('', text_no_custom)
    
    remaining_text = re.sub(r'\s+', '', text_no_emoji)
    is_emoji_only = not remaining_text
    
    total_emoji_count = len(emoji_kustom) + len(unicode_emojis)
    
    if is_emoji_only and 1 <= total_emoji_count <= 30 and not stripped.startswith('# '):
        return f'# {stripped}'
    
    return text


async def check_valid_cdn_url(session:aiohttp.ClientSession, url:str) -> bool:
    sekarang = time.monotonic()
    cache = CACHE_VALIDASI_CDN.get(url)
    if cache and cache[0] > sekarang:
        return cache[1]
    try:
        async with session.head(url, timeout=aiohttp.ClientTimeout(total=1.5), allow_redirects=True) as resp:
            is_valid = resp.status == 200
    except (TimeoutError, aiohttp.ClientError):
        return False
    CACHE_VALIDASI_CDN[url] = (sekarang + TTL_CACHE_CDN, is_valid)
    return is_valid


class SnipeView(discord.ui.LayoutView):
    def __init__(self, ctx:commands.Context, snipes:list[dict], http_session:aiohttp.ClientSession):
        super().__init__(timeout=120)
        self.ctx = ctx
        self.snipes = snipes
        self.http_session = http_session
        self.current_page = 0
        self.total_pages = len(snipes)
        self.message = None
        self._lock = asyncio.Lock()
    
    async def _cari_warna_snipe(self, sniped_data:dict) -> discord.Color:
        warna = sniped_data.get("dominant_color")
        if warna is None:
            warna = await hitung_warna_entry(self.http_session, sniped_data)
            sniped_data["dominant_color"] = warna
        return discord.Color(warna or pengaturan.warna_aika)
    
    def _buat_row(self) -> discord.ui.ActionRow:
        row = discord.ui.ActionRow()
        
        btn_prev = discord.ui.Button(
            label="◀",
            style=discord.ButtonStyle.primary,
            custom_id="snipe_prev",
            disabled=(self.current_page == 0)
        )
        btn_prev.callback = self.prev_callback
        
        btn_ind = discord.ui.Button(
            label=f"{self.current_page + 1}/{self.total_pages}",
            style=discord.ButtonStyle.secondary,
            custom_id="snipe_indicator",
            disabled=True
        )
        
        btn_next = discord.ui.Button(
            label="▶",
            style=discord.ButtonStyle.primary,
            custom_id="snipe_next",
            disabled=(self.current_page == self.total_pages - 1)
        )
        btn_next.callback = self.next_callback
        
        btn_close = discord.ui.Button(
            label="Tutup",
            style=discord.ButtonStyle.danger,
            custom_id="snipe_close"
        )
        btn_close.callback = self.close_callback
        
        row.add_item(btn_prev)
        row.add_item(btn_ind)
        row.add_item(btn_next)
        row.add_item(btn_close)
        return row
    
    async def setup_layout(self) -> list[discord.File]:
        sniped_data = self.snipes[self.current_page]
        color = await self._cari_warna_snipe(sniped_data)
        
        container = discord.ui.Container(accent_color=color)
        unix_ts = int(sniped_data["created_at"].timestamp())
        
        raw_content = sniped_data.get("content")
        stickers = sniped_data.get("stickers", [])
        
        if raw_content:
            content_text = potong_teks(format_jumboji(raw_content))
        elif stickers:
            sticker_names = [st["name"] if isinstance(st, dict) else str(st) for st in stickers]
            content_text = f"*[Sticker: {', '.join(sticker_names)}]*"
        else:
            content_text = "*[Pesan gak berisi teks]*"
        
        author = sniped_data["author"]
        
        container.add_item(discord.ui.TextDisplay("### 🗑️ Pesan yang Baru Saja Dihapus (5 Menit Terakhir)"))
        container.add_item(discord.ui.Separator(visible=True, spacing=discord.SeparatorSpacing.small))
        container.add_item(
            discord.ui.Section(
                discord.ui.TextDisplay(f"-# Pengirim: {author['mention']}\n\n{content_text}"),
                accessory=discord.ui.Thumbnail(media=author["avatar_url"])
            )
        )
        
        attachments = sniped_data.get("attachments", [])
        files = []
        media_items = []
        file_components = []
        
        for st in stickers:
            if isinstance(st, dict) and st.get("url"):
                media_items.append(discord.MediaGalleryItem(media=st["url"], description=f"Sticker: {st['name']}"))
        
        if raw_content:
            url_cdn = list(dict.fromkeys(CDN_LINK_RE.findall(raw_content)))[:MAX_ATTACHMENT_PER_PESAN]
            if url_cdn:
                hasil_cek = await asyncio.gather(*(check_valid_cdn_url(self.http_session, u) for u in url_cdn))
                
                for url, is_valid in zip(url_cdn, hasil_cek):
                    if is_valid:
                        clean_url = url.split('?')[0].lower()
                        if clean_url.endswith(FORMAT_GAMBAR) or clean_url.endswith(FORMAT_VIDEO) or "/avatars/" in clean_url or "/emojis/" in clean_url:
                            media_items.append(discord.MediaGalleryItem(media=url))
        
        for idx, att in enumerate(attachments[:MAX_ATTACHMENT_PER_PESAN]):
            filename = f"{idx + 1}_{att['filename']}" if len(attachments) > 1 else att['filename']
            
            if att.get("bytes"):
                files.append(discord.File(io.BytesIO(att["bytes"]), filename=filename))
                media_target = f"attachment://{filename}"
            elif att.get("url"):
                media_target = att["url"]
            else:
                continue
            
            if _adalah_gambar(att.get("content_type"), att["filename"]) or _adalah_video(att.get("content_type"), att["filename"]):
                media_items.append(discord.MediaGalleryItem(
                    media=media_target,
                    description=att['filename'],
                    spoiler=att.get("spoiler", False)
                ))
            else:
                file_components.append(discord.ui.File(media_target))
        
        if media_items:
            container.add_item(discord.ui.MediaGallery(*media_items[:MAX_ATTACHMENT_PER_PESAN]))
        
        for fc in file_components:
            container.add_item(fc)
        
        container.add_item(discord.ui.Separator(visible=True, spacing=discord.SeparatorSpacing.small))
        container.add_item(discord.ui.TextDisplay(f"-# Dikirim pada pukul <t:{unix_ts}:T> (<t:{unix_ts}:R>)"))
        
        row = self._buat_row()
        
        self.clear_items()
        self.add_item(container)
        self.add_item(row)
        
        return files
    
    async def interaction_check(self, interaction:discord.Interaction) -> bool:
        if interaction.user.id != self.ctx.author.id:
            await interaction.response.send_message("Cuma yang ngetik command yang bisa ngatur tampilan ini ya! 💢", ephemeral=True)
            return False
        return True
    
    async def _ganti_halaman(self, interaction:discord.Interaction, arah:int):
        await interaction.response.defer()
        async with self._lock:
            halaman_baru = self.current_page + arah
            if not 0 <= halaman_baru < self.total_pages:
                return
            self.current_page = halaman_baru
            files = await self.setup_layout()
            await interaction.edit_original_response(
                attachments=files,
                view=self,
                allowed_mentions=discord.AllowedMentions.none()
            )
    
    async def prev_callback(self, interaction:discord.Interaction):
        await self._ganti_halaman(interaction, -1)
    
    async def next_callback(self, interaction:discord.Interaction):
        await self._ganti_halaman(interaction, +1)
    
    async def close_callback(self, interaction:discord.Interaction):
        self.stop()
        await interaction.response.defer()
        await interaction.message.delete()
    
    async def on_timeout(self):
        for item in self.walk_children():
            if isinstance(item, discord.ui.Button):
                item.disabled = True
        try:
            if self.message:
                await self.message.edit(view=self, allowed_mentions=discord.AllowedMentions.none())
        except discord.HTTPException:
            pass


class Snipe(commands.Cog):
    def __init__(self, bot:commands.Bot):
        self.bot = bot
        self.snipes: dict[int, deque] = {}
        self.session: aiohttp.ClientSession | None = None
    
    async def cog_load(self):
        self.session = aiohttp.ClientSession()
        self.clean_expired_snipes.start()
    
    async def cog_unload(self):
        self.clean_expired_snipes.cancel()
        if self.session:
            await self.session.close()
    
    @staticmethod
    def _kadaluarsa(entry:dict, sekarang) -> bool:
        return (sekarang - entry["deleted_at"]).total_seconds() > BATAS_KADALUARSA_SNIPE
    
    def _pakai_byte(self) -> int:
        return sum(
            len(att["bytes"])
            for antrean in self.snipes.values()
            for entry in antrean
            for att in entry["attachments"]
            if att["bytes"]
        )
    
    @tasks.loop(minutes=2)
    async def clean_expired_snipes(self):
        now = discord.utils.utcnow()
        expired_channels = []
        for channel_id, channel_snipes in list(self.snipes.items()):
            while channel_snipes and self._kadaluarsa(channel_snipes[-1], now):
                channel_snipes.pop()
            if not channel_snipes:
                expired_channels.append(channel_id)
        
        for channel_id in expired_channels:
            self.snipes.pop(channel_id, None)
        
        sekarang = time.monotonic()
        for url in [u for u, (exp, _) in CACHE_VALIDASI_CDN.items() if exp <= sekarang]:
            CACHE_VALIDASI_CDN.pop(url, None)
        if len(CACHE_VALIDASI_CDN) > MAX_UKURAN_CACHE:
            CACHE_VALIDASI_CDN.clear()
        if len(CACHE_WARNA_AVATAR) > MAX_UKURAN_CACHE:
            CACHE_WARNA_AVATAR.clear()
    
    def _get_valid_snipes(self, channel_id:int) -> list[dict]:
        snipes = self.snipes.get(channel_id)
        if not snipes:
            return []
        
        now = discord.utils.utcnow()
        while snipes and self._kadaluarsa(snipes[-1], now):
            snipes.pop()
        
        if not snipes:
            self.snipes.pop(channel_id, None)
            return []
        
        return list(snipes)
    
    @commands.Cog.listener()
    async def on_message_delete(self, message:discord.Message):
        if not message.author or message.author.bot or not message.guild:
            return
        
        avatar = message.author.display_avatar
        
        daftar_att = message.attachments[:MAX_ATTACHMENT_PER_PESAN]
        cached_attachments = [
            {
                "filename": att.filename,
                "content_type": att.content_type,
                "url": att.url,
                "bytes": None,
                "spoiler": att.is_spoiler()
            }
            for att in daftar_att
        ]
        
        cached_stickers = [
            {
                "id": s.id,
                "name": s.name,
                "url": s.url,
                "format": str(getattr(s, "format", ""))
            }
            for s in message.stickers
        ]
        
        snipe_entry = {
            "id": message.id,
            "author": {
                "id": message.author.id,
                "name": str(message.author),
                "avatar_url": avatar.url,
                "avatar_key": avatar.key,
                "avatar_kecil_url": _url_avatar_kecil(avatar),
                "mention": message.author.mention
            },
            "content": message.content,
            "stickers": cached_stickers,
            "created_at": message.created_at,
            "deleted_at": discord.utils.utcnow(),
            "attachments": cached_attachments
        }
        
        antrean_snipe = self.snipes.setdefault(message.channel.id, deque(maxlen=MAX_SNIPES_PER_CHANNEL))
        antrean_snipe.appendleft(snipe_entry)
        
        batas_pesan = min(BATAS_UKURAN_BYTE, max(0, BUDGET_BYTE_GLOBAL - self._pakai_byte()))
        total_bytes = 0
        antrean_unduh = []
        
        for att, cache in zip(daftar_att, cached_attachments):
            if att.size <= BATAS_UKURAN_ATTACHMENT and total_bytes + att.size <= batas_pesan:
                total_bytes += att.size
                antrean_unduh.append((cache, asyncio.wait_for(att.read(), timeout=DOWNLOAD_TIMEOUT)))
        
        if antrean_unduh:
            hasil = await asyncio.gather(*(coro for _, coro in antrean_unduh), return_exceptions=True)
            for (cache, _), res in zip(antrean_unduh, hasil):
                if isinstance(res, bytes):
                    cache["bytes"] = res
    
    @commands.hybrid_command(
        name="snipe",
        description="Ngintip hingga 5 pesan yang baru aja dihapus."
    )
    async def snipe(self, ctx: commands.Context):
        async with ctx.typing():
            sniped_list = self._get_valid_snipes(ctx.channel.id)
            
            if not sniped_list:
                await ctx.reply("Gak ada pesan yang baru dihapus di channel ini.")
                return
            
            view = SnipeView(ctx, sniped_list, self.session)
            files = await view.setup_layout()
            
            msg = await ctx.reply(files=files, view=view, allowed_mentions=discord.AllowedMentions.none())
            view.message = msg


async def setup(bot:commands.Bot):
    await bot.add_cog(Snipe(bot))