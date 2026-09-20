import contextlib
import io
import re
import sys
import textwrap
import traceback

import discord
from discord.ext import commands

ID_OWNER = 1524951093560213638  # @arumugi_4405


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
        
        self.pola_eror_compiled = [
            (re.compile(r"\b(KeyboardInterrupt|SystemExit|CancelledError)\b"), self.ANSI["merah_tebal"]),
            (re.compile(r"\b(CommandInvokeError|HTTPException|NotFound|Forbidden|DiscordException|ClientConnectorError)\b"), self.ANSI["pink_tebal"]),
            (re.compile(r"\b(SyntaxError|IndentationError|TypeError|ValueError|KeyError|AttributeError|ImportError|ModuleNotFoundError|NameError|ZeroDivisionError|FileNotFoundError|UnboundLocalError)\b"), self.ANSI["merah_tebal"]),
            (re.compile(r"\b(UserWarning|DeprecationWarning|RuntimeWarning|Warning)\b"), self.ANSI["kuning"]),
        ]
        
        self.re_caret = re.compile(r"^\s*[\^\~]+\s*$")
        self.re_file = re.compile(r'File "(.*?)"')
        self.re_line = re.compile(r'line (\d+)')
        self.re_func = re.compile(r'in ([\w<>]+\b)')
        self.re_soft_err = re.compile(
            r"(Traceback|most recent call last|raise\b|Error|Exception|KeyboardInterrupt|SystemExit|During handling of the above exception)",
            re.IGNORECASE,
        )
    
    @staticmethod
    def kodingan_bersih(isi:str) -> str:
        isi = isi.strip()
        if isi.startswith("```") and isi.endswith("```"):
            lines = isi.splitlines()
            return "\n".join(lines[1:-1]) if len(lines) > 2 else ""
        return isi.strip("` \n")
    
    def format_log_ansi(self, teks_mentah:str) -> str:
        baris_terformat = []
        
        for baris in teks_mentah.splitlines():
            if self.re_caret.match(baris):
                baris = f"{self.ANSI['merah_tebal']}{baris}{self.ANSI['reset']}"
            elif baris.startswith("Traceback") or "most recent call last" in baris:
                baris = f"{self.ANSI['bold']}{self.ANSI['kuning']}{baris}{self.ANSI['reset']}"
            elif "During handling of the above exception" in baris or "The above exception was the direct cause" in baris:
                baris = f"{self.ANSI['bold']}{self.ANSI['merah_tebal']}{baris}{self.ANSI['reset']}"
            elif "File " in baris:
                baris = self.re_file.sub(f'File "{self.ANSI["sian"]}\\1{self.ANSI["reset"]}"', baris)
                baris = self.re_line.sub(f'line {self.ANSI["kuning"]}\\1{self.ANSI["reset"]}', baris)
                baris = self.re_func.sub(f'in {self.ANSI["pink_tebal"]}\\1{self.ANSI["reset"]}', baris)
            else:
                for pola, warna in self.pola_eror_compiled:
                    if pola.search(baris):
                        baris = f"{warna}{baris}{self.ANSI['reset']}"
                        break
            
            baris_terformat.append(baris)
        
        return "\n".join(baris_terformat)
    
    async def _kirim_container(self, ctx, content:str, warna:int, tag_bhs:str="ansi", footer:str|None=None):
        container = discord.ui.Container(accent_color=warna)
        container.add_item(discord.ui.TextDisplay(content=(
            "🔴 🟡 🟢 `Aika Yokina - eval.py`\n"
            "\n"
            f"```{tag_bhs}\n{content}\n```"
        )))
        
        if footer:
            container.add_item(discord.ui.Separator(spacing=discord.SeparatorSpacing.small))
            container.add_item(discord.ui.TextDisplay(content=footer))
        
        return await ctx.send(view=discord.ui.LayoutView().add_item(container))

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
            'self': self,
        }
        env.update(globals())
        
        isi = self.kodingan_bersih(isi)
        stdout = io.StringIO()
        buat_di_compile = f"async def func():\n{textwrap.indent(isi, '    ')}"
        
        try:
            exec(buat_di_compile, env)  # noqa: S102
        except Exception as waduh:  # noqa: BLE001
            pesan_eror = f"{waduh.__class__.__name__}: {waduh}"
            ansi_err = self.format_log_ansi(pesan_eror)
            await ctx.message.add_reaction("❌")
            return await self._kirim_container(ctx, ansi_err, warna=0xE56160)
        
        fungsi = env['func']
        subteks_footer = f"-# Python {sys.version} on {sys.platform}"
        
        try:
            with contextlib.redirect_stdout(stdout):
                ret = await fungsi()
        except Exception:  # noqa: BLE001
            eror_mentahan = f"{stdout.getvalue()}{traceback.format_exc()}"
            ansi_err = self.format_log_ansi(eror_mentahan)
            await ctx.message.add_reaction("❌")
            return await self._kirim_container(ctx, ansi_err, warna=0xE56160, footer=subteks_footer)
        
        nilai = stdout.getvalue()
        hasil = (nilai if nilai else '') if ret is None else (f"{nilai}{ret}" if nilai else str(ret))
        str_hasil = str(hasil)
        
        if self.bot.http.token:
            str_hasil = str_hasil.replace(self.bot.http.token, "[TOKEN_DISENSOR]")
        
        is_eror = bool(self.re_soft_err.search(str_hasil))
        
        if is_eror:
            str_hasil = self.format_log_ansi(str_hasil)
            tag_bhs, warna = "ansi", 0xE56160
            await ctx.message.add_reaction("❌")
        else:
            tag_bhs, warna = "py", 0xD675C1
            await ctx.message.add_reaction("✅")
        
        BATAS_TEKS = 1900
        jumlah_teks = [str_hasil[i:i + BATAS_TEKS] for i in range(0, len(str_hasil), BATAS_TEKS)]
        
        for indeks, teks in enumerate(jumlah_teks[:5]):
            footer = subteks_footer if indeks == len(jumlah_teks[:5]) - 1 else None
            await self._kirim_container(ctx, teks, warna=warna, tag_bhs=tag_bhs, footer=footer)
        
        if len(jumlah_teks) > 5:
            await ctx.send("```... [Output melebihi batas teks]```")
    
    @_eval.error
    async def error(self, ctx, error:commands.CommandError):
        if isinstance(error, commands.CommandInvokeError):
            error = error.original
        
        if isinstance(error, commands.NotOwner):
            await ctx.send("Cuma kak Abin yang bisa pakai command ini! 💢")
        else:
            await ctx.send(f"Ada error internal:\n`{type(error).__name__}: {error}`")


async def setup(bot):
    await bot.add_cog(Eval(bot))