import re

import aiohttp
import discord
from bs4 import BeautifulSoup
from discord.ext import commands


class KBBIPaginator(discord.ui.LayoutView):
    def __init__(self, daftar_entri: list[str], tautan_judul: str, warna: int, fungsi_wadah):
        super().__init__()
        self.daftar_entri = daftar_entri
        self.tautan_judul = tautan_judul
        self.warna = warna
        self.fungsi_wadah = fungsi_wadah
        self.entri_per_halaman = 3
        self.halaman_saat_ini = 0
        self.total_halaman = (len(daftar_entri) - 1) // self.entri_per_halaman + 1

        self.perbarui_tampilan()

    def ambil_entri_halaman(self) -> list[str]:
        awal = self.halaman_saat_ini * self.entri_per_halaman
        akhir = awal + self.entri_per_halaman
        return self.daftar_entri[awal:akhir]

    def perbarui_tampilan(self):
        self.clear_items()
        entri_halaman = self.ambil_entri_halaman()
        teks_bodi = "\n".join(entri_halaman)
        catatan_bawah = "-# Sumber: kbbi.web.id"
        
        wadah = self.fungsi_wadah(
            warna=self.warna, 
            judul=self.tautan_judul, 
            bodi=teks_bodi, 
            catatan_bawah=catatan_bawah
        )
        
        self.add_item(wadah)

        if self.total_halaman > 1:
            tombol_sebelumnya = discord.ui.Button(
                emoji="◀", 
                style=discord.ButtonStyle.secondary, 
                disabled=(self.halaman_saat_ini == 0)
            )
            tombol_indikator = discord.ui.Button(
                label=f"{self.halaman_saat_ini + 1}/{self.total_halaman}", 
                style=discord.ButtonStyle.secondary, 
                disabled=True
            )
            tombol_selanjutnya = discord.ui.Button(
                emoji="▶", 
                style=discord.ButtonStyle.secondary, 
                disabled=(self.halaman_saat_ini == self.total_halaman - 1)
            )

            tombol_sebelumnya.callback = self.halaman_sebelumnya
            tombol_selanjutnya.callback = self.halaman_selanjutnya

            baris_tombol = discord.ui.ActionRow(tombol_sebelumnya, tombol_indikator, tombol_selanjutnya)
            self.add_item(baris_tombol)

    async def halaman_sebelumnya(self, interaksi: discord.Interaction):
        if self.halaman_saat_ini > 0:
            self.halaman_saat_ini -= 1
            self.perbarui_tampilan()
            await interaksi.response.edit_message(view=self)

    async def halaman_selanjutnya(self, interaksi: discord.Interaction):
        if self.halaman_saat_ini < self.total_halaman - 1:
            self.halaman_saat_ini += 1
            self.perbarui_tampilan()
            await interaksi.response.edit_message(view=self)


class KBBI(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.tajuk_permintaan = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}

    def buat_wadah(self, warna: int, judul: str, bodi: str, catatan_bawah: str | None = None):
        wadah = discord.ui.Container(accent_color=warna)
        wadah.add_item(discord.ui.TextDisplay(content=judul))
        wadah.add_item(discord.ui.Separator(spacing=discord.SeparatorSpacing.small))
        wadah.add_item(discord.ui.TextDisplay(content=bodi))
        
        if catatan_bawah:
            wadah.add_item(discord.ui.Separator(spacing=discord.SeparatorSpacing.small))
            wadah.add_item(discord.ui.TextDisplay(content=catatan_bawah))
        
        return wadah

    async def _baca_dan_ekstrak(self, kata: str) -> dict:
        kata_bersih = kata.strip().lower()
        tautan = f"https://kbbi.web.id/{kata_bersih}"
        batas_waktu = aiohttp.ClientTimeout(total=10)

        try:
            async with aiohttp.ClientSession(timeout=batas_waktu) as sesi, sesi.get(tautan, headers=self.tajuk_permintaan) as respon:
                if respon.status != 200:
                    return {"berhasil": False, "pesan": f"Kesalahan HTTP {respon.status} dari server KBBI."}
                html = await respon.text()
        except Exception as e:  # noqa: BLE001
            return {"berhasil": False, "pesan": f"Gagal terhubung ke KBBI: {e}"}

        sup = BeautifulSoup(html, "html.parser")
        div_d1 = sup.find("div", id="d1")

        if not div_d1 or "tidak ditemukan" in div_d1.get_text().lower():
            return {"berhasil": False, "pesan": f"Kata `{kata_bersih}` tidak ditemukan dalam KBBI."}

        # 1. Transform word classes (<font color="red">) and sub-labels (<i>ki</i>) into markdown
        for font_tag in div_d1.find_all("font", color="red"):
            teks_kelas = font_tag.get_text(strip=True)
            if teks_kelas:
                font_tag.replace_with(f" *({teks_kelas})* ")

        # 2. Convert remaining <i> tags (like ki, pb, etc.) safely into italics before text extraction
        for i_tag in div_d1.find_all("i"):
            teks_i = i_tag.get_text(strip=True)
            if teks_i in ["ki", "pb", "ukp", "kp"]:
                i_tag.replace_with(f" *({teks_i})* ")
            else:
                # Target example sentences inside <i> tags specifically without dropping the parent node
                i_tag.replace_with(f" {teks_i} ")

        # 3. Mark sub-words (--) explicitly before flattening
        for b_tag in div_d1.find_all("b"):
            teks_b = b_tag.get_text(strip=True)
            if teks_b.startswith("--") or teks_b.startswith("~"):
                sub_kata = teks_b.strip()
                b_tag.replace_with(f" __SUBWORD_{sub_kata}__ ")

        html_mentah = div_d1.decode_contents()

        # Split block purely on primary entry headers: <b>word</b>
        bagian = re.split(r'(<b>[^<]+</b>)', html_mentah)
        daftar_entri = []

        for idx in range(1, len(bagian), 2):
            html_kepala = bagian[idx]
            html_badan = bagian[idx + 1] if idx + 1 < len(bagian) else ""

            nama_kata = BeautifulSoup(html_kepala, "html.parser").get_text().strip()

            if nama_kata.isdigit():
                continue

            sup_badan = BeautifulSoup(html_badan, "html.parser")
            teks_badan = sup_badan.get_text(separator=" ", strip=True)

            # Extract pronunciation /ha·pus/
            pelafalan = ""
            cocok_pelafalan = re.search(r'/[^/]+/', teks_badan)
            if cocok_pelafalan:
                pelafalan_teks = cocok_pelafalan.group(0)
                pelafalan = f" *`{pelafalan_teks}`*"
                teks_badan = teks_badan.replace(pelafalan_teks, "", 1)
            elif "·" in nama_kata:
                pelafalan = f" *`/{nama_kata}/`*"

            kata_polos = nama_kata.replace("·", "")

            # Strip example sentences following colons (:) while retaining main definition text
            teks_badan = re.sub(r':\s*[^;]+(?=;|$)', '', teks_badan)
            teks_badan = re.sub(r'[\r\n\t]+', ' ', teks_badan)
            teks_badan = re.sub(r'\s+', ' ', teks_badan).strip()

            # Split primary definitions (1, 2, 3...) and compound entries
            items = re.split(r'(\s*\d+\s+|(?=__SUBWORD_))', teks_badan)
            baris_definisi = []
            kelas_terakhir = ""

            for item in items:
                d = item.strip(" :;,")
                if not d or d.isdigit() or d.startswith("-->"):
                    continue

                # Sub-word / idiom line -> blockquote
                if "__SUBWORD_" in d:
                    d_clean = re.sub(r'__SUBWORD_([^_]+)__', r'**\1** ', d).strip()
                    baris_definisi.append(f"> \\- {d_clean}")
                    continue

                # Main definition line
                match_kelas = re.search(r'\*\([^)]+\)\*', d)
                if match_kelas:
                    kelas_terakhir = match_kelas.group(0)
                elif kelas_terakhir and not d.startswith("*("):
                    d = f"{kelas_terakhir} {d}"

                baris_definisi.append(f"\\- {d}")

            if baris_definisi:
                header_line = f"## - {kata_polos}{pelafalan}"
                block = header_line + "\n" + "\n".join(baris_definisi)
                daftar_entri.append(block)

        return {
            "berhasil": True,
            "kata": kata_bersih,
            "entri": daftar_entri,
            "tautan": tautan
        }

    @commands.hybrid_command(name="kbbi", description="Mencari definisi kata dari Kamus Besar Bahasa Indonesia (KBBI)")
    async def kbbi(self, ctx: commands.Context, *, kata: str):
        await ctx.defer()
        
        hasil = await self._baca_dan_ekstrak(kata)
        
        if not hasil["berhasil"]:
            judul_salah = f"# ❌ {kata.capitalize()}"
            wadah_salah = discord.ui.Container(accent_color=discord.Color.red())
            wadah_salah.add_item(discord.ui.TextDisplay(content=judul_salah))
            wadah_salah.add_item(discord.ui.Separator(spacing=discord.SeparatorSpacing.small))
            wadah_salah.add_item(discord.ui.TextDisplay(content=hasil["pesan"]))
            
            tampilan = discord.ui.LayoutView().add_item(wadah_salah)
            await ctx.send(view=tampilan)
            return

        tautan_judul = f"# [{hasil['kata'].lower()}]({hasil['tautan']})"
        warna = 0xD675C1

        paginator = KBBIPaginator(
            daftar_entri=hasil["entri"], 
            tautan_judul=tautan_judul, 
            warna=warna, 
            fungsi_wadah=self.buat_wadah
        )

        await ctx.send(view=paginator)


async def setup(bot: commands.Bot):
    await bot.add_cog(KBBI(bot))