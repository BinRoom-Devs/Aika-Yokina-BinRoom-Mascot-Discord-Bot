import discord, asyncio, aiohttp, io, re
from discord.ext import commands, tasks
from collections import deque
from functools import lru_cache
from PIL import Image


BATAS_UKURAN_ATTACHMENT = 8 * 1024 * 1024   
BATAS_UKURAN_BYTE = 15 * 1024 * 1024     
DOWNLOAD_TIMEOUT = 2.5                 
BATAS_KADALUARSA_SNIPE = 300             
MAX_SNIPES_PER_CHANNEL = 5
MAX_ATTACHMENT_PER_PESAN = 10

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

CACHE_VALIDASI_CDN: dict[str,bool] = {}


def _proses_gambar_warnadominan(byte_gambar:bytes) -> int:
    try:
        with Image.open(io.BytesIO(byte_gambar)) as img:
            thumb = img.convert("RGB").resize((32, 32), Image.Resampling.NEAREST)
            quantized = thumb.quantize(colors=1)
            palette = quantized.getpalette()
            
            if palette:
                r, g, b = palette[:3]
                return (r<<16) + (g<<8) + b
    except Exception:
        pass
    return 0xD675C1

async def cari_warna_dominan(session:aiohttp.ClientSession, url:str) -> int:
    try:
        async with session.get(url, timeout=aiohttp.ClientTimeout(total=DOWNLOAD_TIMEOUT)) as resp:
            if resp.status == 200:
                data = await resp.read()
                return await asyncio.to_thread(_proses_gambar_warnadominan, data)
    except Exception:
        pass
    return 0xD675C1

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

    if is_emoji_only and 1 <= total_emoji_count <= 30:
        if not stripped.startswith('# '):
            return f'# {stripped}'

    return text


async def check_valid_cdn_url(session:aiohttp.ClientSession, url:str) -> bool:
    if url in CACHE_VALIDASI_CDN:
        return CACHE_VALIDASI_CDN[url]
    try:
        async with session.head(url, timeout=aiohttp.ClientTimeout(total=1.5), allow_redirects=True) as resp:
            is_valid = resp.status == 200
            CACHE_VALIDASI_CDN[url] = is_valid
            return is_valid
    except Exception:
        CACHE_VALIDASI_CDN[url] = False
        return False


class SnipeView(discord.ui.LayoutView):
    def __init__(self, ctx:commands.Context, snipes:list[dict], http_session:aiohttp.ClientSession):
        super().__init__(timeout=120)
        self.ctx = ctx
        self.snipes = snipes
        self.http_session = http_session
        self.current_page = 0
        self.total_pages = len(snipes)
        self.message = None
    
    def _cari_warna_snipe(self, sniped_data:dict) -> discord.Color:
        color_int = sniped_data.get("dominant_color", 0xD675C1)
        return discord.Color(color_int if color_int != 0 else 0xD675C1)
    
    async def setup_layout(self) -> list[discord.File]:
        self.clear_items()
        
        sniped_data = self.snipes[self.current_page]
        color = self._cari_warna_snipe(sniped_data)
        
        container = discord.ui.Container(accent_color=color)
        unix_ts = int(sniped_data["created_at"].timestamp())
        
        raw_content = sniped_data.get("content")
        stickers = sniped_data.get("stickers", [])
        
        if raw_content:
            content_text = format_jumboji(raw_content)
        elif stickers:
            sticker_names = [st["name"] if isinstance(st, dict) else str(st) for st in stickers]
            content_text = f"*[Sticker: {', '.join(sticker_names)}]*"
        else:
            content_text = "*[Pesan gak berisi teks]*"
        
        author = sniped_data["author"]

        # 1. Title & Text Content
        container.add_item(discord.ui.TextDisplay("### 🗑️ Pesan yang Baru Saja Dihapus (5 Menit Terakhir)"))
        container.add_item(discord.ui.Separator(visible=True, spacing=discord.SeparatorSpacing.small))
        container.add_item(
            discord.ui.Section(
                discord.ui.TextDisplay(f"-# Pengirim: {author['mention']}\n\n{content_text}"),
                accessory=discord.ui.Thumbnail(media=author["avatar_url"])
            )
        )
        
        # 2. Attachments, Stickers, Media, & CDN links
        attachments = sniped_data.get("attachments", [])
        files = []
        media_items = []
        file_components = []

        if stickers:
            for st in stickers:
                if isinstance(st, dict) and st.get("url"):
                    media_items.append(discord.MediaGalleryItem(media=st["url"], description=f"Sticker: {st['name']}"))
        
        if raw_content:
            found_cdn_urls = CDN_LINK_RE.findall(raw_content)
            if found_cdn_urls:
                tasks = [check_valid_cdn_url(self.http_session, url) for url in found_cdn_urls[:MAX_ATTACHMENT_PER_PESAN]]
                results = await asyncio.gather(*tasks)

                for url, is_valid in zip(found_cdn_urls, results):
                    if is_valid:
                        clean_url = url.split('?')[0].lower()
                        if clean_url.endswith(FORMAT_GAMBAR) or clean_url.endswith(FORMAT_VIDEO) or "/avatars/" in clean_url or "/emojis/" in clean_url:
                            media_items.append(discord.MediaGalleryItem(media=url))

        if attachments:
            for idx, att in enumerate(attachments[:MAX_ATTACHMENT_PER_PESAN]):
                filename = f"{idx + 1}_{att['filename']}" if len(attachments) > 1 else att['filename']
                c_type = att.get("content_type") or ""
                att_fn = att['filename'].lower()
                is_spoiler = att.get("spoiler", False)

                is_img = c_type.startswith("image/") or att_fn.endswith(FORMAT_GAMBAR)
                is_vid = c_type.startswith("video/") or att_fn.endswith(FORMAT_VIDEO)

                if att.get("bytes"):
                    bio = io.BytesIO(att["bytes"])
                    bio.seek(0)
                    files.append(discord.File(bio, filename=filename))
                    media_target = f"attachment://{filename}"
                elif att.get("url"):
                    media_target = att["url"]
                else:
                    continue

                if is_img or is_vid:
                    media_items.append(discord.MediaGalleryItem(media=media_target, description=att['filename'], spoiler=is_spoiler))
                else:
                    file_components.append(discord.ui.File(media_target))

        if media_items:
            container.add_item(discord.ui.MediaGallery(*media_items[:MAX_ATTACHMENT_PER_PESAN]))

        for fc in file_components:
            container.add_item(fc)

        # 3. Footer / Additional Info
        container.add_item(discord.ui.Separator(visible=True, spacing=discord.SeparatorSpacing.small))
        container.add_item(discord.ui.TextDisplay(f"-# Dikirim pada pukul <t:{unix_ts}:T> (<t:{unix_ts}:R>)"))

        # 4. Navigation Controls & Close Button
        row = discord.ui.ActionRow()

        btn_prev = discord.ui.Button(
            label="◀",
            style=discord.ButtonStyle.primary,
            custom_id="snipe_prev",
            disabled=(self.current_page == 0)
        )
        btn_prev.callback = self.prev_callback

        btn_ind = discord.ui.Button(
            label=f"{self.current_page+1}/{self.total_pages}",
            style=discord.ButtonStyle.secondary,
            custom_id="snipe_indicator",
            disabled=True
        )

        btn_next = discord.ui.Button(
            label="▶",
            style=discord.ButtonStyle.primary,
            custom_id="snipe_next",
            disabled=(self.current_page == self.total_pages-1)
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
        container.add_item(row)

        self.add_item(container)
        return files

    async def interaction_check(self, interaction:discord.Interaction) -> bool:
        if interaction.user.id != self.ctx.author.id:
            await interaction.response.send_message("Cuma yang ngetik command yang bisa ngatur tampilan ini ya! 💢", ephemeral=True)
            return False
        return True

    async def _update_page(self, interaction:discord.Interaction):
        await interaction.response.defer()
        files = await self.setup_layout()
        
        if self.message:
            await self.message.edit(attachments=files, view=self, allowed_mentions=discord.AllowedMentions.none())
        else:
            await interaction.edit_original_response(attachments=files, view=self, allowed_mentions=discord.AllowedMentions.none())

    async def prev_callback(self, interaction:discord.Interaction):
        if self.current_page > 0:
            self.current_page -= 1
            await self._update_page(interaction)

    async def next_callback(self, interaction:discord.Interaction):
        if self.current_page < self.total_pages - 1:
            self.current_page += 1
            await self._update_page(interaction)

    async def close_callback(self, interaction:discord.Interaction):
        self.stop()
        #await interaction.response.defer()
        await interaction.message.delete()

    async def on_timeout(self):
        for item in self.walk_children():
            if isinstance(item, discord.ui.Button):
                item.disabled = True
        try:
            if self.message:
                await self.message.edit(view=self, allowed_mentions=discord.AllowedMentions.none())
        except Exception:
            pass


class Snipe(commands.Cog):
    def __init__(self, bot:commands.Bot):
        self.bot = bot
        self.snipes: dict[int, deque] = {}
        self.session: aiohttp.ClientSession = None
        self.clean_expired_snipes.start()

    async def cog_load(self):
        self.session = aiohttp.ClientSession()

    async def cog_unload(self):
        self.clean_expired_snipes.cancel()
        if self.session:
            await self.session.close()

    @tasks.loop(minutes=2)
    async def clean_expired_snipes(self):
        now = discord.utils.utcnow()
        expired_channels = []
        for channel_id, channel_snipes in list(self.snipes.items()):
            while channel_snipes and (now - channel_snipes[-1]["deleted_at"]).total_seconds() > BATAS_KADALUARSA_SNIPE:
                channel_snipes.pop()
            if not channel_snipes:
                expired_channels.append(channel_id)

        for channel_id in expired_channels:
            self.snipes.pop(channel_id, None)

        if len(CACHE_VALIDASI_CDN) > 1000:
            CACHE_VALIDASI_CDN.clear()

    def _get_valid_snipes(self, channel_id:int) -> list[dict]:
        snipes = self.snipes.get(channel_id)
        if not snipes:
            return []

        now = discord.utils.utcnow()
        while snipes and (now - snipes[-1]["deleted_at"]).total_seconds() > BATAS_KADALUARSA_SNIPE:
            snipes.pop()

        if not snipes:
            self.snipes.pop(channel_id, None)
            return []

        return list(snipes)

    @commands.Cog.listener()
    async def on_message_delete(self, message:discord.Message):
        if not message.author or message.author.bot or not message.guild:
            return

        cached_attachments = []
        dominant_color_int = 0xD675C1

        if message.attachments:
            download_tasks = []
            valid_atts = []
            total_bytes = 0

            for att in message.attachments[:MAX_ATTACHMENT_PER_PESAN]:
                is_spoiler = att.is_spoiler()
                if att.size <= BATAS_UKURAN_ATTACHMENT and (total_bytes + att.size) <= BATAS_UKURAN_BYTE:
                    total_bytes += att.size
                    valid_atts.append(att)
                    download_tasks.append(asyncio.wait_for(att.read(), timeout=DOWNLOAD_TIMEOUT))
                else:
                    cached_attachments.append({
                        "filename": att.filename,
                        "content_type": att.content_type,
                        "url": att.url,
                        "bytes": None,
                        "spoiler": is_spoiler
                    })

            if download_tasks:
                results = await asyncio.gather(*download_tasks, return_exceptions=True)
                for att, result in zip(valid_atts, results):
                    att_bytes = result if isinstance(result, bytes) else None
                    if att_bytes and dominant_color_int == 0xD675C1:
                        c_type = att.content_type or ""
                        att_fn = att.filename.lower()
                        if c_type.startswith("image/") or att_fn.endswith(FORMAT_GAMBAR):
                            dominant_color_int = await asyncio.to_thread(_proses_gambar_warnadominan, att_bytes)

                    cached_attachments.append({
                        "filename": att.filename,
                        "content_type": att.content_type,
                        "url": att.url,
                        "bytes": att_bytes,
                        "spoiler": att.is_spoiler()
                    })

        if dominant_color_int == 0xD675C1 and message.author.display_avatar.url:
            dominant_color_int = await cari_warna_dominan(self.session, message.author.display_avatar.url)

        cached_stickers = []
        if message.stickers:
            for s in message.stickers:
                cached_stickers.append({
                    "id": s.id,
                    "name": s.name,
                    "url": s.url,
                    "format": str(getattr(s, "format", ""))
                })

        author_data = {
            "id": message.author.id,
            "name": str(message.author),
            "avatar_url": message.author.display_avatar.url,
            "mention": message.author.mention
        }

        snipe_entry = {
            "id": message.id,
            "author": author_data,
            "content": message.content,
            "stickers": cached_stickers,
            "created_at": message.created_at,
            "deleted_at": discord.utils.utcnow(),
            "attachments": cached_attachments,
            "dominant_color": dominant_color_int
        }

        if message.channel.id not in self.snipes:
            self.snipes[message.channel.id] = deque(maxlen=MAX_SNIPES_PER_CHANNEL)

        self.snipes[message.channel.id].appendleft(snipe_entry)

    @commands.hybrid_command(name="snipe", description="Intip sampai 5 pesan yang baru aja dihapus")
    async def snipe(self, ctx:commands.Context):
        async with ctx.typing():
            sniped_list = self._get_valid_snipes(ctx.channel.id)

            if not sniped_list:
                await ctx.send("Gak ada pesan yang baru dihapus di channel ini.")
                return

            view = SnipeView(ctx, sniped_list, self.session)
            files = await view.setup_layout()

            msg = await ctx.send(files=files, view=view, allowed_mentions=discord.AllowedMentions.none())
            view.message = msg


async def setup(bot:commands.Bot):
    await bot.add_cog(Snipe(bot))