import datetime
import json
import os
import platform
import shutil
import socket
import subprocess
import sys
import time
import urllib.request

import aiosqlite
import discord
import psutil
from discord.ext import commands


class InformasiSistem:
    @staticmethod
    def warna_lingkaran(latensi) -> str:
        if not isinstance(latensi, (int, float)):
            return "⚫"
        if latensi < 250:
            return "🟢"
        elif latensi < 300:
            return "🟡"
        elif latensi < 375:
            return "🟠"
        else:
            return "🔴"
    
    @staticmethod
    def baca_info_git() -> tuple[str, str, int]:
        try:
            keluaran = (
                subprocess.check_output(
                    ["git", "log", "-1", "--format=%h,%H,%ct"],
                    stderr=subprocess.DEVNULL,
                    timeout=2,
                )
                .decode("utf-8")
                .strip()
            )
            hash_commit, hash_panjang, waktu_commit = keluaran.split(",")
            return hash_commit, hash_panjang, int(waktu_commit)
        except Exception:  # noqa: BLE001, S110
            pass
        
        try:
            req = urllib.request.Request(
                "https://api.github.com/repos/BinRoom-Devs/Aika-Yokina-BinRoom-Mascot-Discord-Bot/commits/main",
                headers={"User-Agent": "Aika-Bot-Version-Checker"},
            )
            with urllib.request.urlopen(req, timeout=2) as response:
                data = json.loads(response.read().decode("utf-8"))
                hash_panjang = data["sha"]
                hash_commit = hash_panjang[:7]
                iso_date = data["commit"]["committer"]["date"]
                dt = datetime.datetime.fromisoformat(iso_date.replace("Z", "+00:00"))
                waktu_commit = int(dt.timestamp())
                return hash_commit, hash_panjang, waktu_commit
        except Exception:  # noqa: BLE001
            return "N/A", "", 0
    
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
                    return "[HeavenCloud](https://heavencloud.in/)"
                elif "IPXO GTT" in provider_upper:
                    return "[Wispbyte](https://wispbyte.com/)"
                elif "TELKOM INDONESIA" in provider_upper:
                    return "Lokal (self-hosted)"
                
                if provider:
                    return provider
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
    def format_ukuran(jumlah_mb:float) -> str:
        if jumlah_mb >= 1024:
            return f"{jumlah_mb / 1024:.1f} GB"
        return f"{int(jumlah_mb)} MB"
    
    @staticmethod
    def baca_total_ram_container() -> float:
        jalur_cgroup = [
            "/sys/fs/cgroup/memory.max",
            "/sys/fs/cgroup/memory/memory.limit_in_bytes",
        ]
        for jalur in jalur_cgroup:
            if os.path.exists(jalur):
                try:
                    with open(jalur, "r") as f:
                        nilai = f.read().strip()
                        if nilai != "max" and nilai.isdigit():
                            batas_bytes = int(nilai)
                            if batas_bytes < (1024**4):
                                return batas_bytes / (1024 * 1024)
                except Exception:  # noqa: BLE001, S110
                    pass
        return psutil.virtual_memory().total / (1024 * 1024)
    
    @classmethod
    def baca_ukuran_bot_mb(cls, jalur:str='.') -> float:
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
    def baca_alokasi_sistem(cls) -> str:
        proses = psutil.Process(os.getpid())
        cpu_cores = psutil.cpu_count(logical=True) or 1
        raw_cpu = proses.cpu_percent(interval=None)
        persentase_cpu_bot = raw_cpu / cpu_cores
        
        ram_total_mb = cls.baca_total_ram_container()
        bot_ram_mb = proses.memory_info().rss / (1024 * 1024)
        persentase_ram_bot = (bot_ram_mb / ram_total_mb) * 100 if ram_total_mb > 0 else 0.0
        
        disk_total_mb, bot_disk_mb = cls.baca_total_disk_container()
        persentase_disk_bot = (bot_disk_mb / disk_total_mb) * 100 if disk_total_mb > 0 else 0.0
        
        cpu_str = f"{round(persentase_cpu_bot)}%"
        ram_str = f"{round(persentase_ram_bot)}% `{cls.format_ukuran(bot_ram_mb)}/{cls.format_ukuran(round(ram_total_mb))}`"
        disk_str = f"{round(persentase_disk_bot)}% `{cls.format_ukuran(bot_disk_mb)}/{cls.format_ukuran(round(disk_total_mb))}`"
        
        return f"CPU: {cpu_str}  •  RAM: {ram_str}  •  Disk: {disk_str}"


class Info(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.utils = InformasiSistem()
        
        self.jalur_db = "data/aika.db"
        self.link_repo = "https://github.com/BinRoom-Devs/Aika-Yokina-BinRoom-Mascot-Discord-Bot"
        
        self.hash_commit, self.hash_panjang, self.timestamp_commit = self.utils.baca_info_git()
    
    @property
    def nama(self) -> str:
        return self.bot.user.name if self.bot.user else "Aika Yokina"
    
    @property
    def icon(self) -> str:
        return self.bot.user.display_avatar.url if self.bot.user \
        else "https://cdn.discordapp.com/avatars/1533821291134582896/93b7ad6f1ca97eb0c4abbfa576f2f907.png?size=1024"
    
    @property
    def dev(self) -> str:
        return f"<@{self.bot.owner_id}>" if self.bot.owner_id else "@arumugi_4405"
    
    @property
    def tgl_buat(self) -> str:
        if self.bot.user:
            return discord.utils.format_dt(self.bot.user.created_at, style="D")
        return "3 Agustus 2026"
    
    @property
    def bot_id(self) -> int | str:
        return self.bot.user.id if self.bot.user else "1533821291134582896"
    
    @property
    def bhsa(self) -> str:
        return f"Python v{platform.python_version()}"
    
    @property
    def framework(self) -> str:
        return f"discord.py v{discord.__version__}"
    
    @property
    def os(self) -> str:
        return platform.system()
    
    async def emoji_aika(self) -> str:
        app_emoji = await self.bot.fetch_application_emojis()
        emoji_target = discord.utils.get(app_emoji, name="aikaboticonbulat")
        if emoji_target:
            return str(emoji_target)
        else:
            return "<:Aika_Yokina:1551065535091974276>"
    
    async def hitung_latensi(
        self, ctx:commands.Context, 
        pesan_awal:discord.Message|None,
    ) -> tuple[str, discord.Message]:
        
        latensi_ws = round(self.bot.latency * 1000)
        
        waktu_mulai_api = time.perf_counter()
        pesan = await ctx.send("Memuat info Aika...")
        waktu_selesai_pesan_awal = time.perf_counter()
        
        latensi_api = round((waktu_selesai_pesan_awal - waktu_mulai_api) * 1000)
        
        waktu_mulai_db = time.perf_counter()
        try:
            if os.path.exists(self.jalur_db):
                async with aiosqlite.connect(self.jalur_db) as db:
                    await db.execute("SELECT 1")
                latensi_db = round((time.perf_counter() - waktu_mulai_db) * 1000, 2)
                db_text = f"{round(latensi_db)} ms"
            else:
                latensi_db = None
                db_text = "N/A"
        except Exception:  # noqa: BLE001
            latensi_db = None
            db_text = "Offline"
        
        if pesan_awal:
            try:
                await pesan_awal.delete()
            except Exception:  # noqa: BLE001, S110
                pass
        
        waktu_pesan = pesan.created_at
        waktu_ctx = (
            ctx.interaction.created_at
            if ctx.interaction
            else ctx.message.created_at
        )
        latensi_rtt = abs(round((waktu_pesan - waktu_ctx).total_seconds() * 1000))
        
        format_ping = (
            f"{self.utils.warna_lingkaran(latensi_ws)} **WebSocket: {latensi_ws} ms**     "
            f"{self.utils.warna_lingkaran(latensi_api)} REST API: {latensi_api} ms\n"
            f"{self.utils.warna_lingkaran(latensi_rtt)} Round-Trip: {latensi_rtt} ms     "
            f"{self.utils.warna_lingkaran(latensi_db)} Database: {db_text}\n"
        )
        return format_ping, pesan
    
    def baca_versi(self) -> str:
        version_cog = self.bot.get_cog("VersiAika") or self.bot.get_cog("cogs.version")
        if version_cog and hasattr(version_cog, "__version__"):
            return version_cog.__version__
        elif "stats" in sys.modules and hasattr(sys.modules["stats"], "__version__"):
            return sys.modules["stats"].__version__
        return "N/A"
    
    @property
    def uptime(self) -> str:
        cog_uptime = self.bot.get_cog("Uptime")
        if cog_uptime and hasattr(cog_uptime, "start_time"):
            skrg = datetime.datetime.now(datetime.timezone.utc)
            total_detik = int((skrg - cog_uptime.start_time).total_seconds())
            
            detik_per_menit = 60
            detik_per_jam = 3600
            detik_per_hari = 86400
            detik_per_minggu = 604800
            detik_per_bulan = 2592000   # ~30 hari
            detik_per_tahun = 31536000  # ~365 hari
            
            tahun, sisa = divmod(total_detik, detik_per_tahun)
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
        
        return "N/A"
    
    def pemisah(self, container):
        container.add_item(discord.ui.Separator(spacing=discord.SeparatorSpacing.small))
    
    @commands.hybrid_command(name="info", description="Menampilkan informasi lengkap Aika")
    async def info(self, ctx:commands.Context):
        ping_info, target_pesan = await self.hitung_latensi(ctx, None)
        
        container = discord.ui.Container(accent_color=0xD675C1)
        
        emoji_aika = await self.emoji_aika()
        judul = f"### {emoji_aika}  Informasi Lengkap Aika"
        container.add_item(discord.ui.TextDisplay(content=judul))
        
        self.pemisah(container)
        
        bagian_1 = (
            f"- **Nama:** {self.nama}\n"
            f"- **Pengembang:** {self.dev}\n"
            f"- **Dibuat:** {self.tgl_buat}\n"
            f"- **ID:** `{self.bot_id}`\n"
            f"- **Waktu aktif:** {self.uptime}"
        )
        container.add_item(discord.ui.Section(
            discord.ui.TextDisplay(content=bagian_1),
            accessory=discord.ui.Thumbnail(media=self.icon)
        ))
        
        self.pemisah(container)
        
        bagian_2 = (
            f"- **Bahasa program:** {self.bhsa}\n"
            f"- **Framework:** {self.framework}\n"
            f"- **Sistem operasi:** {self.os}\n"
            f"- **Hosting:** {self.utils.baca_provider_hosting()}"
        )
        container.add_item(discord.ui.Section(
            discord.ui.TextDisplay(content=bagian_2),
            accessory=discord.ui.Button(
                style=discord.ButtonStyle.link,
                label="Source code",
                url=self.link_repo
            )
        ))
        
        self.pemisah(container)
        
        bagian_3 = (
            "**Alokasi sistem:**\n"
            f"{self.utils.baca_alokasi_sistem()}"
        )
        container.add_item(discord.ui.TextDisplay(content=bagian_3))
        
        self.pemisah(container)
        
        bagian_4 = (
            "**Latensi/ping**:\n"
            f"{ping_info}"
        )
        container.add_item(discord.ui.TextDisplay(content=bagian_4))
        
        self.pemisah(container)
        
        tgl_update = f"<t:{self.timestamp_commit}:d>" if self.timestamp_commit else "N/A"
        link_build = f"{self.link_repo}/commit/{self.hash_panjang}" if self.hash_panjang else self.link_repo
        info_build = f"[`{self.hash_commit}`]({link_build})" if self.hash_commit != "N/A" else "N/A"
        
        footer = f"-# Aika Yokina {self.baca_versi()}  •  Build {info_build} (Update {tgl_update})"
        container.add_item(discord.ui.TextDisplay(content=footer))
        
        await target_pesan.edit(
            content=None,
            view=discord.ui.LayoutView().add_item(container),
            allowed_mentions=discord.AllowedMentions.none()
        )


async def setup(bot:commands.Bot):
    await bot.add_cog(Info(bot))