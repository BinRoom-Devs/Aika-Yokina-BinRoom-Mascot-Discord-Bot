import discord
from discord import (
    AllowedMentions,
    Interaction,
    Member,
    SeparatorSpacing,
    TextChannel,
    app_commands,
    ui,
)
from discord.ext import commands

from config import pengaturan


class FormulirModal(discord.ui.Modal, title="Tulis confess-an"):
    pengirim = discord.ui.TextInput(
        label="Dari",
        style=discord.TextStyle.short,
        placeholder="(Opsional) Hamba Allah",
        required=False,
        max_length=50
    )
    penerima = discord.ui.TextInput(
        label="Ke",
        style=discord.TextStyle.short,
        placeholder="(Opsional) orang paling spesial",
        required=False,
        max_length=50
    )
    isi = discord.ui.TextInput(
        label="Isi confess-anmu",
        style=discord.TextStyle.paragraph,
        placeholder="Ketikkan isi pesanmu di sini...",
        required=True,
        max_length=1500
    )
    
    def __init__(self, org_tujuan:Member|None, ch_tujuan:TextChannel|None):
        super().__init__()
        self.org_tujuan = org_tujuan
        self.ch_tujuan = ch_tujuan
    
    async def on_submit(self, interaction:Interaction):
        await interaction.response.defer(ephemeral=True)
        
        ch_target = self.ch_tujuan or interaction.channel
        info_orang = f" untukmu, {self.org_tujuan.mention}" if self.org_tujuan else ''
        
        if not isinstance(ch_target, discord.TextChannel):
            await interaction.response.send_message(
                "❌ Gagal ngemastiin channel tujuan.", ephemeral=True
            )
            return
        
        
        container = ui.Container(accent_color=pengaturan.warna_aika)
        
        judul = f"### 👁️ Ada confess-an anonim{info_orang}"
        container.add_item(ui.TextDisplay(content=judul))
        
        container.add_item(ui.Separator(spacing=SeparatorSpacing.small))
        
        isi = (
            f"-# Dari: {self.pengirim.value if self.pengirim.value else '-'}\n"
            f"-# Ke: {self.penerima.value if self.penerima.value else '-'}\n"
            "\n"
            f"{self.isi.value}"
        )
        thumbnail = "https://cdn.jsdelivr.net/gh/twitter/twemoji@latest/assets/72x72/1f48c.png"
        container.add_item(ui.Section(ui.TextDisplay(content=isi), accessory=ui.Thumbnail(media=thumbnail)))
        
        container.add_item(ui.Separator(spacing=SeparatorSpacing.small))
        
        footer = "-# Mau nulis confess-an kayak gini juga? Coba `/menfess`"
        container.add_item(ui.TextDisplay(content=footer))
        
        try:
            await ch_target.send(
                view=ui.LayoutView().add_item(container),
                allowed_mentions=AllowedMentions.none()
            )
        except discord.Forbidden:
            await interaction.response.send_message(
                "❌ Aika gapunya akses ke channel yang kamu masukkan...",
                ephemeral=True
            )
            return
        
        
        info_org = (
            f" ke {self.org_tujuan.mention}" if self.org_tujuan else ""
        )
        info_channel = f" di {ch_target.mention}"
        
        await interaction.response.send_message(
            f"✅ Confess-an berhasil terkirim{info_org}{info_channel}!",
            ephemeral=True
        )


class Menfess(commands.Cog):
    def __init__(self, bot:commands.Bot):
        self.bot = bot
    
    async def _handle_confessan(
        self,
        intr: Interaction,
        tujuan: Member | None = None,
        ch: TextChannel | None = None
    ):
        await intr.response.send_modal(FormulirModal(org_tujuan=tujuan, ch_tujuan=ch))
    
    @app_commands.command(
        name="menfess",
        description="Tulis confess-an anonim ke seseorg 🤫"
    )
    @app_commands.describe(
        orang_tujuan="org yang ingin kamu kirimin confess-annya (opsional)",
        channel_tujuan="Channel tempat confess-annya dikirim (opsional; default ke channel sekarang jika tidak diinfokan)."
    )
    async def menfess(self, intr:Interaction, orang_tujuan:Member|None=None, channel_tujuan:TextChannel|None=None):
        await self._handle_confessan(intr, orang_tujuan, channel_tujuan)


async def setup(bot: commands.Bot):
    await bot.add_cog(Menfess(bot))