import datetime
import json
import os
import platform
import re
import shutil
import socket
import urllib.request

import discord
import psutil
from discord.ext import commands

from config import pengaturan

#kode warna ansi
ESC = "\u001b"
RESET = f"{ESC}[0m"
ABU = f"{ESC}[30m"
MERAH = f"{ESC}[31m"
HIJAU = f"{ESC}[32m"
KUNING = f"{ESC}[33m"
BIRU = f"{ESC}[34m"
PINK = f"{ESC}[35m"
CYAN = f"{ESC}[36m"
PUTIH = f"{ESC}[37m"
PINK_TEBAL = f"{ESC}[1;35m"

#ansi art aika ala logo fastfetch linux (huruf + simbol berwarna), 20 karakter lebar, 13 baris
AIKA_ANSI_ART = [
    f"   {PINK}.,,,,.,,,,.{RESET}      ",
    f"  {PINK}cccccccccccccc,{RESET}   ",
    f" {PINK},cccc{MERAH}888{PINK}cccccccc,{RESET}  ",
    f" {PINK}ccccc{MERAH}8888{PINK}cccccccc;{RESET} ",
    f" {PINK}:ccccc{PUTIH}::{PINK}ccccccccco{RESET} ",
    f" {PINK}:cccc{PUTIH}::c{CYAN}00{PUTIH}::::::{PINK}c'{RESET} ",
    f" {PINK}:cocc{PUTIH}:::{CYAN}O0{PUTIH}:::{CYAN}OO{PUTIH}:{PINK};{RESET}  ",
    f" {PINK}ccocc{PUTIH}::::::::::{PINK}c;{RESET}  ",
    f"{PINK};;:o;;c{PUTIH}::::::::{PINK}cc{PUTIH}.{RESET}  ",
    f"    {KUNING}.{PUTIH}x;::;:c{KUNING}ooocc{PUTIH}ccc{RESET}",
    f"{KUNING}..,oo{PUTIH}c:::::cc{KUNING}cccc{PUTIH}ccc{RESET}",
    f"{PUTIH}ccc{KUNING}cccc{PUTIH}::::c{KUNING}ccccco{PUTIH}cc{RESET}",
    f"{PUTIH}cccc{KUNING}ccc{PUTIH}::::{KUNING}cccccccc{PUTIH}c{RESET}",
]

#jarak spacing penyeimbang kolom kiri buat baris info ke-12 dst
SPASI_KIRI = " " * 20


class InformasiFastfetch:
    @staticmethod
    def warna_persen(persen: float) -> str:
        nilai = f"{round(persen)}%"
        if persen < 60:
            return f"{HIJAU}{nilai}{RESET}"
        elif persen < 85:
            return f"{KUNING}{nilai}{RESET}"
        return f"{MERAH}{nilai}{RESET}"
    
    @staticmethod
    def format_ukuran(jumlah_mb: float) -> str:
        if jumlah_mb >= 1024:
            return f"{jumlah_mb / 1024:.2f} GiB"
        return f"{int(jumlah_mb)} MiB"
    
    @staticmethod
    def baca_os() -> str:
        sistem = platform.system()
        arsitektur = platform.machine()
        if sistem == "Linux" and os.path.exists("/etc/os-release"):
            try:
                with open("/etc/os-release", "r", encoding="utf-8") as f:
                    for baris in f:
                        if baris.startswith("PRETTY_NAME="):
                            nama_os = baris.split("=", 1)[1].strip().strip('"')
                            return f"{nama_os} {arsitektur}".strip()
            except Exception:  # noqa: BLE001, S110
                pass
        return f"{sistem} {arsitektur}".strip()
    
    @staticmethod
    def baca_kernel() -> str:
        return f"{platform.system()} {platform.release()}".strip()
    
    @staticmethod
    def baca_provider_hosting() -> str:
        try:
            req = urllib.request.Request(
                "http://ip-api.com/json/?fields=isp,org,as",
                headers={"User-Agent": "Mozilla/5.0"},
            )
            with urllib.request.urlopen(req, timeout=1.5) as response:
                data = json.loads(response.read().decode())
                provider = data.get("org") or data.get("isp") or ""
                if provider.startswith("AS"):
                    provider = " ".join(provider.split()[1:])
                
                provider_upper = provider.upper()
                if "SNAJU DEVELOPMENT" in provider_upper:
                    return "HeavenCloud"
                elif "IPXO GTT" in provider_upper:
                    return "Wispbyte"
                elif "TELKOM INDONESIA" in provider_upper:
                    return "Lokal (self-hosted)"
                
                if provider:
                    return re.sub(r"\[([^\]]+)\]\([^)]+\)", r"\1", provider)
        except Exception:  # noqa: BLE001, S110
            pass
        
        try:
            hostname = socket.gethostname()
            if hostname:
                return hostname
        except Exception:  # noqa: BLE001, S110
            pass
        return "Lokal (self-hosted)"
    
    @staticmethod
    def baca_total_ram_container() -> float:
        jalur_cgroup = [
            "/sys/fs/cgroup/memory.max",
            "/sys/fs/cgroup/memory/memory.limit_in_bytes",
        ]
        for jalur in jalur_cgroup:
            if os.path.exists(jalur):
                try:
                    with open(jalur, "r", encoding="utf-8") as f:
                        nilai = f.read().strip()
                        if nilai != "max" and nilai.isdigit():
                            batas_bytes = int(nilai)
                            if batas_bytes < (1024**4):
                                return batas_bytes / (1024 * 1024)
                except Exception:  # noqa: BLE001, S110
                    pass
        return psutil.virtual_memory().total / (1024 * 1024)
    
    @classmethod
    def baca_ukuran_bot_mb(cls, jalur:str=".") -> float:
        ukuran_total = 0
        try:
            for dirjalur, _, nama_file in os.walk(jalur):
                for f in nama_file:
                    fp = os.path.join(dirjalur, f)
                    if not os.path.islink(fp):
                        ukuran_total += os.path.getsize(fp)
        except Exception:  # noqa: BLE001, S110
            pass
        return ukuran_total / (1024 * 1024)
    
    @classmethod
    def baca_total_disk_container(cls) -> tuple[float, float]:
        pemakaian_bot_mb = cls.baca_ukuran_bot_mb(".")
        
        env_disk = os.getenv("SERVER_DISK")
        if env_disk and env_disk.isdigit():
            total_mb = float(env_disk)
            return total_mb, pemakaian_bot_mb
        
        try:
            total, _dipakai, _sisa = shutil.disk_usage(".")
            total_mb = total / (1024 * 1024)
            batas_ram = cls.baca_total_ram_container()
            if total_mb > 100000 and batas_ram < 2000:
                total_mb = 1024.0
        except Exception:  # noqa: BLE001
            total_mb = 1024.0
        
        return total_mb, pemakaian_bot_mb
    
    @classmethod
    def baca_metrik_sistem(cls) -> dict[str, str]:
        proses = psutil.Process(os.getpid())
        cpu_cores = psutil.cpu_count(logical=True) or 1
        raw_cpu = proses.cpu_percent(interval=None)
        persentase_cpu_bot = raw_cpu / cpu_cores
        
        nama_cpu = ""
        if os.path.exists("/proc/cpuinfo"):
            try:
                with open("/proc/cpuinfo", "r", encoding="utf-8") as f:
                    for baris in f:
                        if "model name" in baris:
                            nama_cpu = baris.split(":", 1)[1].strip()
                            break
            except Exception:  # noqa: BLE001, S110
                pass
        if not nama_cpu:
            nama_cpu = platform.processor() or "CPU"
        nama_cpu = re.sub(r"\((R|TM|tm)\)|CPU|Processor", "", nama_cpu)
        nama_cpu = " ".join(nama_cpu.split())
        if len(nama_cpu) > 22:
            nama_cpu = nama_cpu[:22].rstrip()
        
        ram_total_mb = cls.baca_total_ram_container()
        bot_ram_mb = proses.memory_info().rss / (1024 * 1024)
        persen_ram = (bot_ram_mb / ram_total_mb) * 100 if ram_total_mb > 0 else 0.0
        
        try:
            swap = psutil.swap_memory()
            swap_total_mb = swap.total / (1024 * 1024)
            swap_pakai_mb = swap.used / (1024 * 1024)
            persen_swap = swap.percent
        except Exception:  # noqa: BLE001
            swap_total_mb, swap_pakai_mb, persen_swap = 0.0, 0.0, 0.0
        
        disk_total_mb, bot_disk_mb = cls.baca_total_disk_container()
        persen_disk = (bot_disk_mb / disk_total_mb) * 100 if disk_total_mb > 0 else 0.0
        
        cpu_info = f"{nama_cpu} ({cpu_cores}) @ {cls.warna_persen(persentase_cpu_bot)}"
        ram_info = (
            f"{cls.format_ukuran(bot_ram_mb)} / {cls.format_ukuran(round(ram_total_mb))} "
            f"({cls.warna_persen(persen_ram)})"
        )
        if swap_total_mb > 0:
            swap_info = (
                f"{cls.format_ukuran(swap_pakai_mb)} / {cls.format_ukuran(round(swap_total_mb))} "
                f"({cls.warna_persen(persen_swap)})"
            )
        else:
            swap_info = f"0 MiB / 0 MiB ({cls.warna_persen(0)})"
        
        disk_info = (
            f"{cls.format_ukuran(bot_disk_mb)} / {cls.format_ukuran(round(disk_total_mb))} "
            f"({cls.warna_persen(persen_disk)})"
        )
        
        return {
            "cpu": cpu_info,
            "ram": ram_info,
            "swap": swap_info,
            "disk": disk_info,
        }


class Fastfetch(commands.Cog):
    def __init__(self, bot:commands.Bot):
        self.bot = bot
        self.utils = InformasiFastfetch()
    
    @property
    def user_host(self) -> tuple[str, str]:
        if self.bot.user:
            nama_bersih = re.sub(r"[^a-zA-Z0-9]", "", self.bot.user.name).lower() or "aikayokina"
        else:
            nama_bersih = "aikayokina"
        return nama_bersih, "discord"
    
    @property
    def dependencies(self) -> str:
        return f"Python v{platform.python_version()}"
    
    @property
    def uptime(self) -> str:
        cog_uptime = self.bot.get_cog("Uptime")
        waktu_mulai = getattr(cog_uptime, "start_time", None)
        
        if waktu_mulai is not None:
            skrg = datetime.datetime.now(datetime.UTC)
            total_detik = int((skrg - waktu_mulai).total_seconds())
        else:
            try:
                proses = psutil.Process(os.getpid())
                total_detik = int(datetime.datetime.now().timestamp() - proses.create_time())  # noqa: DTZ005
            except Exception:  # noqa: BLE001
                return "N/A"
        
        detik_per_menit = 60
        detik_per_jam = 3600
        detik_per_hari = 86400
        detik_per_minggu = 604800
        detik_per_bulan = 2592000
        detik_per_tahun = 31536000
        
        tahun, sisa = divmod(max(0, total_detik), detik_per_tahun)
        bulan, sisa = divmod(sisa, detik_per_bulan)
        minggu, sisa = divmod(sisa, detik_per_minggu)
        hari, sisa = divmod(sisa, detik_per_hari)
        jam, sisa = divmod(sisa, detik_per_jam)
        menit, detik = divmod(sisa, detik_per_menit)
        
        unit = [
            (tahun, "tahun"),
            (bulan, "bulan"),
            (minggu, "minggu"),
            (hari, "hari"),
            (jam, "jam"),
            (menit, "menit"),
            (detik, "detik"),
        ]
        
        terisi = [(nilai, nama) for nilai, nama in unit if nilai > 0]
        if not terisi:
            return "0 detik"
        
        terpilih = terisi[:2]
        return ", ".join(f"{nilai} {nama}" for nilai, nama in terpilih)
    
    def susun_fastfetch_ansi(self) -> str:
        nama_user, nama_host = self.user_host
        panjang_garis = len(f"{nama_user}@{nama_host}")
        metrik = self.utils.baca_metrik_sistem()
        
        #palet warna: balok solid (3 karakter per warna), baris atas normal, baris bawah terang
        kode_warna = (30, 31, 32, 33, 34, 35, 36, 37)
        palet_normal = "".join(f"{ESC}[{k}m███" for k in kode_warna) + RESET
        palet_terang = "".join(f"{ESC}[1;{k}m███" for k in kode_warna) + RESET
        
        info_kanan = [
            f"{PINK_TEBAL}{nama_user}{RESET}@{PINK_TEBAL}{nama_host}{RESET}",
            "-" * max(23, panjang_garis),
            f"{PINK_TEBAL}OS{RESET}: {self.utils.baca_os()}",
            f"{PINK_TEBAL}Host{RESET}: {self.utils.baca_provider_hosting()}",
            f"{PINK_TEBAL}Kernel{RESET}: {self.utils.baca_kernel()}",
            f"{PINK_TEBAL}Uptime{RESET}: {self.uptime}",
            f"{PINK_TEBAL}Dependencies{RESET}: {self.dependencies}",
            f"{PINK_TEBAL}UI Environment{RESET}: Discord",
            "",
            f"{PINK_TEBAL}CPU{RESET}: {metrik['cpu']}",
            f"{PINK_TEBAL}RAM{RESET}: {metrik['ram']}",
            f"{PINK_TEBAL}Swap{RESET}: {metrik['swap']}",
            f"{PINK_TEBAL}Disk{RESET}: {metrik['disk']}",
            "",
            palet_normal,
            palet_terang,
        ]
        
        pemisah = "   "
        baris_gabungan = []
        for idx in range(len(info_kanan)):
            kiri = AIKA_ANSI_ART[idx] if idx < len(AIKA_ANSI_ART) else SPASI_KIRI
            kanan = info_kanan[idx]
            if kanan:
                baris_gabungan.append(f"{kiri}{pemisah}{kanan}")
            else:
                baris_gabungan.append(kiri.rstrip())
        
        isi_ansi = "\n".join(baris_gabungan)
        return f"```ansi\n{isi_ansi}\n```"
    
    @commands.hybrid_command(
        name="fastfetch",
        description="Menampilkan informasi sistem Aika dengan gaya fastfetch Linux.",
        hidden=True,
    )
    async def fastfetch(self, ctx:commands.Context):
        pesan = await ctx.reply("Memuat fastfetch Aika...")
        
        teks_fastfetch = self.susun_fastfetch_ansi()
        container = discord.ui.Container(accent_color=pengaturan.warna_aika)
        container.add_item(discord.ui.TextDisplay(content=teks_fastfetch))
        
        await pesan.edit(
            content=None,
            view=discord.ui.LayoutView().add_item(container),
            allowed_mentions=discord.AllowedMentions.none(),
        )


async def setup(bot: commands.Bot):
    await bot.add_cog(Fastfetch(bot))