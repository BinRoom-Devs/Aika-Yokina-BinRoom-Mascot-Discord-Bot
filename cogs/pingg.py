import time

import aiosqlite
import discord
from discord.ext import commands


class Ping(commands.Cog):
    def __init__(self, bot:commands.Bot):
        self.bot = bot
        self.jalur_db = "data/aika.db"
    
    def warna_dinamis(self, latensi_ws:int) -> int:        
        PATOKAN = (
            (0,    (0,   255, 102)),   # ijo terang
            (100,  (46,  204, 113)),   # ijo muda
            (200,  (163, 230, 53 )),   # ijo kekuningan
            (300,  (255, 235, 59 )),   # kuning hangat
            (400,  (255, 152, 0  )),   # oren
            (500,  (255, 0,   0  )),   # merah terang (FF0000)
            (1000, (161, 3,   252)),   # ungu menyala (A103FC)
        )
        
        if latensi_ws <= PATOKAN[0][0]:
            r, g, b = PATOKAN[0][1]
            return (r << 16) + (g << 8) + b
        
        if latensi_ws >= PATOKAN[-1][0]:
            return 0xA103FC
        
        for i in range(len(PATOKAN)-1):
            p1, c1 = PATOKAN[i]
            p2, c2 = PATOKAN[i+1]
            if p1 <= latensi_ws <= p2:
                t = (latensi_ws-p1) / (p2-p1)
                r = int(c1[0]+t*(c2[0]-c1[0]))
                g = int(c1[1]+t*(c2[1]-c1[1]))
                b = int(c1[2]+t*(c2[2]-c1[2]))
                return (r << 16) + (g << 8) + b
        return 0x2E003E
    
    def warna_lingkaran(self, latensi) -> str:
        if not isinstance(latensi, (int, float)):
            return "⚫"
        
        if latensi < 250:
            return "🟢"
        elif latensi < 350:
            return "🟡"
        elif latensi < 400:
            return "🟠"
        elif latensi < 700:
            return "🔴"
        else:
            return "🟣"
    
    @commands.hybrid_command(name="ping", description="Nge-ping bot dan liat latensinya")
    async def ping(self, ctx:commands.Context):
        latensi_ws = round(self.bot.latency*1000)
        
        waktu_mulai_db = time.perf_counter()
        try:
            async with aiosqlite.connect(self.jalur_db) as db:
                await db.execute("SELECT 1")
            latensi_db = round((time.perf_counter() - waktu_mulai_db) * 1000, 2)
        except Exception:  # noqa: BLE001
            latensi_db = "Offline"
        
        waktu_mulai_api = time.perf_counter()
        pesan = await ctx.send("Pong! 🏓\nSedang menghitung latensi...")
        latensi_api = round((time.perf_counter() - waktu_mulai_api) * 1000)
        
        waktu_pesan = pesan.created_at
        waktu_ctx = ctx.interaction.created_at if ctx.interaction else ctx.message.created_at
        latensi_rtt = abs(round((waktu_pesan - waktu_ctx).total_seconds() * 1000))
        
        
        info_utama = (
            "📶 **Latensi Aika**\n"
            f"# {latensi_ws} ms"
        )
        container_1 = discord.ui.Container(accent_color=self.warna_dinamis(latensi_ws))
        container_1.add_item(discord.ui.TextDisplay(content=info_utama))
        
        info_tambahan = (
            f"-# {self.warna_lingkaran(latensi_api)} REST API: {latensi_api} ms    "
            f"{self.warna_lingkaran(latensi_rtt)} RTT: {latensi_rtt} ms    "
            f"{self.warna_lingkaran(latensi_db)} Database: {round(latensi_db)} ms"
        )
        container_2 = discord.ui.Container()
        container_2.add_item(discord.ui.TextDisplay(content=info_tambahan))
        
        await pesan.edit(content=None, view=discord.ui.LayoutView().add_item(container_1).add_item(container_2))


async def setup(bot):
    await bot.add_cog(Ping(bot))