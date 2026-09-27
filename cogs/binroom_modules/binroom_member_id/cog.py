import asyncio
import random
from datetime import datetime, timezone

import aiohttp
import discord
from discord import app_commands
from discord.ext import commands

import database

from ._card_generator import BULAN_BHS_INDO, bikin_kartu_member

ID_ROLE_OWNER_BINROOM = 904996218491506759  # @Tuan Rumah 
ID_ROLE_UTK_ADMIN = 904996395260477450      # @Satpam


class BinroomID(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.session = aiohttp.ClientSession()
    
    def cog_unload(self):
        asyncio.create_task(self.session.close())
    
    @commands.Cog.listener()
    async def on_member_remove(self, member: discord.Member):
        await database.delete_binroom_member(member.id)
    
    def _tentukan_tipe_anggota(self, member: discord.Member) -> str:
        if member.guild and member.id == member.guild.owner_id:
            return "Owner"
        
        id_role = [role.id for role in member.roles]
        
        if ID_ROLE_OWNER_BINROOM in id_role:
            return "Owner"
        
        if ID_ROLE_UTK_ADMIN in id_role:
            return "Admin"
        
        return "Member"
    
    def _hitung_urutan_gabung(self, member: discord.Member) -> int:
        anggota_terurut = sorted(
            [m for m in member.guild.members if m.joined_at],
            key=lambda m: m.joined_at
        )
        try:
            return anggota_terurut.index(member) + 1
        except ValueError:
            return len(anggota_terurut)
    
    def _format_tanggal_indonesia(self, dt: datetime) -> str:
        hari = dt.day
        bulan = BULAN_BHS_INDO.get(dt.month, "")
        tahun = dt.year
        return f"{hari} {bulan} {tahun}"
    
    @commands.cooldown(1, 5, commands.BucketType.user)
    @commands.hybrid_group(
        name="membership",
        description="Menampilkan kartu keanggotaan BinRoom kamu.",
        invoke_without_command=True
    )
    @app_commands.describe(member="Anggota yang ingin dilihat kartunya (opsional).")
    async def membership(self, ctx: commands.Context, member: discord.Member = None):
        target = member or ctx.author
        
        if not isinstance(target, discord.Member):
            await ctx.send("❌ Orangnya gaada di BinRoom!", ephemeral=True)
            return
        
        if target.bot:
            await ctx.send("💢 Kartu keanggotaan hanya tersedia untuk member, bukan bot!", ephemeral=True)
            return
        
        await ctx.defer()
        
        data_db = await database.get_binroom_member(target.id)
        nomor_gabung = data_db["join_number"] if data_db else self._hitung_urutan_gabung(target)
        nama_tampilan = data_db["custom_name"] if data_db and data_db["custom_name"] else target.display_name
        
        if not data_db:
            await database.save_binroom_join_number(target.id, nomor_gabung)
        
        url_avatar = target.display_avatar.with_format("png").with_size(256).url
        async with self.session.get(url_avatar) as resp:
            if resp.status != 200:
                await ctx.send("😵 Gagal membaca foto profil, coba lagi nanti...")
                return
            byte_avatar = await resp.read()
        
        teks_tanggal_gabung = self._format_tanggal_indonesia(target.joined_at or datetime.now(timezone.utc))
        tipe_anggota = self._tentukan_tipe_anggota(target)
        
        buffer_kartu = await asyncio.to_thread(
            bikin_kartu_member,
            gambar_polosan="media/binroom_id/binroom_id_template.png",
            ukuran_byte_pfp=byte_avatar,
            user_id=target.id,
            display_name=nama_tampilan,
            tanggal_join=teks_tanggal_gabung,
            nomor_member=nomor_gabung,
            jenis_member=tipe_anggota
        )
        
        berkas = discord.File(fp=buffer_kartu, filename=f"membership_{target.id}.png")
        await ctx.send(file=berkas)
        
        if random.randint(1, 7) == 1:
            await ctx.send(content=(
                "-# Kartu ini **bisa kamu cetak**, karena ukurannya __8.56 x 5.4 cm__ __300 dpi__, sudah sesuai ukuran kartu pada umumnya.\n"
                "Cocok buat kamu taruh di dompet dan lain-lain. 😉"
            ))
    
    @membership.command(
        name="custom-name", 
        aliases=["customname", "nama-kustom", "nama-sendiri"],
        description="Mengubah nama kustom yang ditampilkan pada kartu keanggotaan."
    )
    @app_commands.describe(nama_baru="Nama baru (maksimal 32 karakter).")
    async def custom_name(self, ctx:commands.Context, *, nama_baru:str):
        if len(nama_baru) > 32:
            await ctx.send("💢 Nama kustom tidak boleh lebih dari 32 huruf!", ephemeral=True)
            return
        
        await ctx.defer()
        
        urutan_gabung = self._hitung_urutan_gabung(ctx.author)
        
        await database.save_binroom_custom_name(ctx.author.id, nama_baru, urutan_gabung)
        
        await ctx.send(f"Nama pada kartu berhasil diperbarui menjadi: **{nama_baru}**. Membuat ulang kartu...")
        
        await self.membership(ctx, member=ctx.author)
        
        if random.randint(1, 7) == 1:
            await ctx.send(content=(
                "-# Kartu ini **bisa kamu cetak**, karena ukurannya __8.56 x 5.4 cm__ __300 dpi__, sudah sesuai ukuran kartu pada umumnya.\n"
                "Cocok buat kamu taruh di dompet dan lain-lain. 😉"
            ))
    
    @membership.command(
        name="reset-name",
        aliases=["resetname", "reset"],
        description="Mereset nama kustom pada kartu keanggotaan kembali ke nama tampilan Discord."
    )
    async def reset_name(self, ctx:commands.Context):
        await ctx.defer()
        
        data_db = await database.get_binroom_member(ctx.author.id)
        
        if not data_db or not data_db.get("custom_name"):
            await ctx.send("ℹ️ Kamu belum pernah mengatur nama kustom pada kartu keanggotaan.", ephemeral=True)
            return
        
        await database.reset_binroom_custom_name(ctx.author.id)
        
        await ctx.send("✅ Nama kustom berhasil dihapus. Kartu kamu dikembalikan ke nama tampilan Discord semula. Membuat ulang kartu...")
        
        await self.membership(ctx, member=ctx.author)
    
    @membership.error
    async def membership_error(self, ctx:commands.Context, error:commands.CommandError):
        
        if isinstance(error, (commands.MemberNotFound, commands.UserNotFound)):
            await ctx.send("❌ Orangnya gaada di BinRoom!", ephemeral=True)
            
        elif isinstance(error, commands.CommandOnCooldown):
            await ctx.send(f"⏳ Sabar! Tunggu {error.retry_after:.1f} detik lagi sebelum gunain command ini.", ephemeral=True)

async def setup(bot):
    await bot.add_cog(BinroomID(bot))