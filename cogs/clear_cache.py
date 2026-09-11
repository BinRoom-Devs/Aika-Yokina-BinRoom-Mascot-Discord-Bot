import gc
import sys

import discord
from discord.ext import commands


class CacheManager(commands.Cog):
    def __init__(self,bot):
        self.bot = bot

    @commands.hybrid_command(name="clear_cache", aliases=["refresh", "freemem", "flush", "optimize"])
    @commands.is_owner()
    async def clear_cache(self, ctx):
        async with ctx.typing():
            item_dihapus = []

            snipe_cog = self.bot.get_cog('Snipe')
            if snipe_cog:
                if hasattr(snipe_cog, 'snipes'):
                    total_snipes = sum(len(v) for v in snipe_cog.snipes.values())
                    snipe_cog.snipes.clear()
                    item_dihapus.append(f"Data snipe: {total_snipes} pesan")
                
                try:
                    from cogs.new_snipe import CACHE_VALIDASI_CDN
                    ukuran_cache = len(CACHE_VALIDASI_CDN)
                    CACHE_VALIDASI_CDN.clear()
                    item_dihapus.append(f"Cache validasi link CDN: {ukuran_cache} link")
                except ImportError:
                    pass

            pfp_cog = self.bot.get_cog('PFP')
            if pfp_cog:
                try:
                    pfp_cog._proses_gambar_blocking.cache_clear()
                    item_dihapus.append("Cache pemrosesan foto profil")
                except AttributeError:
                    pass

            ai_cog = self.bot.get_cog('AIPersona')
            if ai_cog:
                if hasattr(ai_cog, 'req_minute'):
                    ai_cog.req_minute.clear()
                    item_dihapus.append("AI request minute rate limit")
                if hasattr(ai_cog, 'tok_minute'):
                    ai_cog.tok_minute.clear()
                    item_dihapus.append("AI token minute rate limit")
                if hasattr(ai_cog, 'req_daily'):
                    ai_cog.req_daily.clear()
                    item_dihapus.append("AI request daily rate limit")
                if hasattr(ai_cog, 'tok_daily'):
                    ai_cog.tok_daily.clear()
                    item_dihapus.append("AI token daily rate limit")            

            try:
                from cogs.cek_terminal import TAMPUNGAN_LOG
                log_size = len(TAMPUNGAN_LOG)
                TAMPUNGAN_LOG.clear()
                item_dihapus.append(f"Log buffer terminal: {log_size} baris")
            except ImportError:
                pass

            if hasattr(self.bot, '_connection') and hasattr(self.bot._connection, '_cache'):
                try:
                    ukuran_cache = len(self.bot._connection._cache)
                    self.bot._connection._cache.clear()
                    item_dihapus.append(f"Cache internal Discord: {ukuran_cache} item")
                except (AttributeError, TypeError):
                    pass
            
            try:
                if hasattr(sys, '_clear_type_caches'):
                    sys._clear_type_caches()
                    item_dihapus.append("Type cache dari Python")
            except (AttributeError, TypeError):
                pass
            
            collected = gc.collect()
            item_dihapus.append(f"Garbage collector: {collected} objek")
            
            container = discord.ui.Container(accent_color=0x77B255)
            container.add_item(discord.ui.TextDisplay(content="### 🧹✅ Aika Berhasil Di-refresh"))
            container.add_item(discord.ui.Separator(spacing=discord.SeparatorSpacing.small))
            
            summary = "\n".join(f"• {item}" for item in item_dihapus)
            container.add_item(discord.ui.TextDisplay(content=f"{summary}\n\n**Total: {len(item_dihapus)} cache dibersihkan.**"))
            
            view = discord.ui.LayoutView()
            view.add_item(container)
            await ctx.send(view=view)


async def setup(bot):
    await bot.add_cog(CacheManager(bot))