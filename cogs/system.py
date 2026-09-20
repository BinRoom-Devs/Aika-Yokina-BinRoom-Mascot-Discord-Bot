import os
import shutil
import time

import discord
import psutil
from discord.ext import commands

waktu_mulai = time.time()

# Inisialisasi pelacakan CPU proses awal
proc = psutil.Process(os.getpid())
proc.cpu_percent()

def baca_limit_ram_container() -> float:
    jalur_cgroup = [
        "/sys/fs/cgroup/memory.max",
        "/sys/fs/cgroup/memory/memory.limit_in_bytes"
    ]
    for jalur in jalur_cgroup:
        if os.path.exists(jalur):
            try:
                with open(jalur, "r") as f:
                    val = f.read().strip()
                    if val != "max" and val.isdigit():
                        batas_bytes = int(val)
                        if batas_bytes < (1024 ** 4):  # Abaikan jika > 1 TB
                            return batas_bytes / (1024 * 1024)
            except Exception:  # noqa: BLE001, S110
                pass
    return psutil.virtual_memory().total / (1024 * 1024)

def get_container_disk_limits() -> tuple[float, float]:
    bot_used_mb = get_bot_directory_size_mb(".")
    
    # 1. Cek jika host menyediakan ENV disk quota (Pterodactyl/Custom ENV)
    env_disk = os.getenv("SERVER_DISK")  # Pterodactyl menyediai variabel ini di beberapa setup
    if env_disk and env_disk.isdigit():
        total_mb = float(env_disk)
        return total_mb, max(0.0, total_mb - bot_used_mb)

    # 2. Cek drive via shutil
    try:
        total, _used, _free = shutil.disk_usage(".")
        total_mb = total / (1024 * 1024)
        
        # Jika berada di container cloud (RAM < 2GB) tapi disk terbaca raksasa (>100GB host leak)
        ram_limit = baca_limit_ram_container()
        if total_mb > 100000 and ram_limit < 2000:
            total_mb = 1024.0  # Default container quota fallback
    except Exception:  # noqa: BLE001
        total_mb = 1024.0

    free_mb = max(0.0, total_mb - bot_used_mb)
    return total_mb, free_mb

def get_bot_directory_size_mb(jalur:str=".") -> float:
    """Menghitung total ukuran berkas bot di direktori aktif."""
    total_size = 0
    try:
        for dirjalur, dirnames, filenames in os.walk(jalur):
            for f in filenames:
                fp = os.jalur.join(dirjalur, f)
                if not os.jalur.islink(fp):
                    total_size += os.jalur.getsize(fp)
    except Exception:  # noqa: BLE001, S110
        pass
    return total_size / (1024 * 1024)

def make_bar(persen:float, panjang:int=11) -> str:
    terisi = round(panjang * max(0.0, min(persen, 100.0)) / 100)
    return "█" * terisi + "░" * (panjang - terisi)

def format_size(mb_value:float) -> str:
    if mb_value >= 1024:
        return f"{mb_value / 1024:.1f} GB"
    return f"{int(mb_value)} MB"


class Sistem(commands.Cog):
    def __init__(self, bot:commands.Bot):
        self.bot = bot
    
    @commands.hybrid_command(name="sistem", aliases=["system"], description="Liat statistik tentang bot ini.")
    async def sistem(self, ctx:commands.Context):
        await ctx.defer()

        # --- METRIK SISTEM ---
        process = psutil.Process(os.getpid())

        #penggunaan CPU
        cpu_cores = psutil.cpu_count(logical=True) or 1
        raw_cpu = process.cpu_percent(interval=None)
        bot_cpu_pct = raw_cpu / cpu_cores

        #penggunaan ram
        ram_total_mb = baca_limit_ram_container()
        bot_ram_mb = process.memory_info().rss / (1024 * 1024)
        ram_avail_mb = max(0.0, ram_total_mb - bot_ram_mb)
        bot_ram_pct = (bot_ram_mb / ram_total_mb) * 100 if ram_total_mb > 0 else 0.0

        #penggunaan disk
        disk_total_mb, disk_free_mb = get_container_disk_limits()
        bot_disk_mb = get_bot_directory_size_mb(".")
        bot_disk_pct = (bot_disk_mb / disk_total_mb) * 100 if disk_total_mb > 0 else 0.0

        #pendeteksi cloud dinamis
        is_cloud = ram_total_mb < 1000
        cpu_limit = 60.0 if is_cloud else 100.0
        cpu_rel_pct = min((bot_cpu_pct / cpu_limit) * 100, 100.0)

        #formatting blok display 
        cpu_str  = f"{bot_cpu_pct:.2f}%"
        ram_str  = f"{format_size(bot_ram_mb)} ({bot_ram_pct:.1f}%)"
        disk_str = f"{format_size(bot_disk_mb)} ({bot_disk_pct:.2f}%)"

        sys_info = (
            "```\n"
            f"CPU : {cpu_str:<15} [{make_bar(cpu_rel_pct)}] {int(cpu_limit)}%\n"
            f"RAM : {ram_str:<15} [{make_bar(bot_ram_pct)}] {format_size(ram_total_mb)}\n"
            f"Disk: {disk_str:<15} [{make_bar(bot_disk_pct)}] {format_size(disk_total_mb)}\n"
            "```"
        )
        
        embed = discord.Embed(title="Rincian Sistem Aika", description=sys_info, color=0xD675C1)
        
        avatar = self.bot.user.display_avatar.url
        embed.set_author(name=str(self.bot.user), icon_url=avatar)
        embed.set_thumbnail(url=avatar)

        #bagian CPU
        try:
            freq_info = psutil.cpu_freq()
            cpu_freq = f"{freq_info.current:.0f} MHz" if freq_info and freq_info.current else "N/A"
        except Exception:  # noqa: BLE001
            cpu_freq = "N/A"

        embed.add_field(
            name="CPU",
            value=(
                f"**Cores:** {cpu_cores} Threads\n"
                f"**Clock:** {cpu_freq}\n"
                f"**Batas:** {int(cpu_limit)}%"
            ),
            inline=True
        )

        #bagian RAM
        embed.add_field(
            name="RAM",
            value=(
                f"**Digunakan:** {format_size(bot_ram_mb)}\n"
                f"**Tersisa:** {format_size(ram_avail_mb)}\n"
                f"**Terpakai:** {bot_ram_pct:.1f}%"
            ),
            inline=True
        )

        #bagian disk
        try:
            partitions = psutil.disk_partitions()
            root_fs = next((p.fstype for p in partitions if p.mountpoint in ('/', 'C:\\')), "N/A")
            if not root_fs or root_fs == "N/A":
                root_fs = partitions[0].fstype if partitions else "N/A"
        except Exception:  # noqa: BLE001
            root_fs = "N/A"

        try:
            disk_io = process.io_counters()
            read_mb = disk_io.read_bytes / (1024 ** 2)
            write_mb = disk_io.write_bytes / (1024 ** 2)
            io_str = f"R: {read_mb:.1f}MB, W: {write_mb:.1f}MB"
        except Exception:  # noqa: BLE001
            io_str = "N/A"

        embed.add_field(
            name="Disk",
            value=(
                f"**Tersedia:** {format_size(disk_free_mb)}\n"
                f"**Format:** {root_fs.upper()}\n"
                f"**I/O:** {io_str}"
            ),
            inline=True
        )

        #ersion = ''
        #version_cog = self.bot.get_cog("VersiAika") or self.bot.get_cog("cogs.version")
        #if version_cog and hasattr(version_cog, "__version__"):
        #    version = version_cog.__version__
        #elif "stats" in sys.modules and hasattr(sys.modules["stats"], "__version__"):
        #    version = sys.modules["stats"].__version__
        
        #nama_hostingan = get_hosting_provider()
        #embed.set_footer(text=f"Versi Aika: {version}")

        is_admin = getattr(ctx.author.guild_permissions, "administrator", False) if ctx.guild else False
        
        await ctx.send(
            content="...ngapain liat2 internalku? Gak penting amat 🧐" if not is_admin else None,
            embed=embed,
        )
        print("[Aika] Command stats dieksekusi")

async def setup(bot:commands.Bot):
    await bot.add_cog(Sistem(bot))