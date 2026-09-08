import discord, aiohttp, re, asyncio, os
from discord.ext import commands
from typing import Optional, Tuple

CHANNEL_LOGGING = 1542006154744565870
SIGHTENGINE_USER = os.getenv("SIGHTENGINE_USER")
SIGHTENGINE_SECRET = os.getenv("SIGHTENGINE_SECRET")

URL_REGEX = r"https?://[^\s<>\"']+"

JENIS_KATEGORI = {
    "sexual": "konten seksual",
    "discriminatory": "ujaran diskriminatif",
    "insult": "hinaan/makian",
    "inappropriate": "ujaran tidak senonoh",
    "grawlix": "simbol sensor kasar",
    "profanity": "bahasa kasar"
}

class SightengineScanner(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.session: Optional[aiohttp.ClientSession] = None

    async def cog_load(self):
        self.session = aiohttp.ClientSession()

    async def cog_unload(self):
        if self.session:
            await self.session.close()

    async def buka_channel_logging(self, guild_or_id:int|discord.Guild) -> Optional[discord.TextChannel]:
        guild = self.bot.get_guild(guild_or_id) if isinstance(guild_or_id, int) else guild_or_id
        if not guild:
            return None
        channel = guild.get_channel(CHANNEL_LOGGING)
        return channel if isinstance(channel, discord.TextChannel) else None

    async def cek_isi_chat(self, text:str) -> Tuple[bool,str,str]:
        if not self.session or not text.strip():
            return False, "", ""

        clean_text = re.sub(URL_REGEX, "", text).strip()
        if not clean_text:
            return False, "", ""

        endpoint = "https://api.sightengine.com/1.0/text/check.json"
        
        params = {
            "text": clean_text,
            "lang": "en",  
            "mode": "standard",
            "api_user": SIGHTENGINE_USER,
            "api_secret": SIGHTENGINE_SECRET
        }

        try:
            async with self.session.get(endpoint, params=params) as resp:
                res = await resp.json()

                if resp.status != 200 or res.get("status") != "success":
                    print(f"[Aika] Sightengine HTTP debug: {resp.status} - {res}")
                    return False, "", ""

                profanity_data = res.get("profanity", {})
                kemiripan = profanity_data.get("matches", [])
                
                if kemiripan:
                    kategori_raw = kemiripan[0].get("type", "profanity").lower()
                    intensitas = kemiripan[0].get("intensity", "medium")

                    alasan_raw = f"`{kategori_raw} ({intensitas})`"
                    alasan_bersih = JENIS_KATEGORI.get(kategori_raw, "bahasa kasar")
                    return True, alasan_raw, alasan_bersih

                intensitas = profanity_data.get("intensity")
                if intensitas in ["medium", "high"]:
                    alasan_raw = f"`profanity ({intensitas})`"
                    alasan_bersih = "bahasa kasar"
                    return True, alasan_raw, alasan_bersih

        except Exception as e:
            print(f"[Aika] Sightengine error saat membaca teks: {e}")

        return False, "", ""

    async def cek_gambar(self, image_url:str) -> Tuple[bool,str,str]:
        if not self.session:
            return False, "", ""

        endpoint = "https://api.sightengine.com/1.0/check.json"
        params = {
            "url": image_url,
            "models": "nudity-2.1,gore-2.0",
            "api_user": SIGHTENGINE_USER,
            "api_secret": SIGHTENGINE_SECRET
        }

        try:
            async with self.session.get(endpoint, params=params) as resp:
                data = await resp.json()
                if resp.status != 200 or data.get("status") != "success":
                    return False, "", ""

                ketelanjangan = data.get("nudity", {})
                aktivitas_seksual = ketelanjangan.get("sexual_activity", 0.0)
                tampilan_seksual = ketelanjangan.get("sexual_display", 0.0)
                erotis = ketelanjangan.get("erotica", 0.0)
                sugestif = ketelanjangan.get("suggestive", 0.0)
                gore = data.get("gore", {}).get("prob", 0.0)

                max_explicit = max(aktivitas_seksual, tampilan_seksual, erotis)
                if max_explicit > 0.40:
                    return True, f"Explicit Image Content ({max_explicit * 100:.1f}%)", "gambar eksplisit"
                if sugestif > 0.75:
                    return True, f"Suggestive Image ({sugestif * 100:.1f}%)", "gambar sugestif"
                if gore > 0.70:
                    return True, f"Gore / Graphic Content ({gore * 100:.1f}%)", "gambar gore"

        except Exception as e:
            print(f"[Aika] Sightengine error saat membaca gambar: {e}")

        return False, "", ""

    def deteksi_link_gambar(self, message:discord.Message) -> list[str]:
        target_urls = []

        if message.attachments:
            for attachment in message.attachments:
                if attachment.content_type and attachment.content_type.startswith("image/"):
                    target_urls.append(attachment.url)

        if message.embeds:
            for embed in message.embeds:
                if embed.image and embed.image.url:
                    target_urls.append(embed.image.url)
                elif embed.thumbnail and embed.thumbnail.url:
                    target_urls.append(embed.thumbnail.url)

        if message.content:
            link_terdeteksi = re.findall(URL_REGEX, message.content)
            for url in link_terdeteksi:
                lower_url = url.lower()
                if any(ext in lower_url for ext in ['.png', '.jpg', '.jpeg', '.webp', '.gif', 'media.discordapp.net', 'cdn.discordapp.com', 'tenor.com/view', 'giphy.com']):
                    target_urls.append(url)

        return list(set(target_urls))

    async def proses_pesan(self, message:discord.Message):
        if message.author.bot or not message.guild:
            return

        ditandai = False
        alasan = ""
        alasan_bersih = ""

        if message.content:
            ditandai, alasan, alasan_bersih = await self.cek_isi_chat(message.content)

        if not ditandai:
            media_urls = self.deteksi_link_gambar(message)
            for url in media_urls:
                ditandai, alasan, alasan_bersih = await self.cek_gambar(url)
                if ditandai:
                    break

        if ditandai:
            log_channel = await self.buka_channel_logging(message.guild)
            if log_channel:
                log_embed = discord.Embed(
                    title="⚠️ Terdeteksi konten sensitif!",
                    description=f"__{alasan_bersih.capitalize()}__ terdeteksi pada [pesan]({message.jump_url}) yang dikirim oleh {message.author.mention} di {message.channel.mention}.",
                    color=discord.Color.gold()
                )
                if message.content:
                    log_embed.add_field(name="Isi Pesan Teks", value=message.content, inline=True)
                log_embed.add_field(name="Dugaan", value=f"`{alasan}`", inline=True)
                log_embed.set_author(name=message.author.name, icon_url=message.author.display_avatar.url)
                log_embed.set_thumbnail(url=message.author.display_avatar.url)
                log_embed.set_footer(text=f"ID User: {message.author.id}  •  ID Pesan: {message.id}  •  by Sightengine")

                if "gambar" in alasan_bersih:
                    await log_channel.send(content="<@1524951093560213638> <@&904996395260477450> 😨", embed=log_embed)
                else:
                    await log_channel.send(embed=log_embed)

    @commands.Cog.listener()
    async def on_message(self, message:discord.Message):
        await self.proses_pesan(message)

        if re.search(URL_REGEX, message.content) and not message.attachments and not message.embeds:
            await asyncio.sleep(2.0)
            try:
                refreshed_message = await message.channel.fetch_message(message.id)
                if refreshed_message.embeds:
                    await self.proses_pesan(refreshed_message)
            except discord.NotFound:
                pass

    @commands.Cog.listener()
    async def on_message_edit(self, before:discord.Message, after:discord.Message):
        await self.proses_pesan(after)


async def setup(bot:commands.Bot):
    await bot.add_cog(SightengineScanner(bot))