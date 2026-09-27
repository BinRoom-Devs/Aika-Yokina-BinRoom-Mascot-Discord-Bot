import asyncio
from collections import deque
from datetime import datetime, timezone

import aiohttp
import discord
from discord import SeparatorSpacing
from discord.ext import commands, tasks
from discord.ui import Container, LayoutView, Separator, TextDisplay

import database


class PendeteksiGangguan(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.riwayat = deque(maxlen=12)
        self.waktu_cek_terakhir: datetime | None = None
        self.lagi_keputus = False
    
    async def cog_load(self):
        await self.muat_riwayat()
        self.catat_restart("Inisialisasi proses / Aika me-restart")
        self.cek_health.start()
    
    def cog_unload(self):
        self.cek_health.cancel()
    
    async def buat_emoji_bar(self):
        try:
            emojis = await self.bot.fetch_application_emojis()
            hijau = discord.utils.get(emojis, name="greenbar")
            kuning = discord.utils.get(emojis, name="yellowbar")
            merah = discord.utils.get(emojis, name="redbar")
            return (
                str(hijau) if hijau else "🟩",
                str(kuning) if kuning else "🟨",
                str(merah) if merah else "🟥",
            )
        except Exception as e:  # noqa: BLE001
            print(f"⚠️ [Aika] Gagal mengambil custom emoji: {e}", flush=True)
            return "🟩", "🟨", "🟥"
    
    async def muat_riwayat(self):
        try:
            data = await database.get_downtime_history()
            self.riwayat.clear()
            for item in data:
                ts = item["timestamp"]
                if isinstance(ts, str):
                    ts = datetime.fromisoformat(ts)
                self.riwayat.append({
                    "status": item.get("status", "ok"),
                    "timestamp": ts,
                    "alasan": item.get("alasan", "Berjalan normal"),
                })
        except Exception as e:  # noqa: BLE001
            print(f"⚠️ [Aika] Database Downtime Tracker: gagal memuat riwayat ({e})", flush=True)
        
        if not self.riwayat:
            self.riwayat.append({
                "status": "ok",
                "timestamp": datetime.now(timezone.utc),
                "alasan": "Berjalan normal",
            })
            self.simpan_riwayat()
    
    def simpan_riwayat(self):
        try:
            terserialisasi = []
            for item in self.riwayat:
                ts = item["timestamp"]
                ts_str = ts.isoformat() if isinstance(ts, datetime) else str(ts)
                terserialisasi.append({
                    "status": item["status"],
                    "timestamp": ts_str,
                    "alasan": item["alasan"],
                })
            
            try:
                loop = asyncio.get_running_loop()
                loop.create_task(database.save_downtime_history(terserialisasi))
            except RuntimeError:
                pass
        
        except Exception as e:  # noqa: BLE001
            print(f"⚠️ [Aika] Database Downtime Tracker: gagal menyimpan riwayat ({e})", flush=True)
    
    def catat_restart(self, alasan:str):
        skrg = datetime.now(timezone.utc)
        self.waktu_cek_terakhir = skrg
        
        if self.riwayat and self.riwayat[-1]["status"] == "restart":
            entri_terakhir = self.riwayat[-1]
            selisih_waktu = (skrg - entri_terakhir["timestamp"]).total_seconds()
            
            if selisih_waktu <= 120:
                daftar_alasan = [a.strip() for a in entri_terakhir["alasan"].split(",")]
                if alasan not in daftar_alasan:
                    daftar_alasan.append(alasan)
                    entri_terakhir["alasan"] = ", ".join(daftar_alasan)
                
                entri_terakhir["timestamp"] = skrg
                self.simpan_riwayat()
                return
        
        self.riwayat.append({
            "status": "restart",
            "timestamp": skrg,
            "alasan": alasan,
        })
        self.simpan_riwayat()
    
    def catat_error(self, alasan:str):
        skrg = datetime.now(timezone.utc)
        self.waktu_cek_terakhir = skrg
        
        if self.riwayat and self.riwayat[-1]["status"] == "down":
            entri_terakhir = self.riwayat[-1]
            selisih_waktu = (skrg - entri_terakhir["timestamp"]).total_seconds()
            
            if selisih_waktu <= 120:
                daftar_alasan = [a.strip() for a in entri_terakhir["alasan"].split(",")]
                if alasan not in daftar_alasan:
                    daftar_alasan.append(alasan)
                    entri_terakhir["alasan"] = ", ".join(daftar_alasan)
                
                entri_terakhir["timestamp"] = skrg
                self.simpan_riwayat()
                return
        
        self.riwayat.append({
            "status": "down",
            "timestamp": skrg,
            "alasan": alasan,
        })
        self.simpan_riwayat()
    
    def buat_elemen_status(self, emoji_hijau:str, emoji_kuning:str, emoji_merah:str):
        kotak_status = []
        daftar_insiden = []
        total_ok = 0
        
        for indeks, entri in enumerate(self.riwayat, start=1):
            stempel_waktu = f"<t:{int(entri['timestamp'].timestamp())}:t>"
            
            if entri["status"] == "ok":
                kotak_status.append(emoji_hijau)
                total_ok += 1
            elif entri["status"] == "restart":
                kotak_status.append(emoji_kuning)
                daftar_insiden.append(
                    f"- {emoji_kuning} **Blok #{indeks}** ({stempel_waktu}): {entri['alasan']}"
                )
            else:  # 'down'
                kotak_status.append(emoji_merah)
                daftar_insiden.append(
                    f"- {emoji_merah} **Blok #{indeks}** ({stempel_waktu}): {entri['alasan']}"
                )
        
        grafik_status = "".join(kotak_status)
        
        total_entri = len(self.riwayat)
        persen_uptime = (total_ok / total_entri) * 100 if total_entri > 0 else 100.0
        
        stempel_tertua = int(self.riwayat[0]["timestamp"].timestamp())
        teks_waktu_lampau = f"<t:{stempel_tertua}:R>"
        
        garis = "▬▬▬▬▬▬▬▬"
        sub_bar = f"-# {teks_waktu_lampau} {garis} __{persen_uptime:.1f}% uptime__ {garis} Sekarang"
        
        return grafik_status, sub_bar, daftar_insiden
    
    @commands.Cog.listener()
    async def on_disconnect(self):
        self.lagi_keputus = True
        self.catat_error("Koneksi WebSocket Discord terputus")
        print("⚠️ [Aika] WebSocket Discord terputus!", flush=True)
    
    @commands.Cog.listener()
    async def on_resumed(self):
        if self.lagi_keputus:
            self.lagi_keputus = False
            print("✅ [Aika] Berhasil terhubung kembali!", flush=True)
    
    @commands.Cog.listener()
    async def on_ready(self):
        if self.lagi_keputus:
            self.lagi_keputus = False
            print("✅ [Aika] Terhubung!", flush=True)
    
    @tasks.loop(minutes=30)
    async def cek_health(self):
        skrg = datetime.now(timezone.utc)
        self.waktu_cek_terakhir = skrg
        
        if self.bot.is_closed() or self.bot.latency == float("inf"):
            self.catat_error("Gateway tidak dapat dijangkau")
            return
        
        self.riwayat.append({
            "status": "ok",
            "timestamp": skrg,
            "alasan": "Berjalan normal",
        })
        self.simpan_riwayat()
    
    @commands.hybrid_command(
        name="status",
        description="Menampilkan status online Aika sekaligus riwayat gangguan.",
        aliases=["uptime-status"]
    )
    async def status(self, ctx:commands.Context):
        if not self.riwayat:
            await ctx.send("Aika masih mantau status aktifnya Aika. Coba lagi nanti. 😌")
            return
        
        emoji_hijau, emoji_kuning, emoji_merah = await self.buat_emoji_bar()
        grafik_status, sub_bar, daftar_insiden = self.buat_elemen_status(
            emoji_hijau, emoji_kuning, emoji_merah
        )
        
        status_saat_ini = self.riwayat[-1]["status"]
        if status_saat_ini == "ok":
            warna = discord.Color.green()
        elif status_saat_ini == "restart":
            warna = 0xFCCA58  # Hex #fcca58
        else:
            warna = 0xDA2D43
        
        #---
        
        container = Container(accent_color=warna)
        
        container.add_item(TextDisplay(content="### 📈 Informasi Status Sistem Aika"))
        container.add_item(Separator(spacing=SeparatorSpacing.large))
        
        container.add_item(TextDisplay(content=f"# {grafik_status}"))
        container.add_item(TextDisplay(content=sub_bar))
        
        if daftar_insiden:
            container.add_item(Separator(spacing=SeparatorSpacing.large))
            insiden_teks = "\n".join(daftar_insiden)
            deskripsi_lanjutan = f"**⚠️ Catatan insiden & restart:**\n{insiden_teks}"
        else:
            deskripsi_lanjutan = (
                "Seluruh sistem berfungsi normal.\n"
                "Tidak ada gangguan yang tercatat dalam rentang waktu ini."
            )
        
        container.add_item(TextDisplay(content=deskripsi_lanjutan))
        container.add_item(Separator(spacing=SeparatorSpacing.small))
        
        if self.waktu_cek_terakhir:
            stempel_terakhir = int(self.waktu_cek_terakhir.timestamp())
            footer_tambahan = f"Terakhir: <t:{stempel_terakhir}:T>"
        else:
            footer_tambahan = "Terakhir: memuat..."
        
        container.add_item(TextDisplay(content=f"-# Diperbarui setiap 30 menit  •  {footer_tambahan}"))
        
        await ctx.send(view=LayoutView().add_item(container))


class SambungUlangOtomatis(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.pemantau_koneksi.start()
    
    def cog_unload(self):
        self.pemantau_koneksi.cancel()
    
    @tasks.loop(seconds=5)
    async def pemantau_koneksi(self):
        try:
            batas_waktu = aiohttp.ClientTimeout(total=3, connect=2)
            async with aiohttp.ClientSession(timeout=batas_waktu) as sesi, sesi.get(
                "https://discord.com/api/v10/gateway"
            ) as tanggapan:
                if tanggapan.status != 200:
                    raise aiohttp.ClientError(f"HTTP {tanggapan.status}")
            
        except Exception as e:  # noqa: BLE001
            print(f"⚠️ [Aika] WATCHDOG: Koneksi terputus ({e.__class__.__name__})", flush=True)
            
            pelacak = self.bot.get_cog("PendeteksiGangguan")
            if pelacak:
                pelacak.catat_error(f"Koneksi terputus `({e.__class__.__name__})`")
            
            if self.bot.ws and not self.bot.is_closed():
                await self.bot.ws.close(code=1001)


async def setup(bot):
    await bot.add_cog(PendeteksiGangguan(bot))
    await bot.add_cog(SambungUlangOtomatis(bot))