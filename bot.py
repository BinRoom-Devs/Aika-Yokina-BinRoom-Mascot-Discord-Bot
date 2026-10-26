import asyncio
import difflib
import os
import subprocess
import sys
from pathlib import Path

import discord
from discord.ext import commands

import config
import database

intents = discord.Intents.all()
intents.messages = True
intents.message_content = True
intents.members = True


class AikaYokina(commands.Bot):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
    
    async def setup_hook(self) -> None:
        await database.init_db()
    
    async def interaction_check(self, interaction:discord.Interaction) -> bool:
        if interaction.guild is None and interaction.user.id != config.pengaturan.id_pemilik:
            print("[Aika] Ada chat di DM. Aika langsung cegat.")
            return False
        return True


aika = AikaYokina(
    command_prefix="ak!",
    intents=intents,
    case_insensitive=True,
    help_command=None,
    allowed_mentions=discord.AllowedMentions.none()
)


@aika.check
async def block_dm_prefix_commands(ctx:commands.Context) -> bool:
    if ctx.guild is None and ctx.author.id != config.pengaturan.id_pemilik:
        print("[Aika] Ada command prefix lewat DM, Aika cegat.")
        return False
    return True


@aika.event
async def on_ready():
    print(f"🟢 {aika.user} sudah online.")
    
    try:
        synced = await aika.tree.sync()
        print(f"[Aika] {len(synced)} slash command disinkronkan.")
    except (discord.HTTPException, discord.Forbidden) as e:
        print(f"[Aika] Gagal menyinkronkan slash command: {e}")


async def load_cogs():
    jalur_cogs = Path("cogs")
    if jalur_cogs.exists():
        for jalur_file in jalur_cogs.rglob("*.py"):
            if jalur_file.name.startswith("_"):
                continue
            
            jalur_relatif = jalur_file.relative_to(Path("."))
            nama_format = ".".join(jalur_relatif.with_suffix("").parts)
            
            try:
                await aika.load_extension(nama_format)
                print(f"[Aika] Cog dimuat: {nama_format}")
            except Exception as why:  # noqa: BLE001
                print(f"[Aika] Gagal memuat cog {nama_format}: {why}")


async def start_bot():
    if not config.pengaturan.token_bot:
        raise ValueError(f"[Aika] TOKEN_BOT tidak ditemukan! Dicek di jalur: {config.pengaturan.jalur_env.absolute()}")
    
    await load_cogs()
    await aika.start(config.pengaturan.token_bot)


@aika.event
async def on_command_error(ctx:commands.Context, error:commands.CommandError):
    if isinstance(error, commands.CommandNotFound):
        invoked_cmd = ctx.invoked_with
        if not invoked_cmd:
            return
        
        slash_cmds = {cmd.name for cmd in aika.tree.get_commands()}
        if invoked_cmd in slash_cmds:
            await ctx.reply(
                f"❌ Command `{invoked_cmd}` hanya tersedia via slash command.\n\n"
                f"-# Coba `/{invoked_cmd}`."
            )
            return
        
        slash_mirip = difflib.get_close_matches(invoked_cmd, list(slash_cmds), n=1, cutoff=0.7)
        if slash_mirip:
            await ctx.reply(
                f"❌ Perintah `{invoked_cmd}` tidak ditemukan.\n\n"
                f"-# Maksudmu slash command `/{slash_mirip[0]}`?"
            )
            return
        
        semua_cmd = []
        for cmd in aika.walk_commands():
            if not cmd.hidden:
                semua_cmd.append(cmd.qualified_name)
                semua_cmd.extend(cmd.aliases)
        
        cocok = difflib.get_close_matches(invoked_cmd, semua_cmd, n=1, cutoff=0.6)
        if cocok:
            saran = cocok[0]
            await ctx.reply(
                f"❌ Command `{invoked_cmd}` tidak ditemukan.\n\n"
                f"-# Mungkin maksudmu `{ctx.prefix}{saran}`?"
            )
        else:
            await ctx.reply(f"❌ Command `{invoked_cmd}` tidak ditemukan.")
        return


def start_card_api(): #Card API, kartu tampilan bot yang muncul di readme github
    card_api_path = Path(__file__).parent / "card_api.py"
    if not card_api_path.exists():
        print("[Aika] card_api.py tidak ditemukan, melewati Card API...")
        return None
    
    print("[Aika] Memulai Card API...")
    
    process = subprocess.Popen(
        [sys.executable, str(card_api_path)],
        stdout=None,
        stderr=None
    )
    print(f"[Aika] Card API dimulai dengan PID: {process.pid}")
    return process


if __name__ in {"__main__", "__mp_main__"}:
    enable_card_api = os.getenv("ENABLE_CARD_API", "true").lower() == "true"
    
    card_api_process = None
    if enable_card_api:
        card_api_process = start_card_api()
    
    try:
        asyncio.run(start_bot())
    except KeyboardInterrupt:
        print("\n[Aika] Mematikan bot...")
    finally:
        if card_api_process:
            print("[Aika] Mematikan Card API...")
            card_api_process.terminate()
            try:
                card_api_process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                card_api_process.kill()
                card_api_process.wait()
            print("[Aika] Card API dimatikan.")