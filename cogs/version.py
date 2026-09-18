import subprocess

import discord
from discord.ext import commands

VERSI_AIKA = "v2.6.0"
LINK_REPO = "https://github.com/BinRoom-Devs/Aika-Yokina-BinRoom-Mascot-Discord-Bot"

def baca_info_git():
    try:
        keluaran = subprocess.check_output(
            ["git", "log", "-1", "--format=%h,%H,%ct"], # %h = hash pendek, # %H = hash lengkap, %ct = format timestamp unix
            stderr=subprocess.DEVNULL
        ).decode("utf-8").strip()
        
        hash_commit, hash_panjang, waktu_commit = keluaran.split(",")
        return hash_commit, hash_panjang, int(waktu_commit)
    
    except Exception:  # noqa: BLE001
        return "N/A", "", 0


class VersiAika(commands.Cog):
    def __init__(self, bot:commands.Bot):
        self.bot = bot
        self.__version__ = VERSI_AIKA
        self.hash_commit, self.hash_lengkap, self.timestamp_commit = baca_info_git()
    
    @commands.hybrid_command(name="version", aliases=["versi", "ver", "versi-aika", "versi-bot"])
    async def version(self, ctx):
        container = discord.ui.Container(accent_color=0xDE82CF) 
        
        container.add_item(
            discord.ui.Section(
                discord.ui.TextDisplay(content=(
                    "**Versi Aika**\n"
                    f"# {self.__version__}"
                )),
                accessory = discord.ui.Thumbnail(media=self.bot.user.display_avatar.url)
            )
        )
        
        container.add_item(discord.ui.Separator(spacing=discord.SeparatorSpacing.small))
        
        container.add_item(discord.ui.TextDisplay(
            content=(
                f"-# Build `{self.hash_commit}`"
                "  •  "
                f"Terakhir diperbarui: {f'<t:{self.timestamp_commit}:D>' if self.timestamp_commit else 'N/A'}"
            ))
        )
        
        link_build = f"{LINK_REPO}/commit/{self.hash_lengkap}" if self.hash_lengkap else LINK_REPO
        link_changelog = f"{LINK_REPO}/blob/main/changelog.md"
        
        deretan_tombol = discord.ui.ActionRow(
            discord.ui.Button(label="Info build", url=link_build, style=discord.ButtonStyle.link),
            discord.ui.Button(label="Riwayat pembaruan", url=link_changelog, style=discord.ButtonStyle.link)
        )
        
        await ctx.send(view=discord.ui.LayoutView().add_item(container).add_item(deretan_tombol))


async def setup(bot):
    await bot.add_cog(VersiAika(bot))