import datetime

import discord
from discord.ext import commands


class Honeypot(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.ID_CHANNEL_RANJAU = 1498144198577356831

    @commands.Cog.listener()
    async def on_message(self, pesan:discord.Message):
        if pesan.author.bot or pesan.channel.id != self.ID_CHANNEL_RANJAU: return
        if not pesan.guild or not isinstance(pesan.author, discord.Member): return

        #langsung hapus pesan phishing
        try:
            await pesan.delete()
        except discord.HTTPException:
            pass

        #langsung gas timeout 28 hari
        try:
            timeout_duration = datetime.timedelta(days=28)
            await pesan.author.timeout(
                timeout_duration, 
                reason="Anda masuk perangkap honeypot / channel terlarang yang tujuan aslinya untuk menangkap pesan phishing otomatis. Anda langsung dikarantina dan di-timeout dan akan di-review nanti."
            )

            print(f"[Aika] Honeypot: {pesan.author} ({pesan.author.id}) tertangkap!")

            embed = discord.Embed(
                title="Tertangkap di honeypot! 🛑",
                description="Tinjau apabila ini ketidaksengajaan atau konfirmasi dengan pemilik akun jika akses berhasil di-recover.",
                timestamp=datetime.datetime.now(datetime.timezone.utc),
                color=0xFF0000
            )
            embed.set_thumbnail(url=f"{pesan.author.display_avatar.url}")
            embed.add_field(name="User", value=f"{pesan.author.mention}", inline=True)
            embed.add_field(name="ID", value=f"{pesan.author.id}", inline=True)

            channel_log = self.bot.get_channel(932191307789656064)
            await channel_log.send(embed=embed)

        except discord.Forbidden:
            print(f"[Aika] Honeypot: gagal menangkap {pesan.author} (Aika gapunya izin)")
        except discord.HTTPException as e:
            print(f"[Aika] Honeypot: HTTP eror {pesan.author}: {e}")

async def setup(bot):
    await bot.add_cog(Honeypot(bot))