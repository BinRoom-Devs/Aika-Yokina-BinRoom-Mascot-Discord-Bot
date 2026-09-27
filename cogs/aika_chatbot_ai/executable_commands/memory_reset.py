"""Berisi command yang berfungsi untuk menghapus memori percakapan user."""

import time

import discord
from discord.ext import commands

from .._views import HapusIngatan


class ResetMemori(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
    
    def get_ai_cog(self):
        cog = self.bot.get_cog("AIPersona")
        if not cog:
            print("[Aika] Gagal menemukan instance cog 'AIPersona'.")
        return cog
    
    @commands.hybrid_command(
        name="reset-memori",
        description="Ngehapus ingatan percakapan Aika denganmu.",
        aliases=["reset", "hapus-ingatan", "reset-memory", "memory-reset"]
    )
    async def reset_memori(self, ctx: commands.Context):
        ai_cog = self.get_ai_cog()
        if not ai_cog:
            await ctx.send("❌ Eror: perintah ini belum terhubung dengan modul chat AI.", ephemeral=True)
            return
        
        if ctx.author.id not in ai_cog.user_chats:
            await ctx.send("Mau reset apa? Aika aja belum tau apapun soalmu. 🧐", ephemeral=True, delete_after=12)
            return
        
        timeout_timestamp = int(time.time() + 30)
        embed = discord.Embed(
            title="⚠️ Konfirmasi Reset Memori",
            description=f"Kamu yakin ingin menghapus semua ingatan percakapan Aika denganmu? Tindakan ini gabisa dibalikin.\n\n-# Batal otomatis <t:{timeout_timestamp}:R>",
            color=discord.Color.orange()
        )
        
        view = HapusIngatan(cog=ai_cog, user_id=ctx.author.id)
        
        if ctx.interaction:
            await ctx.interaction.response.send_message(embed=embed, view=view, ephemeral=True)
            view.message = await ctx.interaction.original_response()
        else:
            view.message = await ctx.send(embed=embed, view=view)


async def setup(bot: commands.Bot):
    await bot.add_cog(ResetMemori(bot))