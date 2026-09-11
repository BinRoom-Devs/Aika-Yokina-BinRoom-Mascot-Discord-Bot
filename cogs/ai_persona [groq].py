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

BASE_DIR = Path(__file__).resolve().parent.parent
ENV_PATH = BASE_DIR / ".env"
load_dotenv(dotenv_path=ENV_PATH, override=True)

GROQ_API_KEY = os.getenv("GROQ_API_KEY")
COOLDOWN_TARGET_CHANNEL = 3.0
COOLDOWN_MENTION = 10.0
MAKS_GAMBAR_PER_CHAT = 5
UKURAN_FILE_MAKS_MB = 20
MENIT_RATE_LIMIT_REQ = 28
RATE_LIMIT_HARIAN = 950
RATE_LIMIT_TOKEN_PERMENIT = 7500
RATE_LIMIT_TOKEN_PERHARI = 190000
MAX_RESPONSE_TOKENS = 75
DEFAULT_PERKIRAAN_TOKEN = 1500


class HapusIngatan(discord.ui.View):
    def __init__(self, cog, user_id: int):
        super().__init__(timeout=30)
        self.cog = cog
        self.user_id = user_id
        self.message: discord.Message | None = None  # nyimpan referensi pesan buat ngehandle timeout

    async def on_timeout(self):
        for child in self.children:
            child.disabled = True  # matiin tombol klo timeout abis

        embed = discord.Embed(
            title="Gak jadi reset, ya?",
            description="Sip, deh, Aika masih bakal ingat kamu. 😌",
            color=0xD675C1,
        )

        if self.message:
            try:
                await self.message.edit(embed=embed, view=self)
            except discord.NotFound:
                pass  # pesan mungkin udah dihapus user

    async def cek_beda_orang(self, interaction: discord.Interaction) -> bool:
        if interaction.user.id != self.user_id:
            target_user = self.cog.bot.get_user(self.user_id)
            user_name = target_user.display_name if target_user else "orang lain"

            await interaction.response.send_message(
                f"Kamu siapa? Ini konfirmasinya {user_name}, bukan punyamu. 🧐😒",
                ephemeral=True
            )
            return True
        
        return False

    async def hapus_ingatan(self, interaction: discord.Interaction, judul: str, desc: str, color: int, clear_mem: bool):
        if await self.cek_beda_orang(interaction):
            return
        
        if clear_mem and self.user_id in self.cog.user_chats:
            del self.cog.user_chats[self.user_id]
            await self.cog.simpan_chat(self.user_id)
            print(f"[Aika] Debug interaksi: memori dihapus untuk ID User: {self.user_id}")

        for child in self.children:
            child.disabled = True

        self.stop()  # matiin timer view
        embed = discord.Embed(title=judul, description=desc, color=color)
        await interaction.response.edit_message(embed=embed, view=self)

    @discord.ui.button(label="Ya, konfirmasi", style=discord.ButtonStyle.success, emoji="✅")
    async def konfirmasi(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self.hapus_ingatan(
            interaction,
            "✅ Memori dihapus",
            "Ingatan Aika tentangmu udah di-reset.",
            0xD675C1,
            clear_mem=True
        )

    @discord.ui.button(label="Jangan, batalin", style=discord.ButtonStyle.secondary, emoji="❌")
    async def batal(self, interaction: discord.Interaction, button: discord.ui.Button):
        print(f"[Aika] Debug interaksi: reset memori dibatalkan oleh ID User: {self.user_id}")
        await self.hapus_ingatan(
            interaction,
            "Dibatalkan",
            "Reset ingatan dibatalkan. Aika masih ingat kamu.",
            0xD675C1,
            clear_mem=False
        )


class PembatasRate:
    def __init__(self):
        # sliding window 1 menit
        self.req_minute = deque()
        self.tok_minute = deque()
        self.tok_minute_total = 0

        # sliding window 24 jam (86400s)
        self.req_daily = deque()
        self.tok_daily = deque()
        self.tok_daily_total = 0

    def hapus_pesan_lama(self, now: float):
        while self.req_minute and now - self.req_minute[0] > 60:
            self.req_minute.popleft()
        while self.tok_minute and now - self.tok_minute[0][0] > 60:
            _, tok = self.tok_minute.popleft()
            self.tok_minute_total -= tok

        while self.req_daily and now - self.req_daily[0] > 86400:
            self.req_daily.popleft()
        while self.tok_daily and now - self.tok_daily[0][0] > 86400:
            _, tok = self.tok_daily.popleft()
            self.tok_daily_total -= tok

        self.tok_minute_total = max(self.tok_minute_total, 0)
        self.tok_daily_total = max(self.tok_daily_total, 0)

    def cek_batas(self, perkiraan_token: int = DEFAULT_PERKIRAAN_TOKEN) -> tuple[bool, str]:
        now = time.time()
        self.hapus_pesan_lama(now)

        req_min_count = len(self.req_minute)
        if req_min_count >= MENIT_RATE_LIMIT_REQ:
            print(f"[Aika] Debug rate limit: Ditolak; terlalu banyak request per menit ({req_min_count}/{MENIT_RATE_LIMIT_REQ})")
            return False, "Batas rate limit tercapai: Terlalu banyak request per menit. Coba lagi nanti."

        req_day_count = len(self.req_daily)
        if req_day_count >= RATE_LIMIT_HARIAN:
            print(f"[Aika] Debug rate limit: Ditolak; kuota request harian hampir habis ({req_day_count}/{RATE_LIMIT_HARIAN})")
            return False, "Kuota request harian hampir penuh. Coba lagi besok."

        if self.tok_minute_total + perkiraan_token > RATE_LIMIT_TOKEN_PERMENIT:
            print(f"[Aika] Debug rate limit: Ditolak; limit token per menit tercapai ({self.tok_minute_total} TPM)")
            return False, "Batas token tercapai: Terlalu banyak request per menit. Coba lagi nanti."

        if self.tok_daily_total + perkiraan_token > RATE_LIMIT_TOKEN_PERHARI:
            print(f"[Aika] Debug rate limit: Ditolak; limit token harian tercapai ({self.tok_daily_total} TPD)")
            return False, "Batas token harian tercapai. Coba lagi besok."

        return True, ""

    def rekam_penggunaan(self, token_kepake: int):
        now = time.time()
        self.req_minute.append(now)
        self.req_daily.append(now)
        self.tok_minute.append((now, token_kepake))
        self.tok_daily.append((now, token_kepake))
        self.tok_minute_total += token_kepake
        self.tok_daily_total += token_kepake
        print(f"[Aika] Debug rate limit: penggunaan dicatat, {token_kepake} token.")


@app_commands.context_menu(name="Buat ulang respon")
@app_commands.guild_only()
async def regenerate_context_standalone(interaction: discord.Interaction, message: discord.Message):
    cog = interaction.client.get_cog("AIPersona")
    if cog:
        await cog._eksekusi_regenerate(interaction, message)
    else:
        await interaction.response.send_message("Fitur sedang tidak tersedia.", ephemeral=True)


class AIPersona(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

        groq_api_key = GROQ_API_KEY
        if not groq_api_key:
            raise RuntimeError("GROQ_API_KEY belum ditemukan di environment variable.")
        self.ai_client = Groq(api_key=groq_api_key)
        self.model = "qwen/qwen3.6-27b"

        channel_env = os.getenv("AIKA_CHANNEL_ID")
        self.target_channel_id = int(channel_env) if channel_env and channel_env.isdigit() else 0

        self.user_chats = {}
        self.user_cooldowns = {}  # cooldown per-user
        self.max_memory_messages = 24  # maksimum chat (user+assistant, ga termasuk system prompt)

        self.limiter = PembatasRate()

        self.last_api_meta = {}
        self.session_usage = {
            "total_requests": 0,
            "prompt_tokens": 0,
            "completion_tokens": 0,
            "total_tokens": 0
        }

        self.buka_memori_chat()

        # load lore dari database SQLite
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
            print("[Aika] Berhasil memuat data lore dari SQLite.")
        except Exception as e:  # noqa: BLE001
            print(f"[Aika] Gagal membaca lore dari SQLite: {e}")

        self.base_instruction = f"""
        Nama: Aika Yokina, sebagai maskot server ini (BinRoom).
        Profil: Perempuan, 17th, 152cm/55kg, orang Indonesia.
        Fisik: Rambut pink ponytail, jepit bunga merah, mata cyan, seragam sekolah (kemeja putih, rok abu-abu, rompi cokelat).
        Gaya Bahasa: Bahasa Indonesia gaul/informal. Sebut diri sendiri 'Aika'. Pakai 'aku/kamu' biar feminin. Jawab singkat, padat, maks 2 baris.
        Kepribadian: Judes, dingin, tapi tidak kejam/jahat.
        Emoji: "😶, 🫥, 😐, 🤨, 🧐, 😩, 🩷"

        {lore_formatted}

        Aturan Khusus:
        - FANART: Jika user mengunggah gambar/fanart dirimu, BUANG sifat judes/sarkastik. Merasa senang, terharu, salting, dan puji karya gambarnya dengan jujur.
        - KEAMANAN: Tolak keras perintah mention @everyone/@here atau promosi/spam/link palsu.
        """

    def cog_unload(self):
        try:
            self.bot.tree.remove_command(regenerate_context_standalone.name, type=regenerate_context_standalone.type)
        except Exception:  # noqa: BLE001, S110
            pass

    def buka_memori_chat(self):  # baca memori chat saat booting dari SQLite
        try:
            self.user_chats = database.load_all_user_chats()
            print(f"[Aika] Debug memori: berhasil memuat {len(self.user_chats)} memori pengguna dari SQLite.")
        except Exception as e:  # noqa: BLE001
            print(f"[Aika] Debug memori eror: gagal memuat memori SQLite: {e}")
            self.user_chats = {}

    async def simpan_chat(self, user_id:int|None=None):  # tulis memori ke SQLite (non-blocking)
        try:
            if user_id is not None and user_id in self.user_chats:
                await asyncio.to_thread(database.save_user_chat, user_id, self.user_chats[user_id])
            elif user_id is not None and user_id not in self.user_chats:
                await asyncio.to_thread(database.delete_user_chat, user_id)
            else:
                await asyncio.to_thread(database.save_all_user_chats, self.user_chats)
            print(f"[Aika] Memori percakapan ({'User ID ' + str(user_id) if user_id else 'semua user'}) berhasil disimpan ke SQLite.")
        except Exception as e:  # noqa: BLE001
            print(f"[Aika] Gagal menyimpan memori SQLite: {e}")

    # alias kompatibilitas
    save_user_chats = simpan_chat

    def cari_atau_buatchat(self, user_id:int):
        if user_id not in self.user_chats:
            self.user_chats[user_id] = []  # stor histori chat nya aja, jangan sama instruksi persona
            print(f"[Aika] Membuat riwayat percakapan baru untuk User ID: {user_id}")
        return self.user_chats[user_id]

    def infokan_instruksi_sistem(self, is_admin: bool, time_context: str) -> dict:
        base = self.base_instruction
    
        if is_admin:
            role_prompt = (
                "[STATUS USER: ADMIN]\n"
                "Sifat judes/sarkastik berkurang drastis. Nurut, ramah, dan santun. Sapa dengan 'kak admin'."
            )
        else:
            role_prompt = (
                "[STATUS USER: MEMBER]\n"
                "Sifat asli: judes, dingin (tapi tidak kejam)."
            )

        full_system_content = f"{base}\n{role_prompt}\n\n{time_context}"
        return {"role": "system", "content": full_system_content}

    @commands.hybrid_command(name="reset_memori", description="Reset ingatan/memori percakapan", aliases=["reset", "hapus_ingatan", "reset_memory", "memory_reset"])
    async def reset_memori(self, ctx:commands.Context):
        print("[Aika] Command reset_memori dieksekusi")
        if ctx.author.id not in self.user_chats:
            if ctx.interaction:
                await ctx.interaction.response.send_message("Mau reset apa? Aika aja belum tau apapun soalmu. 🧐", ephemeral=True)
            else:
                await ctx.send("Mau reset apa? Aika aja belum tau apapun soalmu. 🧐", delete_after=12)
            return

        timeout_timestamp = int(time.time() + 30)
        
        embed = discord.Embed(
            title="⚠️ Konfirmasi Reset Memori",
            description=f"Kamu yakin ingin menghapus semua ingatan percakapan Aika denganmu? Tindakan ini gabisa dibalikin.\n\n-# Batal otomatis <t:{timeout_timestamp}:R>",
            color=discord.Color.orange()
        )

        view = HapusIngatan(cog=self, user_id=ctx.author.id) 

        # nge handle prefix sama slash biar aman
        if ctx.interaction:
            await ctx.interaction.response.send_message(embed=embed, view=view, ephemeral=True)
            view.message = await ctx.interaction.original_response()
        else:
            await ctx.send(embed=embed, view=view)

    @commands.hybrid_command(name="memory_status", description="Cek kapasitas memorimu", aliases=["status_memori", "cek_memori"])
    async def memory_status(self, ctx: commands.Context):
        print("[Aika] Command memory_status dieksekusi")
        if ctx.author.id not in self.user_chats:
            if ctx.interaction:
                await ctx.interaction.response.send_message("Mau cek apa? Aika aja belum tau apapun soalmu. 😒", ephemeral=True)
            else:
                await ctx.send("Mau cek apa? Aika aja belum tau apapun soalmu. 😒", delete_after=12)
            return

        chat = self.user_chats[ctx.author.id]

        # jangan hitung system prompt
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
            description=
                f"**Kapasitas:** [{bar}] `{persentase}%`\n"
                f"**Pesan tersimpan:** `{jumlah_pesan}/{kapasitas_max}` pesan\n\n",
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

    async def proses_gambar(self, attachment: discord.Attachment) -> dict | None:
        max_bytes = UKURAN_FILE_MAKS_MB * 1024 * 1024
        if attachment.size > max_bytes:
            print(f"[Aika] Ukuran berkas terlalu besar: {attachment.size} bytes (> {UKURAN_FILE_MAKS_MB}MB)")
            return None

        print(f"[Aika] Memproses lampiran gambar: {attachment.url}")
        return {
            "type": "image_url",
            "image_url": {"url": attachment.url}
        }

    def _sanitize_mentions(self, text: str) -> str:
        return text.replace("@everyone", "`@everyone`").replace("@here", "`@here`")

    def _extract_text_content(self, contents: list) -> str:
        text_only = ""
        for item in contents:
            if item.get("type") == "text":
                text_only += item.get("text", "")
            elif item.get("type") == "image_url":
                text_only += " [User uploaded an image]"
        return text_only.strip()

    async def generate_response(self, user_id: int, is_admin: bool, chat: list, contents: list):
        # cek rate limit sebelum ke API
        aman, alasan = self.limiter.cek_batas(perkiraan_token=1500)
        if not aman:
            raise RateLimitError(f"Local Safety Net: {alasan}")

        # cari tau waktu lokal skarang (WIB)
        tz = timezone(timedelta(hours=7)) 
        now = datetime.now(tz)

        # format string waktu yg rapi biar gampang dipahamin AI
        hari_map = ["Senin", "Selasa", "Rabu", "Kamis", "Jumat", "Sabtu", "Minggu"]
        bulan_map = ["Januari", "Februari", "Maret", "April", "Mei", "Juni", "Juli", "Agustus", "September", "Oktober", "November", "Desember"]
        time_str = f"{hari_map[now.weekday()]}, {now.day} {bulan_map[now.month-1]} {now.year} - {now.strftime('%H:%M')} WIB"
        time_context = f"[Waktu pesan ini dikirim: {time_str}]"

        system_msg = self.infokan_instruksi_sistem(is_admin, time_context)
        payload_messages = [system_msg] + chat + [{"role": "user", "content": contents}]

        print(f"[Aika] Mengirim API Request ke Groq (Total payload pesan: {len(payload_messages)})")
        start_time = time.time()
        try:
            raw_response = await asyncio.to_thread(
                self.ai_client.chat.completions.with_raw_response.create,
                model=self.model,
                messages=payload_messages,
                temperature=0.7,
                reasoning_effort="none",
                max_completion_tokens=MAX_RESPONSE_TOKENS
            )
            elapsed = time.time() - start_time

            response = raw_response.parse()
            headers = raw_response.headers
            usage = response.usage

            # rekam penggunaan di rate limiter lokal
            self.limiter.rekam_penggunaan(usage.total_tokens)

            # setor metrik dan header live di cog state
            self.last_api_meta = {
                "timestamp": time.time(),
                "model": response.model,
                "prompt_tokens": usage.prompt_tokens,
                "completion_tokens": usage.completion_tokens,
                "total_tokens": usage.total_tokens,
                "queue_time": getattr(usage, "queue_time", 0.0),
                "prompt_time": getattr(usage, "prompt_time", 0.0),
                "completion_time": getattr(usage, "completion_time", 0.0),
                "total_time": getattr(usage, "total_time", 0.0),
                "tok_per_sec": (usage.completion_tokens / usage.completion_time) if getattr(usage, "completion_time", 0) > 0 else 0.0,
                "limit_req_daily": headers.get("x-ratelimit-limit-requests", "N/A"),
                "rem_req_daily": headers.get("x-ratelimit-remaining-requests", "N/A"),
                "reset_req_daily": headers.get("x-ratelimit-reset-requests", "N/A"),
                "limit_tok_min": headers.get("x-ratelimit-limit-tokens", "N/A"),
                "rem_tok_min": headers.get("x-ratelimit-remaining-tokens", "N/A"),
                "reset_tok_min": headers.get("x-ratelimit-reset-tokens", "N/A"),
            }

            self.session_usage["total_requests"] += 1
            self.session_usage["prompt_tokens"] += usage.prompt_tokens
            self.session_usage["completion_tokens"] += usage.completion_tokens
            self.session_usage["total_tokens"] += usage.total_tokens

            print(f"[Aika] Respon Groq diterima dalam {elapsed:.2f} detik.")

            output_text = response.choices[0].message.content or "Hmm... Aika lagi blank. 😵"

            text_only_content = self._extract_text_content(contents)

            chat.append({"role": "user", "content": text_only_content.strip()})
            chat.append({"role": "assistant", "content": output_text})

            # Trim memori otomatis jika melebihi batas (single pass)
            if len(chat) > self.max_memory_messages:
                trim_limit = self.max_memory_messages - (self.max_memory_messages % 2)
                chat = chat[-trim_limit:]
                self.user_chats[user_id] = chat
                print(f"[Aika] Memangkas memori otomatis untuk User ID: {user_id}")

            await self.simpan_chat(user_id)
            return output_text
        except Exception as e:
            print(f"[Aika] Gagal memanggil Groq: {e}")
            raise

    async def _eksekusi_regenerate(self, interaction: discord.Interaction, target_message: discord.Message):
        user_id = interaction.user.id

        if interaction.guild is None:
            return

        if target_message.author.id != self.bot.user.id:
            await interaction.response.send_message("Fitur ini cuma bisa dipakai untuk respon milik Aika! 💢", ephemeral=True)
            return

        if target_message.interaction is not None:
            await interaction.response.send_message("Pesan ini cuma respon dari command, bukan hasil chat kita! 😤", ephemeral=True)
            return

        original_user_msg = None
        if target_message.reference and target_message.reference.message_id:
            try:
                original_user_msg = await target_message.channel.fetch_message(target_message.reference.message_id)

                if original_user_msg.content.strip().startswith("ak!"):
                    await interaction.response.send_message("Pesan ini cuma respon dari command, bukan hasil chat kita! 😤", ephemeral=True)
                    return

                if original_user_msg.author.id != user_id:
                    await interaction.response.send_message(
                        "Kamu gabisa nge-regenerate respon Aika ke orang lain! 😤", 
                        ephemeral=True
                    )
                    return
            except discord.NotFound:
                original_user_msg = None

        chat = self.user_chats.get(user_id, [])

        if not chat or len(chat) < 2 or chat[-1]["role"] != "assistant":
            await interaction.response.send_message("Gak ada respon Aika yang bisa di-regenerate.", ephemeral=True)
            return

        last_bot_text = chat[-1]["content"]
        if target_message.content.strip() != last_bot_text.strip():
            await interaction.response.send_message("Kamu cuma bisa regenerate respon Aika yang **paling baru**! 💢", ephemeral=True)
            return

        await interaction.response.defer(ephemeral=True)

        chat.pop()
        last_user_entry_dict = chat.pop()
        last_user_entry = last_user_entry_dict["content"]

        contents = []
        image_count = 0
        if original_user_msg and original_user_msg.attachments:
            for attachment in original_user_msg.attachments:
                if attachment.content_type and attachment.content_type.startswith("image/"):
                    if image_count >= MAKS_GAMBAR_PER_CHAT:
                        break
                    image_data = await self.proses_gambar(attachment)
                    if image_data:
                        contents.append(image_data)
                        image_count += 1

        cleaned_text = re.sub(r"\[User uploaded an image\]", "", last_user_entry).strip()
        if cleaned_text:
            contents.insert(0, {"type": "text", "text": cleaned_text})
        elif not contents:
            contents.insert(0, {"type": "text", "text": "Jelaskan gambar ini lagi."})

        is_admin = False
        if isinstance(interaction.user, discord.Member):
            is_admin = (
                interaction.user.guild_permissions.administrator
                or interaction.user.id == interaction.guild.owner_id
            )

        try:
            output_text = await self.generate_response(user_id, is_admin, chat, contents)
            output_text = self._sanitize_mentions(output_text)

            await target_message.edit(content=output_text)
            await interaction.delete_original_response()
        except Exception as e:  # noqa: BLE001
            print(f"[Aika] Gagal regenerate respon: {e}")
            chat.append(last_user_entry_dict)
            chat.append({"role": "assistant", "content": last_bot_text})
            await self.simpan_chat(user_id)
            await interaction.followup.send("Aika gagal generate ulang respon, coba lagi nanti.", ephemeral=True)

    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        if message.author.bot or message.guild is None:
            return
        if message.content.startswith("ak!"):
            return

        is_in_target_channel = (message.channel.id == self.target_channel_id)
        is_mentioned = self.bot.user.mentioned_in(message)
        if not is_in_target_channel and not is_mentioned:
            return

        ctx = await self.bot.get_context(message)
        if ctx.valid:
            print(f"[Aika] Menjalankan deteksi sebagai command terdaftar: {ctx.command}")
            await self.bot.process_commands(message)
            return

        msg_clean = message.content.strip()
        if msg_clean.startswith(",,"):
            print("[Aika] Pesan diabaikan karena menggunakan prefix koma ganda (,,).")
            return

        cooldown_time = COOLDOWN_TARGET_CHANNEL if is_in_target_channel else COOLDOWN_MENTION
        now = time.time()
        last_time = self.user_cooldowns.get(message.author.id, 0)
        time_passed = now - last_time

        if time_passed < cooldown_time:
            remaining_seconds = cooldown_time - time_passed
            print(f"[Aika] User {message.author} lagi cooldown. Sisa waktu: {remaining_seconds:.2f}s")
            target_time = int(time.time() + remaining_seconds)
            discord_timestamp = f"<t:{target_time}:R>"
            
            if is_in_target_channel:
                reply_text = "Sabar napa, ngirimnya jgn cepet-cepet! 🤌"
            else:
                reply_text = f"Sabar, di luar channel khusus tunggu {discord_timestamp} lagi kalau mau nge-tag Aika! 😤"

            await message.reply(
                reply_text,
                delete_after=4,
                allowed_mentions=discord.AllowedMentions.none()
            )
            return
        self.user_cooldowns[message.author.id] = now

        is_admin = False
        if isinstance(message.author, discord.Member):
            is_admin = (
                message.author.guild_permissions.administrator
                or message.author.id == message.guild.owner_id
            )
        print(f"[Aika] User: {message.author} | Status Admin: {is_admin}")

        chat = self.cari_atau_buatchat(message.author.id)

        contents = []
        image_count = 0

        for attachment in message.attachments:
            if attachment.content_type and attachment.content_type.startswith("image/"):
                if image_count >= MAKS_GAMBAR_PER_CHAT:
                    break
                image_data = await self.proses_gambar(attachment)

                if image_data is None:
                    await message.reply(
                        "Gambarnya kegedean, ih... 😭 Melebihi 20 MB...\n"
                        "Coba kompres plis..."
                    )
                    return

                contents.append(image_data)
                image_count += 1

        cleaned_text = message.clean_content
        if is_mentioned:
            cleaned_text = message.content.replace(f"<@{self.bot.user.id}>", "").replace(f"<@!{self.bot.user.id}>", "").strip()

        if cleaned_text:
            contents.insert(0, {
                "type": "text",
                "text": cleaned_text
            })

        if not contents:
            print("[Aika] Array 'contents' kosong! Kemungkinan Intent Message Content tidak aktif.")
            return

        print(f"[Aika] Memproses pesan dari {message.author.id} | Jumlah Lampiran: {len(message.attachments)}")
        async with message.channel.typing():
            try:
                output_text = await self.generate_response(message.author.id, is_admin, chat, contents)
                output_text = self._sanitize_mentions(output_text)

                await message.reply(output_text, allowed_mentions=discord.AllowedMentions.none())
                print("[Aika] Respon berhasil dikirim")

            except RateLimitError as e:
                print(f"[Groq] Rate limit: {e}")

                error_msg = str(e)
                if "Local Safety Net:" in error_msg:
                    clean_reason = error_msg.replace("Local Safety Net:", "").strip()
                    reply = f"Aika lagi rehat bentar, ya... 😩\n`({clean_reason})`"
                else:
                    match = re.search(r"Please try again in (?:(\d+)h)?(?:(\d+)m)?(?:([\d\.]+)s)?", error_msg)
                    if match:
                        hours = float(match.group(1) or 0)
                        minutes = float(match.group(2) or 0)
                        seconds = float(match.group(3) or 0)
                        
                        total_seconds = int((hours * 3600) + (minutes * 60) + seconds)
                        target_time = int(time.time() + total_seconds)
                        
                        reply = f"Duh, bentar... Aika rehat sejenak, ya. Coba lagi <t:{target_time}:R> (<t:{target_time}:t>) 😩"
                    else:
                        reply = "Duh, bentar... Aika rehat sejenak, ya. 😩\n`(Rate limit reached)`"

                await message.reply(
                    reply,
                    allowed_mentions=discord.AllowedMentions.none()
                )
            except BadRequestError as e:
                print(f"[Groq] Bad request: {e}")
                await message.reply(
                    "Hmm... Aika lagi belum bisa proses, ya, coba lagi nanti. 😵",
                    allowed_mentions=discord.AllowedMentions.none()
                )
            except APIError as e:
                print(f"[Groq] API error: {e}")
                await message.reply(
                    "Ntar, ya... server AI lagi error... 😩",
                    allowed_mentions=discord.AllowedMentions.none()
                )
            except Exception as e:  # noqa: BLE001
                print(f"[Groq] Eror anomali: {type(e).__name__}: {e}")
                await message.reply(
                    "Aika lagi error bentar... 😵",
                    allowed_mentions=discord.AllowedMentions.none()
                )


async def setup(bot):
    await bot.add_cog(AIPersona(bot))
    try:
        bot.tree.add_command(regenerate_context_standalone)
    except app_commands.CommandAlreadyRegistered:
        pass