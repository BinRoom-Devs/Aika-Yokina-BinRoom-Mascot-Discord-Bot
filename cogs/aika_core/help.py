import collections
import inspect
import sys
from typing import Union, get_args, get_origin

import discord
from discord import AllowedMentions, SeparatorSpacing
from discord.ext import commands
from discord.ui import Container, LayoutView, Section, Separator, TextDisplay, Thumbnail

from cogs.aika_core.version import LINK_REPO, baca_info_git

FOLDER_MAP = {
    "aika_chatbot_ai": "🗣️ AI Chatbot",
    "aika_core": "🌸 Tentang Aika",
    "aika_utility_commands": "💡 Utilitas",
    "binroom_modules": "🧩 Modul BinRoom",
    "leaderboard_central": "📊 Leaderboard / Papan Peringkat",
}

URUTAN_KATEGORI = [
    "🧩 Modul BinRoom",
    "🗣️ AI Chatbot",
    "📊 Leaderboard / Papan Peringkat",
    "💡 Utilitas",
    "🌸 Tentang Aika",
]

INDEKS_URUTAN = {name: index for index, name in enumerate(URUTAN_KATEGORI)}


class Help(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self._cached_emoji: str | discord.Emoji | None = None
        _, self.hash_lengkap, _ = baca_info_git()
    
    async def emoji_aika(self) -> str | discord.Emoji:
        if self._cached_emoji is not None:
            return self._cached_emoji
        
        try:
            emojis = await self.bot.fetch_application_emojis()
            emoji_tujuan = discord.utils.get(emojis, name="aikaboticonbulat")
            if emoji_tujuan:
                self._cached_emoji = emoji_tujuan
                return self._cached_emoji
        except Exception:  # noqa: BLE001, S110
            pass
        
        self._cached_emoji = "<:Aika_Yokina:1551065535091974276>"
        return self._cached_emoji
    
    def baca_versi(self) -> str:
        version_cog = self.bot.get_cog("VersiAika") or self.bot.get_cog("cogs.version")
        if version_cog and hasattr(version_cog, "__version__"):
            return version_cog.__version__
        
        stats_mod = sys.modules.get("stats")
        if stats_mod and hasattr(stats_mod, "__version__"):
            return stats_mod.__version__
        
        return ""
    
    def isi_help(self) -> str:
        kategori = collections.defaultdict(list)
        
        for perintah in self.bot.walk_commands():
            if perintah.hidden or not perintah.enabled:
                continue
            
            module_parts = perintah.callback.__module__.split(".")
            folder = module_parts[1] if len(module_parts) > 1 and module_parts[0] == "cogs" else "Tidak dikategorikan"
            
            nama_kategori = FOLDER_MAP.get(folder, folder.replace("_", " ").title())
            
            kategori[nama_kategori].append(perintah.qualified_name)
        
        kategori_tersusun = sorted(
            kategori.items(),
            key=lambda x: INDEKS_URUTAN.get(x[0], len(INDEKS_URUTAN))
        )
        
        return "\n\n".join(
            f"**{nama_kategori}:**\n" + " ".join(f"`{cmd}`" for cmd in sorted(cmds))
            for nama_kategori, cmds in kategori_tersusun
        )
    
    async def format_command_help(self, cmd:commands.Command, ctx:commands.Context) -> Container:
        container = Container(accent_color=0xD675C1)
        emoji_aika = await self.emoji_aika()
        
        header = f"## {emoji_aika}  Info command `{cmd.qualified_name}`"
        container.add_item(TextDisplay(content=header))
        container.add_item(Separator(spacing=SeparatorSpacing.small))
        
        deskripsi = cmd.help or cmd.description or "Tidak ada deskripsi."
        aliases = f"`{', '.join(cmd.aliases)}`" if cmd.aliases else "Tidak ada."
        
        parameter = []
        argumen_penggunaan = []
        
        for nama, prmtr in cmd.clean_params.items():
            if prmtr.default is inspect.Parameter.empty:
                argumen_penggunaan.append(f"<{nama}>")
                str_prmtr = f"`<{nama}>` (Wajib)"
            else:
                argumen_penggunaan.append(f"[{nama}]")
                default_val = f" = {prmtr.default}" if prmtr.default is not None else ""
                str_prmtr = f"`[{nama}]` (Opsional{default_val})"
            
            if prmtr.annotation != inspect.Parameter.empty:
                anotasi = prmtr.annotation
                asal = get_origin(anotasi)
                if asal is Union or asal is type(Union):
                    args = [getattr(a, "__name__", str(a)) for a in get_args(anotasi) if a is not type(None)]
                    nama_type = " | ".join(args)
                else:
                    nama_type = getattr(anotasi, "__name__", str(anotasi))
                
                str_prmtr += f" - *{nama_type}*"
            
            parameter.append(f"• {str_prmtr}")
        
        teks_parameter = "\n".join(parameter) if parameter else "Tidak dibutuhkan."
        penggunaan = f"`{ctx.clean_prefix}{cmd.qualified_name} {' '.join(argumen_penggunaan)}`".strip()
        
        subcommands_text = ""
        if isinstance(cmd, commands.Group) and cmd.commands:
            subcmds = [f"`{sub.name}`" for sub in cmd.commands if not sub.hidden]
            if subcmds:
                subcommands_text = "\n\n**Sub-commands:**\n" + " ".join(subcmds)
        
        isi = (
            f"**Deskripsi:**\n{deskripsi}\n\n"
            f"**Nama lain:** {aliases}\n\n"
            f"**Penggunaan:**\n{penggunaan}\n\n"
            f"**Keterangan:**\n{teks_parameter}"
            f"{subcommands_text}"
        )
        
        container.add_item(TextDisplay(content=isi))
        container.add_item(Separator(spacing=SeparatorSpacing.small))
        
        footer = f"-# Ketik `{ctx.clean_prefix}help` untuk melihat daftar perintah lengkapnya Aika."
        container.add_item(TextDisplay(content=footer))
        
        return container
    
    @commands.hybrid_command(
        name="help",
        description="Menampilkan semua command Aika atau detail command tertentu."
    )
    async def help(self, ctx: commands.Context, *, command_name: str | None = None):
        if command_name:
            cmd = self.bot.get_command(command_name)
            
            if not cmd or cmd.hidden:
                await ctx.send("❌🤫 Perintah ini tersembunyi / tidak publik.", ephemeral=True)
                return
            
            container = await self.format_command_help(cmd, ctx)
            await ctx.send(
                view=LayoutView().add_item(container),
                allowed_mentions=AllowedMentions.none()
            )
            return
        
        container = Container(accent_color=0xD675C1)
        
        header_1 = f"## {await self.emoji_aika()}  Aika Yokina Bot Help"
        container.add_item(TextDisplay(content=header_1))
        
        container.add_item(Separator(spacing=SeparatorSpacing.small))
        
        aika_icon = self.bot.user.display_avatar.url
        isi_2 = (
            "Hay, salken.. Aku Aika Yokina, bot maskot server BinRoom. Tugas utamaku buat ngejaga server ini. "
            "Selain itu, aku juga bisa kamu ajak ngobrol di channel <#1540785170335006833>.\n\n"
            "Command-ku bisa dieksekusi via `/slash command` dan prefiks `ak!`."
        )
        container.add_item(Section(TextDisplay(content=isi_2), accessory=Thumbnail(media=aika_icon)))
        
        container.add_item(Separator(spacing=SeparatorSpacing.small))
        
        container.add_item(TextDisplay(content=self.isi_help()))
        
        container.add_item(Separator(spacing=SeparatorSpacing.small))
        
        version = self.baca_versi()
        version_prefix = f"{version}  •  " if version else ""
        footer = f"-# Aika Yokina {version_prefix}Dibuat dengan Python dan discord.py  •  Dikembangkan oleh <@1524951093560213638>"
        container.add_item(TextDisplay(content=footer))
        
        link_build = f"{LINK_REPO}/commit/{self.hash_lengkap}" if self.hash_lengkap else LINK_REPO
        
        tombol = discord.ui.ActionRow(
            discord.ui.Button(
                label="Source code",
                url=LINK_REPO,
                style=discord.ButtonStyle.link
            ),
            discord.ui.Button(
                label="Changelog",
                url=f"{LINK_REPO}/blob/main/changelog.md",
                style=discord.ButtonStyle.link
            ),
            discord.ui.Button(
                label="Build",
                url=link_build,
                style=discord.ButtonStyle.link
            )
        )
        
        await ctx.send(
            view=LayoutView().add_item(container).add_item(tombol),
            allowed_mentions=AllowedMentions.none()
        )


async def setup(bot:commands.Bot):
    await bot.add_cog(Help(bot))