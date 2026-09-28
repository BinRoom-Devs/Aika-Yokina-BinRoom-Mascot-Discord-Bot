import math
from datetime import datetime, timedelta, timezone

import discord
from discord.ext import commands, tasks

from dashboard.ui import state


class CustomStatusCog(commands.Cog):
    WIB = timezone(timedelta(hours=7))
                     #6 desember 2026, 00.00 wib
    TGL_ANNIV = datetime(2026, 12, 1, 0, 0, 0, tzinfo=WIB)
    INTERVAL_DETIK = 90
    STATUS_DEFAULT = "Nemenin BinRoom"
    
    ANNIV_STATUS_1 = "🥳🎂🎉 Happy BinRoom 6th anniversary!"
    ANNIV_STATUS_2 = "🥳🎂🎉 HBD BinRoom yg ke-6!"
    
    def __init__(self, bot:commands.Bot):
        self.bot = bot
        self.toggle_status = True
    
    def cog_unload(self):
        self.update_status.cancel()
    
    def baca_teks_status_skrg(self) -> str:
        skrg = datetime.now(timezone.utc).astimezone(self.WIB)
        sisa_wktu = self.TGL_ANNIV - skrg
        
        if sisa_wktu.total_seconds() <= 0:
            return self.ANNIV_STATUS_1 if self.toggle_status else self.ANNIV_STATUS_2
        
        if self.toggle_status:
            hari = math.ceil(sisa_wktu.total_seconds() / 86400)
            return f"H-{hari} BinRoom anniv..."
        
        return self.STATUS_DEFAULT
    
    async def eksekusi_update(self):
        try:
            teks_status = self.baca_teks_status_skrg()
            self.toggle_status = not self.toggle_status
            
            state.bot_activity = teks_status
            
            await self.bot.change_presence(
                status=discord.Status.dnd,
                activity=discord.CustomActivity(name=state.bot_activity)
            )
        except Exception as e:  # noqa: BLE001
            state.log_event(f"[Aika] Gagal update status: {e}")
    
    @commands.Cog.listener()
    async def on_ready(self):
        await self.eksekusi_update()
        if not self.update_status.is_running():
            self.update_status.start()
    
    @tasks.loop(seconds=INTERVAL_DETIK)
    async def update_status(self):
        await self.eksekusi_update()


async def setup(bot: commands.Bot):
    await bot.add_cog(CustomStatusCog(bot))