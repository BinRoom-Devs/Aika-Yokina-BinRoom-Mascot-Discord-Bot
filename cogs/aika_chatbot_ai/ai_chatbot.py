"""Berisi otak utama AI chatbot Aika."""

import asyncio
import os
import time
from datetime import datetime, timedelta, timezone

import discord
from discord import app_commands
from discord.ext import commands
from groq import APIError, BadRequestError, Groq, RateLimitError

import database

from ._config import (
    GROQ_API_KEY,
    ID_ROLE_REASONING,
    MAKS_GAMBAR_PER_CHAT,
    MAKS_TOKEN_RESPON,
    PERKIRAAN_TOKEN_DEFAULT,
    RE_BARIS_BARU_GANDA,
    RE_HAPUS_TAG_KONTEN,
    RE_WAKTU_RATE_LIMIT,
    WAKTU_TUNGGU_MENTION,
    WAKTU_TUNGGU_SALURAN_TARGET,
    WARNA_AIKA,
)
from ._persona import infokan_instruksi_sistem, muat_lore_cerita
from ._rate_limiter import PembatasRate
from ._utils import (
    ekstrak_teksnya_doang,
    hapus_alur_berpikir,
    ilangin_mention,
    masukin_ke_component_v2,
    proses_gambar,
)
from ._views import buat_ulang_konteks_standalone


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
        
        self.base_instruction = ""
    
    async def cog_load(self):
        await self.buka_memori_chat()
        await muat_lore_cerita(self)
    
    def cog_unload(self):
        try:
            self.bot.tree.remove_command(buat_ulang_konteks_standalone.name, type=buat_ulang_konteks_standalone.type)
        except Exception:  # noqa: BLE001, S110
            pass
    
    async def buka_memori_chat(self):
        try:
            self.user_chats = await database.load_all_user_chats()
        except Exception as e:  # noqa: BLE001
            print(f"[SQLite] Debug memori eror: gagal memuat memori: {e}")
            self.user_chats = {}
    
    async def simpan_chat(self, user_id:int|None=None) -> int | None:
        try:
            if user_id is not None:
                messages = self.user_chats.get(user_id, [])
                await database.save_user_chat(user_id, messages)
                return user_id
            else:
                for uid, chats in self.user_chats.items():
                    await database.save_user_chat(uid, chats)
                return None
        except Exception as e: # noqa: BLE001
            print(f"[SQLite] AI Chatbot: Gagal menyimpan memori: {e}")
            return None
    
    save_user_chats = simpan_chat
    
    def cari_atau_buatchat(self, user_id:int) -> list:
        if user_id not in self.user_chats:
            self.user_chats[user_id] = []
        return self.user_chats[user_id]
    
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
        
        prompt_sistem = infokan_instruksi_sistem(self, adalah_admin, konteks_waktu, penalaran_nyala=penalaran_nyala)
        isi_pesan = [prompt_sistem] + chat + [{"role": "user", "content": contents}]
        
        waktu_mulai = time.time()  # noqa: F841
        
        try:
            respon_mentah = await asyncio.to_thread(
                self.ai_client.chat.completions.with_raw_response.create,
                model=self.model,
                messages=isi_pesan,
                temperature=0.2,
                reasoning_effort="low" if penalaran_nyala else "none",
                max_completion_tokens=4096 if penalaran_nyala else MAKS_TOKEN_RESPON
            )
            
            respon = respon_mentah.parse()
            headers = respon_mentah.headers
            penggunaan = respon.usage
            
            self.limiter.rekam_penggunaan(penggunaan.total_tokens)
            
            self.last_api_meta = {
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
            
            teks_murni_dari_user = ekstrak_teksnya_doang(contents)
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
            print(f"[Groq] Gagal terhubung ke Groq: {e}")
            raise
    
    async def _eksekusi_regenerate(self, interaction:discord.Interaction, target_message:discord.Message):
        user_id = interaction.user.id
        
        if interaction.guild is None:
            return
        
        if target_message.author.id != self.bot.user.id:
            await interaction.response.send_message("Fitur ini cuma bisa dipakai untuk respon milik Aika! 💢", ephemeral=True)
            return
        
        if target_message.interaction_metadata is not None:
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
        
        # Make a copy of the current chat context to avoid corrupting self.user_chats on failure
        chat_copy = list(chat)
        chat_aika_terakhir_mem = chat_copy.pop()
        dict_entri_terakhir_dari_user = chat_copy.pop()
        entri_terakhir_dari_user = dict_entri_terakhir_dari_user["content"]
        
        contents = []
        jumlah_gambar = 0
        if pesan_original_dari_user and pesan_original_dari_user.attachments:
            if len(pesan_original_dari_user.attachments) > MAKS_GAMBAR_PER_CHAT:
                await interaction.followup.send(
                    f"Pesan asli punya lebih dari {MAKS_GAMBAR_PER_CHAT} gambar, gak bisa di-regenerate! 😭",
                    ephemeral=True
                )
                return
            
            for attachment in pesan_original_dari_user.attachments:
                if attachment.content_type and attachment.content_type.startswith("image/"):
                    if jumlah_gambar >= MAKS_GAMBAR_PER_CHAT:
                        break
                    data_gambar = proses_gambar(attachment)
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
            teks_keluaran, _ = await self.bikin_respon(user_id, adalah_admin, chat_copy, contents)
            teks_keluaran = ilangin_mention(teks_keluaran)
            
            self.user_chats[user_id] = chat_copy
            
            await target_message.edit(content=teks_keluaran)
            await interaction.delete_original_response()
        except Exception as e:  # noqa: BLE001
            print(f"[Regenerate Error]: {e}")
            await interaction.followup.send("Aika gagal generate ulang respon, coba lagi nanti.", ephemeral=True)
    
    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
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
        
        if len(message.attachments) > MAKS_GAMBAR_PER_CHAT:
            await message.reply("Aika cuma bisa proses sampai 3 gambar doang.. 😔")
            return
        
        for attachment in message.attachments:
            if attachment.content_type and attachment.content_type.startswith("image/"):
                if jumlah_gambar >= MAKS_GAMBAR_PER_CHAT:
                    break
                data_gambar = proses_gambar(attachment)
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
                    teks_keluaran_clean = hapus_alur_berpikir(teks_keluaran)
                    teks_sebelum, v2_components, teks_sesudah = masukin_ke_component_v2(teks_keluaran_clean)
                    
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