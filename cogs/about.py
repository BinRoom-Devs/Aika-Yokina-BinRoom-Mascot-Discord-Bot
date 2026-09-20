from dataclasses import dataclass

import discord
from discord.ext import commands


@dataclass
class Saya:
    nama: str = "Aika Yokina"
    umur: str = "17 tahun"
    gender: str = "Perempuan"
    tinggi: str = "152 cm"
    berat: str = "~55 kg"
    kebangsaan: str = "Indonesia"


class About(commands.Cog):
    def __init__(self, bot:commands.Bot):
        self.bot = bot
    
    @commands.hybrid_command(name="about", description="Liat info tentang saya.")
    async def about(self, ctx: commands.Context):
        embed = discord.Embed(
            title = "Tentang Bot",
            description = "Halo, aku cuma maskot server ini yang kebetulan ditugasin ngejagain. Namaku Aika Yokina. Aku berumur 17 tahun. Salam kenal. Untuk info lebih lanjut soal diriku, bisa cek di <#1533541868653117571>.",
            color = 0xDE82CF
        )
        embed.set_thumbnail(url="https://cdn.discordapp.com/attachments/863959650448703538/1540201066455371888/bunga.png?ex=6a891785&is=6a87c605&hm=69d799fb0347fd7461acc9e4aeaaa32563dbaf31a05cc239f6ae10301e6dba47&")
        embed.set_image(url="https://cdn.discordapp.com/attachments/863959650448703538/1541536432685060196/latihan_affinity.png?ex=6a8f44ad&is=6a8df32d&hm=cfbc261b086028328945ec3289152628efcc8a18a229b2897f903cecdd3f757d&")
            
        embed.set_author(icon_url=str(self.bot.user.display_avatar.url), name=str(self.bot.user))
            
        embed.add_field(
            name = "Nama",
            value = Saya().nama,
            inline = True
        )
        embed.add_field(
            name = "Umur",
            value = Saya().umur,
            inline = True
        )
        embed.add_field(
            name = "Jenis kelamin",
            value = Saya().gender,
            inline = True
        )
        embed.add_field(
            name = "Tinggi",
            value = Saya().tinggi,
            inline = True
        )
        embed.add_field(
            name = "Berat",
            value = Saya().berat,
            inline = True
        )
        embed.add_field(
            name = "Kebangsaan",
            value = Saya().kebangsaan,
            inline = True
        )
            
        embed.set_footer(text="Untuk info statisik bot, cek ak!info")
        
        await ctx.send(embed=embed)
        print("[Aika] Command about dieksekusi")


async def setup(bot:commands.Bot):
    await bot.add_cog(About(bot))