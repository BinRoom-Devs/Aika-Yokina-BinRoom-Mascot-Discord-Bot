import asyncio
import io
from functools import lru_cache

import aiohttp
import discord
from discord.ext import commands
from PIL import Image


class LihatProfil(discord.ui.LayoutView):
    def __init__(self, cog:"PFP", ctx:commands.Context, user:discord.User|discord.Member, member:discord.Member|None, asset_type:str):
        super().__init__(timeout=180)
        self.cog = cog
        self.ctx = ctx
        self.user = user
        self.member = member
        self.asset_type = asset_type
        self.message = None
        
        if self.asset_type == "avatar":
            self.has_server = bool(self.member and self.member.guild_avatar)
            self.current_mode = "server" if self.has_server else "utama"
        else:
            self.has_server = bool(self.member and getattr(self.member, "guild_banner", None))
            self.current_mode = "server" if self.has_server else "utama"

    def _cari_aset_utama(self, mode:str) -> discord.Asset | None:
        if self.asset_type == "avatar":
            if mode == "server" and self.member and self.member.guild_avatar:
                return self.member.guild_avatar
            return self.user.avatar or self.user.default_avatar
        else:
            if mode == "server" and self.member and getattr(self.member, "guild_banner", None):
                return self.member.guild_banner
            return getattr(self.user, "banner", None)

    async def buat_container(self, tombol_mati:bool=False) -> discord.ui.Container:
        asset = self._cari_aset_utama(self.current_mode)
        
        if not asset:
            accent = getattr(self.user, "accent_color", None)
            if accent:
                warna = accent.value
                hex_str = f"#{warna:06x}"
                container = discord.ui.Container(accent_color=warna)
                container.add_item(discord.ui.TextDisplay(content="## Banner Tidak Ada"))
                container.add_item(discord.ui.Separator(spacing=discord.SeparatorSpacing.small))
                container.add_item(discord.ui.TextDisplay(content=f"{self.user.mention} tidak punya gambar banner, tetapi menggunakan warna solid **{hex_str.upper()}**."))
            else:
                container = discord.ui.Container()
                container.add_item(discord.ui.TextDisplay(content="## Banner Tidak Ada"))
                container.add_item(discord.ui.Separator(spacing=discord.SeparatorSpacing.small))
                container.add_item(discord.ui.TextDisplay(content=f"{self.user.mention} tidak memiliki banner custom maupun warna aksen."))
            return container

        try:
            link_hd = asset.with_size(4096).url
        except (discord.InvalidArgument, AttributeError):
            link_hd = asset.url
        warna, lebar_hd, tinggi_hd, beranimasi, total_frame = await self.cog.proses_aset_cached(link_hd)

        str_format = "GIF" if beranimasi else "PNG"
        jenis_label = "Foto Profilnya" if self.asset_type == "avatar" else "Foto Sampulnya"
        mode_label = "(Dalam Server)" if self.current_mode == "server" else ''
        
        container = discord.ui.Container(accent_color=warna)
        container.add_item(discord.ui.TextDisplay(content=f"## {jenis_label} si {self.user.mention} {mode_label}"))
        container.add_item(discord.ui.Separator(spacing=discord.SeparatorSpacing.small))
        container.add_item(discord.ui.MediaGallery(discord.MediaGalleryItem(link_hd)))
        container.add_item(discord.ui.Separator(spacing=discord.SeparatorSpacing.small))

        frames = f"  ·  {total_frame} frames" if beranimasi else ''

        if self.asset_type == "avatar":
            ukuran = f"  ·  {tinggi_hd}p" if tinggi_hd else ''
            key = f"  ·  `{asset.key}`" if asset.key else ''
        else:
            ukuran = f"  ·  {lebar_hd}x{tinggi_hd}p" if lebar_hd and tinggi_hd else ''
            key = f"  ·  `{asset.key}`" if (lebar_hd and lebar_hd > 500) else ''

        
        footer = f"-# [Link]({link_hd})  ·  {str_format}{ukuran}{frames}{key}"
        container.add_item(discord.ui.TextDisplay(content=footer))

        if self.has_server and not tombol_mati:
            action_row = discord.ui.ActionRow()
            kalo_mode_server = (self.current_mode == "server")
            
            tmbol_server = discord.ui.Button(
                label = "Server", 
                style = discord.ButtonStyle.primary if kalo_mode_server else discord.ButtonStyle.secondary,
                disabled = kalo_mode_server,
                custom_id = "tmbol_server"
            )
            tmbol_utama = discord.ui.Button(
                label = "Utama", 
                style = discord.ButtonStyle.primary if not kalo_mode_server else discord.ButtonStyle.secondary,
                disabled = not kalo_mode_server,
                custom_id = "tmbol_utama"
            )

            tmbol_server.callback = self._klik_tombol_server
            tmbol_utama.callback = self._klik_tombol_utama

            action_row.add_item(tmbol_server)
            action_row.add_item(tmbol_utama)
            container.add_item(action_row)
        return container

    async def _klik_tombol_server(self, interaction:discord.Interaction):
        if interaction.user.id != self.ctx.author.id:
            return await interaction.response.send_message("Yang bisa mencet tombol cuma yang ngeksekusi command-nya 💢", ephemeral=True)
        
        if self.current_mode == "server":
            return await interaction.response.defer()

        self.current_mode = "server"
        await interaction.response.defer()
        
        self.clear_items()
        container = await self.buat_container()
        self.add_item(container)
        await interaction.message.edit(view=self)

    async def _klik_tombol_utama(self, interaction:discord.Interaction):
        if interaction.user.id != self.ctx.author.id:
            return await interaction.response.send_message("Yang bisa mencet tombol cuma yang ngeksekusi command-nya 💢", ephemeral=True)

        if self.current_mode == "utama":
            return await interaction.response.defer()

        self.current_mode = "utama"
        await interaction.response.defer()

        self.clear_items()
        container = await self.buat_container()
        self.add_item(container)
        await interaction.message.edit(view=self)

    async def on_timeout(self):
        try:
            if self.message and self.has_server:
                self.clear_items()
                container = await self.buat_container(tombol_mati=True)
                self.add_item(container)
                await self.message.edit(view=self)
        except discord.HTTPException:
            pass


class PFP(commands.Cog):
    def __init__(self, bot:commands.Bot):
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
    def _proses_gambar_blocking(byte_gambar:bytes) -> tuple[int,int,int,bool,int]:
        try:
            with Image.open(io.BytesIO(byte_gambar)) as img:
                lebar, tinggi = img.size
                total_frame = getattr(img, "n_frames", 1)
                beranimasi = getattr(img, "is_animated", False) and total_frame > 1

                thumb = img.convert("RGB").resize((32,32), Image.Resampling.NEAREST)
                quantized = thumb.quantize(colors=1)
                palette = quantized.getpalette()
                
                warna = 0xD675C1
                if palette:
                    r,g,b = palette[:3]
                    warna = (r<<16) + (g<<8) + b

                return warna, lebar, tinggi, beranimasi, total_frame
        except (Image.UnidentifiedImageError, OSError, ValueError):
            pass
        return 0xD675C1, 0, 0, False, 1
    
    async def proses_aset_cached(self, link_gambar:str) -> tuple[int,int,int,bool,int]:
        try:
            async with self.session.get(link_gambar) as respon:
                if respon.status != 200:
                    return 0xD675C1, 0, 0, False, 1
                byte_gambar = await respon.read()
            return await asyncio.to_thread(self._proses_gambar_blocking, byte_gambar)
        except (aiohttp.ClientError, asyncio.TimeoutError) as e:
            print(f"[Aika] Foto profil: gagal memproses gambar ({e})")
            return 0xD675C1, 0, 0, False, 1
    
    async def _putuskan_user_dan_member(self, ctx:commands.Context, target:discord.Member|discord.User|None):
        target_obj = target or ctx.author
        member_obj = target_obj if isinstance(target_obj, discord.Member) else None

        if isinstance(target_obj, discord.User):
            user_obj = target_obj
        else:
            user_obj = target_obj._user if hasattr(target_obj, "_user") else target_obj

        if getattr(user_obj, "banner", None) is None:
            try:
                user_obj = await self.bot.fetch_user(target_obj.id)
            except discord.HTTPException:
                pass

        return user_obj, member_obj

    @commands.hybrid_command(name="avatar", aliases=["pfp", "pp", "icon"], description="Nampilin foto profil orang")
    async def avatar(self, ctx:commands.Context, member:discord.Member|discord.User=None):
        await ctx.defer()

        user_obj, member_obj = await self._putuskan_user_dan_member(ctx, member)

        view = LihatProfil(self, ctx, user_obj, member_obj, asset_type="avatar")
        container = await view.buat_container()
        view.add_item(container)

        view.message = await ctx.send(view=view, allowed_mentions=discord.AllowedMentions.none())

    @commands.hybrid_command(name="banner", aliases=["bn"], description="Nampilin foto sampul/banner profil orang")
    @discord.app_commands.describe(member="Member atau user yang mau diliat bannernya (opsional)")
    async def banner(self, ctx:commands.Context, member:discord.Member|discord.User=None):
        await ctx.defer()

        user_obj, member_obj = await self._putuskan_user_dan_member(ctx, member)

        view = LihatProfil(self, ctx, user_obj, member_obj, asset_type="banner")
        container = await view.buat_container()
        view.add_item(container)

        view.message = await ctx.send(view=view, allowed_mentions=discord.AllowedMentions.none())

    @avatar.error
    @banner.error
    async def profile_error(self, ctx:commands.Context, error:commands.CommandError):
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
    await bot.add_cog(PFP(bot))