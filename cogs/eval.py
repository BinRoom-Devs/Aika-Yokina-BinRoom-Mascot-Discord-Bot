import contextlib
import io
import re
import sys
import traceback

import discord
from discord.ext import commands

ID_OWNER = 1524951093560213638 # @arumugi_4405


class Eval(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        
        self.ANSI = {
            "reset": "\x1b[0m",
            "bold": "\x1b[1m",
            "merah": "\x1b[0;31m",
            "merah_tebal": "\x1b[1;31m",
            "hijau": "\x1b[0;32m",
            "kuning": "\x1b[0;33m",
            "sian": "\x1b[0;36m",
            "pink": "\x1b[0;35m",
            "pink_tebal": "\x1b[1;35m",
            "abu": "\x1b[0;30m",
        }
        
        self.pola_eror = [
            (r"\b(KeyboardInterrupt|SystemExit|CancelledError)\b", self.ANSI["merah_tebal"]),
            (r"\b(CommandInvokeError|HTTPException|NotFound|Forbidden|DiscordException|ClientConnectorError)\b", self.ANSI["pink_tebal"]),
            (r"\b(SyntaxError|IndentationError|TypeError|ValueError|KeyError|AttributeError|ImportError|ModuleNotFoundError|NameError|ZeroDivisionError|FileNotFoundError|UnboundLocalError)\b", self.ANSI["merah_tebal"]),
            (r"\b(UserWarning|DeprecationWarning|RuntimeWarning|Warning)\b", self.ANSI["kuning"]),
        ]
    
    @staticmethod
    def kodingan_bersih(isi:str) -> str:
        if isi.startswith("```") and isi.endswith("```"):
            return "\n".join(isi.split("\n")[1:-1])
        return isi.strip("` \n")
    
    def inden_kodingan(self, kode:str) -> str:
        return "\n".join(f"    {baris}" for baris in kode.split("\n"))
    
    def format_log_ansi(self, teks_mentah: str) -> str:
        baris_terformat = []
        
        for baris in teks_mentah.splitlines():
            if re.match(r"^\s*[\^\~]+\s*$", baris):
                baris = f"{self.ANSI['merah_tebal']}{baris}{self.ANSI['reset']}"

            elif baris.startswith("Traceback") or "most recent call last" in baris:
                baris = f"{self.ANSI['bold']}{self.ANSI['kuning']}{baris}{self.ANSI['reset']}"
            elif "During handling of the above exception" in baris or "The above exception was the direct cause" in baris:
                baris = f"{self.ANSI['bold']}{self.ANSI['merah_tebal']}{baris}{self.ANSI['reset']}"
            
            elif "File " in baris:
                baris = re.sub(r'File "(.*?)"', f'File "{self.ANSI["sian"]}\\1{self.ANSI["reset"]}"', baris)
                baris = re.sub(r'line (\d+)', f'line {self.ANSI["kuning"]}\\1{self.ANSI["reset"]}', baris)
                baris = re.sub(r'in ([\w<>]+\b)', f'in {self.ANSI["pink_tebal"]}\\1{self.ANSI["reset"]}', baris)
            
            else:
                for pola, warna in self.pola_eror:
                    if re.search(pola, baris):
                        baris = f"{self.ANSI['merah_tebal']}{baris}{self.ANSI['reset']}"
                        break
            
            baris_terformat.append(baris)
        
        return "\n".join(baris_terformat)
    
    @commands.hybrid_command(name="eval", aliases=["ev"])
    @commands.is_owner()
    async def _eval(self, ctx, *, isi:str):
        if ctx.author.id != ID_OWNER:
            return
        
        env = {
            'bot': self.bot,
            'ctx': ctx,
            'channel': ctx.channel,
            'author': ctx.author,
            'guild': ctx.guild,
            'message': ctx.message,
            'self': self
        }
        env.update(globals())
        
        isi = self.kodingan_bersih(isi)
        stdout = io.StringIO()
        
        buat_di_complie = f"async def func():\n{self.inden_kodingan(isi)}"
        
        try:
            exec(buat_di_complie, env)  # noqa: S102
        except Exception as waduh:  # noqa: BLE001
            pesan_eror = f"{waduh.__class__.__name__}: {waduh}"
            ansi_err = self.format_log_ansi(pesan_eror)
            
            container = discord.ui.Container(accent_color=0xE56160)
            container.add_item(discord.ui.TextDisplay(content=f"```ansi\n{ansi_err}\n```"))
            
            await ctx.message.add_reaction("❌")
            return await ctx.send(view=discord.ui.LayoutView().add_item(container))
        
        fungsi = env['func']
        try:
            with contextlib.redirect_stdout(stdout):
                ret = await fungsi()
            
        except Exception:  # noqa: BLE001
            nilai = stdout.getvalue()
            eror_mentahan = f"{nilai}{traceback.format_exc()}"
            ansi_err = self.format_log_ansi(eror_mentahan)
            
            info_sistem = f"Python {sys.version} pada {sys.platform}"
            subteks_footer = f"-# {info_sistem}"
            
            container = discord.ui.Container(accent_color=0xE56160)
            container.add_item(discord.ui.TextDisplay(content=f"```ansi\n{ansi_err}\n```"))
            container.add_item(discord.ui.Separator(spacing=discord.SeparatorSpacing.small))
            container.add_item(discord.ui.TextDisplay(content=subteks_footer))
            
            await ctx.message.add_reaction("❌")
            await ctx.send(view=discord.ui.LayoutView().add_item(container))
            
        else:
            nilai = stdout.getvalue()
            hasil = None
            
            if ret is None and nilai:
                hasil = nilai if nilai else ''
            else:
                hasil = f"{nilai}{ret}" if nilai else str(ret)
            
            info_sistem = f"Python {sys.version} pada {sys.platform}"
            subteks_footer = f"-# {info_sistem}"
            
            str_hasil = str(hasil)
            if self.bot.http.token:
                str_hasil = str_hasil.replace(self.bot.http.token, "[TOKEN_DISENSOR]")
            
            pola_deteksi_eror = r"(Traceback|most recent call last|raise\b|Error|Exception|KeyboardInterrupt|SystemExit|During handling of the above exception)"
            is_eror = bool(re.search(pola_deteksi_eror, str_hasil, re.IGNORECASE))
            
            warna = ''
            if is_eror:
                str_hasil = self.format_log_ansi(str_hasil)
                lang_tag = "ansi"
                warna = 0xE56160
                await ctx.message.add_reaction("❌")
            else:
                lang_tag = "py"
                warna = 0xD675C1
                await ctx.message.add_reaction("✅")
            
            BATAS_TEKS = 1900
            jumlah_teks = [str_hasil[i:i + BATAS_TEKS] for i in range(0, len(str_hasil), BATAS_TEKS)]
            
            for indeks, teks in enumerate(jumlah_teks[:5]):
                container = discord.ui.Container(accent_color=warna)
                container.add_item(discord.ui.TextDisplay(content=f"```{lang_tag}\n{teks}\n```"))
                
                if indeks == len(jumlah_teks[:5]) - 1:
                    container.add_item(discord.ui.Separator(spacing=discord.SeparatorSpacing.small))
                    container.add_item(discord.ui.TextDisplay(content=subteks_footer))
                    
                await ctx.send(view=discord.ui.LayoutView().add_item(container))
            
            if len(jumlah_teks) > 5:
                await ctx.send("```... [Output melebihi batas teks]```")
    
    @_eval.error
    async def error(self, ctx, error:commands.NotOwner):
        if error:
            await ctx.send("Cuma kak Abin yang bisa pakai command ini! 💢")


async def setup(bot):
    await bot.add_cog(Eval(bot))