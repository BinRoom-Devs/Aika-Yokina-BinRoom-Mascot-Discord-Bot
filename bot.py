import asyncio
import os
from pathlib import Path

import discord
from discord.ext import commands, tasks
from dotenv import load_dotenv
from nicegui import app, ui

import database
from dashboard.auth import setup_auth
from dashboard.ui import state
from dashboard.ui.dashboard import setup_dashboard
from dashboard.ui.views.card import init_card_view

database.init_db()

DIREKTORI_UTAMA = Path(__file__).resolve().parent.parent
JALUR_ENV = DIREKTORI_UTAMA / ".env"
load_dotenv(dotenv_path=JALUR_ENV, override=True)

OWNER_ID = 1524951093560213638  # @arumugi_4405
TOKEN = os.getenv("TOKEN_BOT")

intents = discord.Intents.all()
intents.messages = True
intents.message_content = True
intents.members = True

setup_auth(app)


class AikaYokina(commands.Bot):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
    
    async def interaction_check(self, interaction:discord.Interaction) -> bool:
        if interaction.guild is None and interaction.user.id != OWNER_ID:
            state.log_event("[Aika] Ada chat di DM. Aika langsung cegat.")
            return False
        return True


aika = AikaYokina(command_prefix="ak!", intents=intents, case_insensitive=True)


@aika.check
async def block_dm_prefix_commands(ctx:commands.Context) -> bool:
    if ctx.guild is None and ctx.author.id != OWNER_ID:
        state.log_event("[Aika] Ada command prefix lewat DM, Aika cegat.")
        return False
    return True

@tasks.loop(seconds=3.0)
async def update_bot_metrics():
    if aika.is_ready():
        state.latency_ms = round(aika.latency * 1000)
        state.guild_count = len(aika.guilds)

@aika.event
async def on_ready():
    state.bot_status_text = f"Online sebagai {aika.user.name}"
    state.latency_ms = round(aika.latency * 1000)
    state.guild_count = len(aika.guilds)
    
    await aika.change_presence(
        status=discord.Status.dnd,
        activity=discord.CustomActivity(name=state.bot_activity),
    )
    state.log_event(f"🟢 {aika.user} sudah online.")
    
    if not update_bot_metrics.is_running():
        update_bot_metrics.start()
    
    try:
        synced = await aika.tree.sync()
        state.log_event(f"[Aika] {len(synced)} slash command disinkronkan.")
    except (discord.HTTPException, discord.Forbidden) as e:
        state.log_event(f"[Aika] Gagal menyinkronkan slash command: {e}")

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
                state.log_event(f"[Aika] Cog dimuat: {nama_format}")
            except Exception as why:  # noqa: BLE001
                state.log_event(f"[Aika] Gagal memuat cog {nama_format}: {why}")

async def start_bot():
    port = int(os.getenv("PORT", 16426))  # noqa: PLW1508
    protocol = "https" if os.path.exists("cert.pem") else "http"
    print(f"\n🌐 Dashboard live at: {protocol}://localhost:{port}\n")
    await load_cogs()
    asyncio.create_task(aika.start(TOKEN))


app.add_static_files("/static", "dashboard/static")
init_card_view(aika)
setup_dashboard(aika)
app.on_startup(start_bot)

if __name__ in {"__main__", "__mp_main__"}:
    port = int(os.getenv("PORT", 16426)) # noqa: PLW1508

    ui.run(
        host="0.0.0.0",
        port=port,
        show=False,
        reload=False,
        title="BinRoom - Aika Yokina Dashboard",
        forwarded_allow_ips="*",
    )