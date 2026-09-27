"""Berisi command yang berfungsi untuk mengecek kapasitas memori chat user."""

import discord
from discord.ext import commands


class CekIngatan(commands.Cog):
    def __init__(self, bot:commands.Bot):
        self.bot = bot
    
    def get_ai_cog(self):
        cog = self.bot.get_cog("AIPersona")
        if not cog:
            print("[Aika] Gagal menemukan instance cog 'AIPersona'.")
        return cog
    
    @commands.hybrid_command(
        name="status-memori-ai",
        description="Ngecek kapasitas memorimu untuk percakapan Aika.",
        aliases=["status-memori", "memory-status", "cek-memori"]
    )
    async def memory_status(self, ctx:commands.Context):
        ai_cog = self.get_ai_cog()
        if not ai_cog:
            pesan = "❌ Eror: perintah ini belum terhubung dengan modul chat AI."
            if ctx.interaction:
                await ctx.interaction.response.send_message(pesan, ephemeral=True)
            else:
                await ctx.send(pesan)
            return
        
        if ctx.author.id not in ai_cog.user_chats:
            msg = "Mau cek apa? Aika aja belum tau apapun soalmu. 😒"
            if ctx.interaction:
                await ctx.interaction.response.send_message(msg, ephemeral=True)
            else:
                await ctx.send(msg, delete_after=12)
            return
        
        chat = ai_cog.user_chats[ctx.author.id]
        pesan_chat = [message for message in chat if message["role"] != "system"]
        jumlah_pesan = len(pesan_chat)
        
        kapasitas_max = ai_cog.max_memory_messages
        persentase = min(int((jumlah_pesan / kapasitas_max) * 100), 100)
        kotak_terisi = int(persentase / 10)
        bar = ("█" * kotak_terisi + "░" * (10 - kotak_terisi))
        
        if persentase < 25:
            flavor = "Baru kenal dikit... ingatan masih ringan."
        elif persentase >= 50:
            flavor = "Kita mulai kenal dekat nih."
        elif persentase < 75:
            flavor = "Udah lumayan sering ngobrol nih."
        else:
            flavor = "Kita udah kenal banyak..."
        
        embed = discord.Embed(
            title=f"Status Ingatan Aika ({ctx.author.display_name})",
            description=f"**Kapasitas:** [{bar}] `{persentase}%`\n**Pesan tersimpan:** `{jumlah_pesan}/{kapasitas_max}` pesan\n\n",
            color=0xD675C1
        )
        embed.set_footer(
            text="Pesan paling lama akan dihapus otomatis saat penuh.\nMau hapus semua sekalian? Gunakan ak!reset-memori",
            icon_url="https://cdn.discordapp.com/attachments/863959650448703538/1540201066455371888/bunga.png?ex=6a8b11c5&is=6a89c045&hm=2f7837e9e91cf914975584cb8ba5f001f80ea54d36c86e643547b1f23a111b26&"
        )
        embed.set_thumbnail(url=ctx.author.display_avatar.url)
        
        if ctx.interaction:
            await ctx.interaction.response.send_message(content=flavor, embed=embed, ephemeral=True)
        else:
            await ctx.send(content=flavor, embed=embed)


async def setup(bot:commands.Bot):
    await bot.add_cog(CekIngatan(bot))