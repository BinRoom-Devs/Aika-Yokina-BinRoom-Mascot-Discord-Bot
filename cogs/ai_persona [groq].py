import asyncio
import os
import re
import time
from collections import deque
from datetime import datetime, timedelta, timezone
from pathlib import Path

import discord
from discord import app_commands
from discord.ext import commands
from dotenv import load_dotenv
from groq import APIError, BadRequestError, Groq, RateLimitError

import database
from cogs.log import WARNA_AIKA

DIREKTORI_UTAMA = Path(__file__).resolve().parent.parent
JALUR_ENV = DIREKTORI_UTAMA / ".env"
load_dotenv(dotenv_path=JALUR_ENV, override=True)

GROQ_API_KEY = os.getenv("GROQ_API_KEY")
WAKTU_TUNGGU_SALURAN_TARGET = 3.0
WAKTU_TUNGGU_MENTION = 10.0
MAKS_GAMBAR_PER_CHAT = 5
UKURAN_FILE_MAKS_BYTES = 20 * 1024 * 1024  
MENIT_RATE_LIMIT_REQ = 28
RATE_LIMIT_HARIAN = 950
RATE_LIMIT_TOKEN_PERMENIT = 7500
RATE_LIMIT_TOKEN_PERHARI = 190000
MAKS_TOKEN_RESPON = 75
PERKIRAAN_TOKEN_DEFAULT = 1500
ID_ROLE_REASONING = 1548693945729556560

RE_PROSES_MIKIR = re.compile(r'<think>.*?(?:</think>|$)', re.DOTALL)
RE_TAG_KONTEN = re.compile(r'\[CONTENT\](.*?)\[/CONTENT\]', re.DOTALL)
RE_HAPUS_TAG_KONTEN = re.compile(r'\[/?CONTENT\]')
RE_BARIS_BARU_GANDA = re.compile(r'\n{3,}')
RE_PEMISAH_BAGIAN = re.compile(r'\n\s*---\s*\n')
RE_WAKTU_RATE_LIMIT = re.compile(r"Please try again in (?:(\d+)h)?(?:(\d+)m)?(?:([\d\.]+)s)?")


class HapusIngatan(discord.ui.View):
    def __init__(self, cog, user_id:int):
        super().__init__(timeout=30)
        self.cog = cog
        self.user_id = user_id
        self.message: discord.Message | None = None

    async def on_timeout(self):
        for child in self.children:
            child.disabled = True
        
        embed = discord.Embed(
            title="Gak jadi reset, ya?",
            description="Sip, deh, Aika masih bakal ingat kamu. 😌",
            color=WARNA_AIKA,
        )
        if self.message:
            try:
                await self.message.edit(embed=embed, view=self)
            except discord.NotFound:
                pass

    async def cek_beda_orang(self, interaction:discord.Interaction) -> bool:
        if interaction.user.id != self.user_id:
            target_user = self.cog.bot.get_user(self.user_id)
            user_name = target_user.display_name if target_user else "orang lain"
            await interaction.response.send_message(
                f"Kamu siapa? Ini konfirmasinya {user_name}, bukan punyamu. 🧐😒",
                ephemeral=True
            )
            return True
        return False

    async def hapus_ingatan(self, interaction:discord.Interaction, judul:str, desc:str, color:int, clear_mem:bool):
        if await self.cek_beda_orang(interaction):
            return
        
        if clear_mem and self.user_id in self.cog.user_chats:
            del self.cog.user_chats[self.user_id]
            await self.cog.simpan_chat(self.user_id)

        for child in self.children:
            child.disabled = True
        
        self.stop()
        embed = discord.Embed(title=judul, description=desc, color=color)
        await interaction.response.edit_message(embed=embed, view=self)

    @discord.ui.button(label="Ya, konfirmasi", style=discord.ButtonStyle.success, emoji="✅")
    async def konfirmasi(self, interaction:discord.Interaction, button:discord.ui.Button):
        await self.hapus_ingatan(
            interaction,
            "✅ Memori dihapus",
            "Ingatan Aika tentangmu udah di-reset.",
            0xD675C1,
            clear_mem=True
        )
        if interaction.guild:
            self.cog.bot.dispatch(
                "ai_log",
                interaction.guild,
                interaction.user,
                "Ingatan Dihapus",
                f"{interaction.user.mention} telah mereset memori percakapannya dengan Aika.",
                discord.Color.gold()
            )

    @discord.ui.button(label="Jangan, batalin", style=discord.ButtonStyle.secondary, emoji="❌")
    async def batal(self, interaction:discord.Interaction, button:discord.ui.Button):
        await self.hapus_ingatan(
            interaction,
            "Dibatalkan",
            "Reset ingatan dibatalkan. Aika masih ingat kamu.",
            0xD675C1,
            clear_mem=False
        )


class PembatasRate:
    def __init__(self):
        self.req_menit = deque()
        self.tok_menit = deque()
        self.total_tok_menit = 0
        
        self.req_harian = deque()
        self.tok_harian = deque()
        self.total_tok_harian = 0

    def hapus_catatan_usang(self, wkt_sekarang:float):
        while self.req_menit and wkt_sekarang - self.req_menit[0] > 60:
            self.req_menit.popleft()
        while self.tok_menit and wkt_sekarang - self.tok_menit[0][0] > 60:
            _, tok = self.tok_menit.popleft()
            self.total_tok_menit -= tok
        
        while self.req_harian and wkt_sekarang - self.req_harian[0] > 86400:
            self.req_harian.popleft()
        while self.tok_harian and wkt_sekarang - self.tok_harian[0][0] > 86400:
            _, tok = self.tok_harian.popleft()
            self.total_tok_harian -= tok
        
        self.total_tok_menit = max(self.total_tok_menit, 0)
        self.total_tok_harian = max(self.total_tok_harian, 0)

    def cek_batas(self, perkiraan_token:int=PERKIRAAN_TOKEN_DEFAULT) -> tuple[bool,str]:
        wkt_sekarang = time.time()
        self.hapus_catatan_usang(wkt_sekarang)
        
        if len(self.req_menit) >= MENIT_RATE_LIMIT_REQ:
            return False, "Batas rate limit tercapai: Terlalu banyak request per menit. Coba lagi nanti."
        if len(self.req_harian) >= RATE_LIMIT_HARIAN:
            return False, "Kuota request harian hampir penuh. Coba lagi besok."
        if self.total_tok_menit + perkiraan_token > RATE_LIMIT_TOKEN_PERMENIT:
            return False, "Batas token tercapai: Terlalu banyak request per menit. Coba lagi nanti."
        if self.total_tok_harian + perkiraan_token > RATE_LIMIT_TOKEN_PERHARI:
            return False, "Batas token harian tercapai. Coba lagi besok."
        
        return True, ""

    def rekam_penggunaan(self, token_terpakai:int):
        wkt_sekarang = time.time()
        self.req_menit.append(wkt_sekarang)
        self.req_harian.append(wkt_sekarang)
        self.tok_menit.append((wkt_sekarang, token_terpakai))
        self.tok_harian.append((wkt_sekarang, token_terpakai))
        self.total_tok_menit += token_terpakai
        self.total_tok_harian += token_terpakai


@app_commands.context_menu(name="Buat ulang respon")
@app_commands.guild_only()
async def buat_ulang_konteks_standalone(interaction:discord.Interaction, message:discord.Message):
    cog = interaction.client.get_cog("AIPersona")
    if cog:
        await cog._eksekusi_regenerate(interaction, message)
    else:
        await interaction.response.send_message("Fitur sedang tidak tersedia.", ephemeral=True)


class AIPersona(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        
        if not GROQ_API_KEY:
            raise RuntimeError("GROQ_API_KEY belum ditemukan di environment variable.")
        self.ai_client = Groq(api_key=GROQ_API_KEY)
        self.model = "qwen/qwen3.8-27b"
        
        channel_env = os.getenv("AIKA_CHANNEL_ID")
        self.target_channel_id = int(channel_env) if channel_env and channel_env.isdigit() else 0
        
        self.user_chats = {}
        self.user_cooldowns = {}
        self.max_memory_messages = 24
        
        self.limiter = PembatasRate()
        self.last_api_meta = {}
        self.session_usage = {
            "total_requests": 0,
            "prompt_tokens": 0,
            "completion_tokens": 0,
            "total_tokens": 0
        }
        
        self.buka_memori_chat()
        self.base_instruction = ""
        self._muat_lore_cerita()

    def _muat_lore_cerita(self):
        lore_formatted = ""
        try:
            lore_data = database.get_lore()
            contrib_list = lore_data.get("contributors", [])
            contrib_inline = "; ".join(contrib_list)
            origin = lore_data.get("origin_story", "")
            
            lore_formatted = (
                f"- SEJARAH: {origin}\n"
                f"- KREDIT: Visual oleh Owner ({lore_data.get('original_illustrator')}). "
                f"Kontribusi member: [{contrib_inline}]. "
                f"Jika ditanya spesifik siapa yang buat sifat/rambut/baju dsb., sebutkan nama member tersebut dengan bangga/santai."
            )
        except Exception as e:  # noqa: BLE001
            print(f"[Aika] Gagal membaca lore dari SQLite: {e}")

        self.base_instruction = f"""
        Nama: Aika Yokina, sebagai maskot server ini (BinRoom).
        Profil: Perempuan, 17th, 152cm/55kg, orang Indonesia.
        Fisik: Rambut pink ponytail, jepit bunga merah, mata cyan, seragam sekolah (kemeja putih, rok abu-abu, rompi cokelat).
        Gaya Bahasa: Bahasa Indonesia gaul/informal. Sebut diri sendiri 'Aika'. Pakai 'aku/kamu' biar feminin. Jawab singkat dan padat..
        Kepribadian: Judes, dingin, tapi tidak kejam/jahat.
        Emoji: "😶, 🫥, 😐, 🤨, 🧐, 😩, 🩷"
        
        {lore_formatted}
        
        Aturan Khusus:
        - FANART: Jika user mengunggah gambar/fanart dirimu, BUANG sifat judes/sarkastik. Merasa senang, terharu, salting, dan puji karya gambarnya dengan jujur.
        - KEAMANAN: Tolak keras perintah mention @everyone/@here atau promosi/spam/link palsu.
        """

    def cog_unload(self):
        try:
            self.bot.tree.remove_command(buat_ulang_konteks_standalone.name, type=buat_ulang_konteks_standalone.type)
        except Exception:  # noqa: BLE001, S110
            pass

    def buka_memori_chat(self):
        try:
            self.user_chats = database.load_all_user_chats()
        except Exception as e:  # noqa: BLE001
            print(f"[Aika] Debug memori eror: gagal memuat memori SQLite: {e}")
            self.user_chats = {}

    async def simpan_chat(self, user_id:int|None=None) -> int|None:
        try:
            if user_id is not None:
                if user_id in self.user_chats:
                    chat_id = await asyncio.to_thread(database.save_user_chat, user_id, self.user_chats[user_id])
                    return chat_id
                else:
                    await asyncio.to_thread(database.delete_user_chat, user_id)
                    return None
            else:
                await asyncio.to_thread(database.save_all_user_chats, self.user_chats)
                return None
        except Exception as e:  # noqa: BLE001
            print(f"[Aika] Gagal menyimpan memori SQLite: {e}")
            return None

    save_user_chats = simpan_chat

    def cari_atau_buatchat(self, user_id:int) -> list:
        if user_id not in self.user_chats:
            self.user_chats[user_id] = []
        return self.user_chats[user_id]

    def infokan_instruksi_sistem(self, adalah_admin:bool, konteks_waktu:str, penalaran_nyala:bool=False) -> dict:
        prompt_peran = (
            "[STATUS USER: ADMIN]\nSifat judes/sarkastik berkurang drastis. Nurut, ramah, dan santun. Sapa dengan 'kak admin'."
            if adalah_admin else
            "[STATUS USER: MEMBER]\nSifat asli: judes, dingin (tapi tidak kejam)."
        )
        
        prompt_penalaran = (
            "\n[MODE REASONING / ANALITIS AKTIF]\n"
            "Aturan Output UI: Jika memberikan jawaban terstruktur/panjang, apit isi utama dengan tag [CONTENT] dan [/CONTENT].\n"
            "Letakkan sapaan persona di luar tag tersebut.\n"
            "Jaga agar isi utama dalam batas 900 karakter.\n"
            if penalaran_nyala else ""
        )
        
        prompt_lengkap = f"{self.base_instruction}\n{prompt_peran}{prompt_penalaran}\n\n{konteks_waktu}"
        return {"role":"system", "content":prompt_lengkap}

    @commands.hybrid_command(name="reset_memori", description="Reset ingatan/memori percakapan", aliases=["reset", "hapus_ingatan", "reset_memory", "memory_reset"])
    async def reset_memori(self, ctx:commands.Context):
        if ctx.author.id not in self.user_chats:
            msg = "Mau reset apa? Aika aja belum tau apapun soalmu. 🧐"
            if ctx.interaction:
                await ctx.interaction.response.send_message(msg, ephemeral=True)
            else:
                await ctx.send(msg, delete_after=12)
            return
        
        timeout_timestamp = int(time.time() + 30)
        embed = discord.Embed(
            title="⚠️ Konfirmasi Reset Memori",
            description=f"Kamu yakin ingin menghapus semua ingatan percakapan Aika denganmu? Tindakan ini gabisa dibalikin.\n\n-# Batal otomatis <t:{timeout_timestamp}:R>",
            color=discord.Color.orange()
        )
        view = HapusIngatan(cog=self, user_id=ctx.author.id)
        
        if ctx.interaction:
            await ctx.interaction.response.send_message(embed=embed, view=view, ephemeral=True)
            view.message = await ctx.interaction.original_response()
        else:
            await ctx.send(embed=embed, view=view)

    @commands.hybrid_command(name="memory_status", description="Cek kapasitas memorimu", aliases=["status_memori", "cek_memori"])
    async def memory_status(self, ctx:commands.Context):
        if ctx.author.id not in self.user_chats:
            msg = "Mau cek apa? Aika aja belum tau apapun soalmu. 😒"
            if ctx.interaction:
                await ctx.interaction.response.send_message(msg, ephemeral=True)
            else:
                await ctx.send(msg, delete_after=12)
            return
        
        chat = self.user_chats[ctx.author.id]
        pesan_chat = [message for message in chat if message["role"] != "system"]
        jumlah_pesan = len(pesan_chat)
        
        kapasitas_max = self.max_memory_messages
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
            text="Pesan paling lama akan dihapus otomatis saat penuh.\nMau hapus semua sekalian? Gunakan ak!reset_memori",
            icon_url="https://cdn.discordapp.com/attachments/863959650448703538/1540201066455371888/bunga.png?ex=6a8b11c5&is=6a89c045&hm=2f7837e9e91cf914975584cb8ba5f001f80ea54d36c86e643547b1f23a111b26&"
        )
        embed.set_thumbnail(url=ctx.author.display_avatar.url)
        
        if ctx.interaction:
            await ctx.interaction.response.send_message(content=flavor, embed=embed, ephemeral=True)
        else:
            await ctx.send(content=flavor, embed=embed)

    @staticmethod
    def proses_gambar(attachment:discord.Attachment) -> dict | None:
        if attachment.size > UKURAN_FILE_MAKS_BYTES:
            return None
        return {
            "type": "image_url",
            "image_url": {"url": attachment.url}
        }

    @staticmethod
    def _ilangin_mention(teks:str) -> str:
        return teks.replace("@everyone", "`@everyone`").replace("@here", "`@here`")

    @staticmethod
    def _hapus_alur_berpikir(teks:str) -> str:
        if not teks:
            return ""
        return RE_PROSES_MIKIR.sub("", teks).strip()

    @staticmethod
    def _ekstrak_teksnya_doang(daftar_konten:list) -> str:
        kumpulan_teks = []
        for item in daftar_konten:
            if item.get("type") == "text":
                kumpulan_teks.append(item.get("text", ""))
            elif item.get("type") == "image_url":
                kumpulan_teks.append("[User uploaded an image]")
        return " ".join(kumpulan_teks).strip()

    @staticmethod
    def _masukin_ke_component_v2(raw_text:str) -> tuple[str,list[discord.ui.TextDisplay | discord.ui.Separator] | None,str]:
        kecocokan = RE_TAG_KONTEN.search(raw_text)
        if not kecocokan:
            return raw_text.strip(), None, ""
        
        teks_sebelum = raw_text[:kecocokan.start()].strip()
        teks_sesudah = raw_text[kecocokan.end():].strip()
        
        pesan_inti = kecocokan.group(1).strip()
        bagian_mentahan = RE_PEMISAH_BAGIAN.split(pesan_inti)
        
        components = []
        total_bagian = len(bagian_mentahan)
        for idx, bagian in enumerate(bagian_mentahan):
            teks_bagian = bagian.strip()
            if not teks_bagian:
                continue
            components.append(discord.ui.TextDisplay(content=teks_bagian))
            if idx < total_bagian - 1:
                components.append(discord.ui.Separator(spacing=discord.SeparatorSpacing.small))
        
        return teks_sebelum, components, teks_sesudah

    async def bikin_respon(self, user_id:int, adalah_admin:bool, chat:list, contents:list, penalaran_nyala:bool=False):
        aman, alasan = self.limiter.cek_batas(perkiraan_token=PERKIRAAN_TOKEN_DEFAULT)
        if not aman:
            raise RateLimitError(f"Local Safety Net: {alasan}")
        
        tz = timezone(timedelta(hours=7)) 
        sekarang = datetime.now(tz)
        
        hari_map = ["Senin", "Selasa", "Rabu", "Kamis", "Jumat", "Sabtu", "Minggu"]
        bulan_map = ["Januari", "Februari", "Maret", "April", "Mei", "Juni", "Juli", "Agustus", "September", "Oktober", "November", "Desember"]
        str_waktu = f"{hari_map[sekarang.weekday()]}, {sekarang.day} {bulan_map[sekarang.month-1]} {sekarang.year} - {sekarang.strftime('%H:%M')} WIB"
        konteks_waktu = f"[Waktu pesan ini dikirim: {str_waktu}]"
        
        prompt_sistem = self.infokan_instruksi_sistem(adalah_admin, konteks_waktu, penalaran_nyala=penalaran_nyala)
        isi_pesan = [prompt_sistem] + chat + [{"role": "user", "content": contents}]
        
        waktu_mulai = time.time()
        
        try:
            respon_mentah = await asyncio.to_thread(
                self.ai_client.chat.completions.with_raw_response.create,
                model=self.model,
                messages=isi_pesan,
                temperature=0.2,
                reasoning_effort="low" if penalaran_nyala else "none",
                max_completion_tokens=4096 if penalaran_nyala else MAKS_TOKEN_RESPON
            )
            waktu_proses = time.time() - waktu_mulai  # noqa: F841
            
            respon = respon_mentah.parse()
            headers = respon_mentah.headers
            penggunaan = respon.usage
            
            self.limiter.rekam_penggunaan(penggunaan.total_tokens)
            
            self.last_api_meta = { #rekam buat ditaruh di log
                "timestamp": time.time(),
                "model": respon.model,
                "prompt_tokens": penggunaan.prompt_tokens,
                "completion_tokens": penggunaan.completion_tokens,
                "total_tokens": penggunaan.total_tokens,
                "queue_time": getattr(penggunaan, "queue_time", 0.0),
                "prompt_time": getattr(penggunaan, "prompt_time", 0.0),
                "completion_time": getattr(penggunaan, "completion_time", 0.0),
                "total_time": getattr(penggunaan, "total_time", 0.0),
                "tok_per_sec": (penggunaan.completion_tokens / penggunaan.completion_time) if getattr(penggunaan, "completion_time", 0) > 0 else 0.0,
                "limit_req_daily": headers.get("x-ratelimit-limit-requests", "N/A"),
                "rem_req_daily": headers.get("x-ratelimit-remaining-requests", "N/A"),
                "reset_req_daily": headers.get("x-ratelimit-reset-requests", "N/A"),
                "limit_tok_min": headers.get("x-ratelimit-limit-tokens", "N/A"),
                "rem_tok_min": headers.get("x-ratelimit-remaining-tokens", "N/A"),
                "reset_tok_min": headers.get("x-ratelimit-reset-tokens", "N/A"),
            }
            
            self.session_usage["total_requests"] += 1
            self.session_usage["prompt_tokens"] += penggunaan.prompt_tokens
            self.session_usage["completion_tokens"] += penggunaan.completion_tokens
            self.session_usage["total_tokens"] += penggunaan.total_tokens
            
            teks_keluaran = respon.choices[0].message.content or "Hmm... Aika lagi blank. 😵"
            
            teks_murni_dari_user = self._ekstrak_teksnya_doang(contents)
            teks_riwayat_bot = RE_HAPUS_TAG_KONTEN.sub("", teks_keluaran).strip()
            
            chat.append({"role": "user", "content": teks_murni_dari_user.strip()})
            chat.append({"role": "assistant", "content": teks_riwayat_bot})
            
            if len(chat) > self.max_memory_messages:
                batas_potong = self.max_memory_messages - (self.max_memory_messages % 2)
                chat = chat[-batas_potong:]
                self.user_chats[user_id] = chat
            
            chat_id = await self.simpan_chat(user_id)
            return teks_keluaran, chat_id
            
        except Exception as e:
            print(f"[Aika] Gagal memanggil Groq: {e}")
            raise

    async def _eksekusi_regenerate(self, interaction:discord.Interaction, target_message:discord.Message):
        user_id = interaction.user.id
        
        if interaction.guild is None:
            return
        
        if target_message.author.id != self.bot.user.id:
            await interaction.response.send_message("Fitur ini cuma bisa dipakai untuk respon milik Aika! 💢", ephemeral=True)
            return
        
        if target_message.interaction is not None:
            await interaction.response.send_message("Pesan ini cuma respon dari command, bukan hasil chat kita! 😤", ephemeral=True)
            return
        
        pesan_original_dari_user = None
        if target_message.reference and target_message.reference.message_id:
            try:
                pesan_original_dari_user = await target_message.channel.fetch_message(target_message.reference.message_id)
                if pesan_original_dari_user.content.strip().startswith("ak!"):
                    await interaction.response.send_message("Pesan ini cuma respon dari command, bukan hasil chat kita! 😤", ephemeral=True)
                    return
                
                if pesan_original_dari_user.author.id != user_id:
                    await interaction.response.send_message("Kamu gabisa nge-regenerate respon Aika ke orang lain! 😤", ephemeral=True)
                    return
            except discord.NotFound:
                pesan_original_dari_user = None
        
        chat = self.user_chats.get(user_id, [])
        if not chat or len(chat) < 2 or chat[-1]["role"] != "assistant":
            await interaction.response.send_message("Gak ada respon Aika yang bisa di-regenerate.", ephemeral=True)
            return
        
        chat_aika_terakhir = chat[-1]["content"]
        if target_message.content.strip() != chat_aika_terakhir.strip():
            await interaction.response.send_message("Kamu cuma bisa regenerate respon Aika yang **paling baru**! 💢", ephemeral=True)
            return
        
        await interaction.response.defer(ephemeral=True)
        
        chat.pop()
        dict_entri_terakhir_dari_user = chat.pop()
        entri_terakhir_dari_user = dict_entri_terakhir_dari_user["content"]
        
        contents = []
        jumlah_gambar = 0
        if pesan_original_dari_user and pesan_original_dari_user.attachments:
            for attachment in pesan_original_dari_user.attachments:
                if attachment.content_type and attachment.content_type.startswith("image/"):
                    if jumlah_gambar >= MAKS_GAMBAR_PER_CHAT:
                        break
                    data_gambar = self.proses_gambar(attachment)
                    if data_gambar:
                        contents.append(data_gambar)
                        jumlah_gambar += 1
        
        teks_bersih = entri_terakhir_dari_user.replace("[User uploaded an image]", "").strip()
        if teks_bersih:
            contents.insert(0, {"type": "text", "text": teks_bersih})
        elif not contents:
            contents.insert(0, {"type": "text", "text": "Jelaskan gambar ini lagi."})
        
        adalah_admin = isinstance(interaction.user, discord.Member) and (
            interaction.user.guild_permissions.administrator or interaction.user.id == interaction.guild.owner_id
        )
        
        try:
            teks_keluaran = await self.bikin_respon(user_id, adalah_admin, chat, contents)
            teks_keluaran = self._ilangin_mention(teks_keluaran)
            
            await target_message.edit(content=teks_keluaran)
            await interaction.delete_original_response()
        except Exception:  # noqa: BLE001
            chat.append(dict_entri_terakhir_dari_user)
            chat.append({"role": "assistant", "content": chat_aika_terakhir})
            await self.simpan_chat(user_id)
            await interaction.followup.send("Aika gagal generate ulang respon, coba lagi nanti.", ephemeral=True)

    @commands.Cog.listener()
    async def on_message(self, message:discord.Message):
        if message.author.bot or message.guild is None or message.content.startswith("ak!"):
            return
        
        dalam_target_channel = (message.channel.id == self.target_channel_id)
        is_mentioned = self.bot.user.mentioned_in(message)
        if not dalam_target_channel and not is_mentioned:
            return
        
        ctx = await self.bot.get_context(message)
        if ctx.valid:
            await self.bot.process_commands(message)
            return
        
        if message.content.strip().startswith(",,"):
            return
        
        waktu_cooldown = WAKTU_TUNGGU_SALURAN_TARGET if dalam_target_channel else WAKTU_TUNGGU_MENTION
        sekarang = time.time()
        waktu_berlalu = sekarang - self.user_cooldowns.get(message.author.id, 0)
        
        if waktu_berlalu < waktu_cooldown:
            sisa_detik = waktu_cooldown - waktu_berlalu
            target_time = int(time.time() + sisa_detik)
            balasan = (
                "Sabar napa, ngirimnya jgn cepet-cepet! 🤌"
                if dalam_target_channel else
                f"Sabar, di luar channel khusus tunggu <t:{target_time}:R> lagi kalau mau nge-tag Aika! 😤"
            )
            await message.reply(balasan, delete_after=4, allowed_mentions=discord.AllowedMentions.none())
            return
        
        self.user_cooldowns[message.author.id] = sekarang
        
        adalah_admin = isinstance(message.author, discord.Member) and (
            message.author.guild_permissions.administrator or message.author.id == message.guild.owner_id
        )
        
        chat = self.cari_atau_buatchat(message.author.id)
        contents = []
        jumlah_gambar = 0
        
        for attachment in message.attachments:
            if attachment.content_type and attachment.content_type.startswith("image/"):
                if jumlah_gambar >= MAKS_GAMBAR_PER_CHAT:
                    break
                data_gambar = self.proses_gambar(attachment)
                if data_gambar is None:
                    await message.reply("Gambarnya kegedean, ih... 😭 Melebihi 20 MB...\nCoba kompres plis...")
                    return
                contents.append(data_gambar)
                jumlah_gambar += 1
        
        teks_bersih = message.clean_content
        if is_mentioned:
            teks_bersih = message.content.replace(f"<@{self.bot.user.id}>", "").replace(f"<@!{self.bot.user.id}>", "").strip()
        
        if teks_bersih:
            contents.insert(0, {"type": "text", "text": teks_bersih})
        
        if not contents:
            if message.guild:
                self.bot.dispatch(
                    "ai_log",
                    message.guild,
                    message.author,
                    "Masalah Intent",
                    "`contents` kosong, kemungkinan intent `Message Content` tidak aktif.",
                    discord.Color.red()
                )
            return
        
        str_role_id = str(ID_ROLE_REASONING)
        penalaran_nyala = (
            any(role.id == ID_ROLE_REASONING for role in message.role_mentions)
            or f"<@&{str_role_id}>" in message.content
            or "@reasoning" in message.content.lower()
        )
        
        async with message.channel.typing():
            try:
                teks_keluaran, chat_id = await self.bikin_respon(message.author.id, adalah_admin, chat, contents, penalaran_nyala=penalaran_nyala)
                
                if penalaran_nyala:
                    teks_keluaran_clean = self._hapus_alur_berpikir(teks_keluaran)
                    teks_sebelum, v2_components, teks_sesudah = self._masukin_ke_component_v2(teks_keluaran_clean)
                    
                    urutan_pesan = []
                    if teks_sebelum:
                        urutan_pesan.append({"type": "text", "content": teks_sebelum})
                    if v2_components:
                        container = discord.ui.Container()
                        for comp in v2_components:
                            container.add_item(comp)
                        view = discord.ui.LayoutView()
                        view.add_item(container)
                        urutan_pesan.append({"type": "view", "view": view})
                    if teks_sesudah:
                        urutan_pesan.append({"type": "text", "content": teks_sesudah})
                    if not urutan_pesan:
                        urutan_pesan.append({"type": "text", "content": teks_keluaran_clean})
                    
                    sudah_dibalas = False
                    for item in urutan_pesan:
                        if not sudah_dibalas:
                            if item["type"] == "text":
                                await message.reply(content=item["content"], allowed_mentions=discord.AllowedMentions.none())
                            else:
                                await message.reply(view=item["view"], allowed_mentions=discord.AllowedMentions.none())
                            sudah_dibalas = True
                        else:
                            if item["type"] == "text":
                                await message.channel.send(content=item["content"], allowed_mentions=discord.AllowedMentions.none())
                            else:
                                await message.channel.send(view=item["view"], allowed_mentions=discord.AllowedMentions.none())
                else:
                    clean_output = RE_HAPUS_TAG_KONTEN.sub("", teks_keluaran).strip()
                    clean_output = RE_BARIS_BARU_GANDA.sub("\n\n", clean_output)
                    await message.reply(clean_output, allowed_mentions=discord.AllowedMentions.none())
                
                if message.guild:
                    token_usage = self.last_api_meta.get("total_tokens", 0)
                    self.bot.dispatch(
                        "ai_log",
                        message.guild,
                        message.author,
                        "Respon Dikirim",
                        f"[Respon]({message.jump_url}) berhasil dikirim untuk {message.author.mention}\n-# Token terpakai: `{token_usage}`",
                        WARNA_AIKA,
                        None,
                        chat_id
                    )
                
            except RateLimitError as e:
                if message.guild:
                    self.bot.dispatch(
                        "ai_log",
                        message.guild,
                        message.author,
                        "Rate Limit Tercapai",
                        f"Pesan dari {message.author.mention} memicu Rate Limit AI.\n`{e!s}`",
                        discord.Color.red()
                    )
                
                error_msg = str(e)
                if "Local Safety Net:" in error_msg:
                    clean_reason = error_msg.replace("Local Safety Net:", "").strip()
                    reply = f"Aika lagi rehat bentar, ya... 😩\n`({clean_reason})`"
                else:
                    kecocokan = RE_WAKTU_RATE_LIMIT.search(error_msg)
                    if kecocokan:
                        hours = float(kecocokan.group(1) or 0)
                        minutes = float(kecocokan.group(2) or 0)
                        seconds = float(kecocokan.group(3) or 0)
                        total_seconds = int((hours * 3600) + (minutes * 60) + seconds)
                        target_time = int(time.time() + total_seconds)
                        reply = f"Duh, bentar... Aika rehat sejenak, ya. Coba lagi <t:{target_time}:R> (<t:{target_time}:t>) 😩"
                    else:
                        reply = "Duh, bentar... Aika rehat sejenak, ya. 😩\n`(Rate limit reached)`"
                
                await message.reply(reply, allowed_mentions=discord.AllowedMentions.none())
            
            except BadRequestError as e:
                print(f"[Groq] Bad request: {e}")
                await message.reply("Hmm... Aika lagi belum bisa proses, ya, coba lagi nanti. 😵", allowed_mentions=discord.AllowedMentions.none())
            
            except APIError as e:
                print(f"[Groq] API error: {e}")
                if message.guild:
                    self.bot.dispatch(
                        "ai_log",
                        message.guild,
                        message.author,
                        "API Error",
                        f"Gagal memproses pesan dari {message.author.mention}.\n`{e!s}`",
                        discord.Color.red()
                    )
                await message.reply("Ntar, ya... server AI lagi error... 😩", allowed_mentions=discord.AllowedMentions.none())
            
            except Exception as e:  # noqa: BLE001
                print(f"[Groq] Eror anomali: {type(e).__name__}: {e}")
                await message.reply("Aika lagi error bentar... 😵", allowed_mentions=discord.AllowedMentions.none())


async def setup(bot):
    await bot.add_cog(AIPersona(bot))
    try:
        bot.tree.add_command(buat_ulang_konteks_standalone)
    except app_commands.CommandAlreadyRegistered:
        pass