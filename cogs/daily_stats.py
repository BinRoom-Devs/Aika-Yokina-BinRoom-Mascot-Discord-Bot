import collections
import json
import os
import re
from datetime import datetime, time, timedelta, timezone

import discord
from discord.ext import commands, tasks

ID_CHANNEL_LOG = 932191307789656064
WIB = timezone(timedelta(hours=7))
FILE_PATH = "data/stats_harian.json"

HARI_INDONESIA = {
    "Monday": "Senin",
    "Tuesday": "Selasa",
    "Wednesday": "Rabu",
    "Thursday": "Kamis",
    "Friday": "Jumat",
    "Saturday": "Sabtu",
    "Sunday": "Minggu",
}

BULAN_INDONESIA = {
    1: "Januari",
    2: "Februari",
    3: "Maret",
    4: "April",
    5: "Mei",
    6: "Juni",
    7: "Juli",
    8: "Agustus",
    9: "September",
    10: "Oktober",
    11: "November",
    12: "Desember",
}


class StatistikHarian(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.data_stats = self._default_stats()
        self._muat_statistik()
        self.tugas_laporan_harian.start()

    def cog_unload(self):
        self.tugas_laporan_harian.cancel()

    def _default_stats(self) -> dict:
        """Struktur default data statistik."""
        return {
            # field 1: aktivitas chat
            "pesan_dikirim": 0,
            "pesan_dihapus": 0,
            "pesan_diedit": 0,
            "media_dikirim": 0,
            # field 2: reaction & emoji
            "emoji_digunakan": collections.Counter(),
            "reaction_ditambahkan": 0,
            # field 3: keanggotaan
            "member_bergabung": 0,
            "member_keluar": 0,
            "member_dikick": 0,
            "member_diban": 0,
            "member_timeout": 0,
            "member_ubah_username": 0,
            "member_ubah_foto_profil": 0,
            "member_ubah_foto_sampul": 0,
            "member_ubah_nickname": 0,
            "member_berganti_role": 0,
            "member_boost_server": 0,
            # field 4: aktivitas voice
            "vc_bergabung": 0,
            "vc_keluar": 0,
            "vc_durasi_total": 0,
            "vc_jumlah_sesi": 0,
            "vc_share_screen": 0,
            # field 5: pengaturan server
            "channel_dibuat": 0,
            "channel_nama_diubah": 0,
            "channel_dihapus": 0,
            "role_dibuat": 0,
            "role_pengaturan_diubah": 0,
            "server_nama_diubah": 0,
            "server_foto_diubah": 0,
            "server_sampul_diubah": 0,
            "webhook_diubah": 0,
            "integrasi_dibuat": 0,
            "emoji_ditambahkan": 0,
            "emoji_dihapus": 0,
            "thread_dibuat": 0,
            "thread_dihapus": 0,
            "thread_diarsipkan": 0,
            "thread_nama_diubah": 0,
            "event_dibuat": 0,
            "event_dibatalkan": 0,
        }

    def _simpan_statistik(self):
        os.makedirs(os.path.dirname(FILE_PATH), exist_ok=True)
        data_to_save = self.data_stats.copy()
        
        if isinstance(data_to_save["emoji_digunakan"], collections.Counter):
            data_to_save["emoji_digunakan"] = dict(data_to_save["emoji_digunakan"])

        with open(FILE_PATH, "w", encoding="utf-8") as f:
            json.dump(data_to_save, f, indent=4, ensure_ascii=False)

    def _muat_statistik(self):
        if not os.path.exists(FILE_PATH):
            return

        try:
            with open(FILE_PATH, "r", encoding="utf-8") as f:
                loaded_data = json.load(f)

            if "emoji_digunakan" in loaded_data:
                loaded_data["emoji_digunakan"] = collections.Counter(loaded_data["emoji_digunakan"])

            for key, val in loaded_data.items():
                if key in self.data_stats:
                    self.data_stats[key] = val

        except (OSError, json.JSONDecodeError):
            pass

    def _reset_statistik(self):
        """Reset data ke default dan hapus/timpa isi JSON."""
        self.data_stats = self._default_stats()
        self._simpan_statistik()

    def _tambah_stat(self, key: str, value: int = 1):
        """Helper internal untuk update counter sekaligus auto-save."""
        self.data_stats[key] += value
        self._simpan_statistik()

    @staticmethod
    def format_durasi(detik:int) -> str:
        detik = max(int(detik), 0)
        menit, s = divmod(detik, 60)
        jam, m = divmod(menit, 60)
        if jam > 0:
            return f"{jam} jam {m} menit" if m > 0 else f"{jam} jam"
        elif m > 0:
            return f"{m} menit {s} detik" if s > 0 else f"{m} menit"
        else:
            return f"{s} detik"

    # ==========================================
    # PENANGKAP EVENT / STATISTIK
    # ==========================================

    @commands.Cog.listener()
    async def on_message(self, message:discord.Message):
        if not message.guild or message.author.bot:
            return

        self.data_stats["pesan_dikirim"] += 1
        if message.attachments:
            self.data_stats["media_dikirim"] += len(message.attachments)

        if message.content:
            emoji_kustom = re.findall(r"<a?:(\w+):(\d+)>", message.content)
            for nama_emoji, id_emoji in emoji_kustom:
                self.data_stats["emoji_digunakan"][f"<:{nama_emoji}:{id_emoji}>"] += 1

        self._simpan_statistik()

    @commands.Cog.listener()
    async def on_message_delete(self, message:discord.Message):
        if message.guild:
            self._tambah_stat("pesan_dihapus")

    @commands.Cog.listener()
    async def on_bulk_message_delete(self, messages:list[discord.Message]):
        if messages and messages[0].guild:
            self._tambah_stat("pesan_dihapus", len(messages))

    @commands.Cog.listener()
    async def on_message_edit(self, before:discord.Message, after:discord.Message):
        if before.guild and before.content != after.content:
            self._tambah_stat("pesan_diedit")

    @commands.Cog.listener()
    async def on_reaction_add(self, reaction:discord.Reaction, user:discord.User|discord.Member):
        if reaction.message.guild and not user.bot:
            self.data_stats["reaction_ditambahkan"] += 1
            if isinstance(reaction.emoji, (discord.Emoji, discord.PartialEmoji)):
                self.data_stats["emoji_digunakan"][str(reaction.emoji)] += 1
            self._simpan_statistik()

    @commands.Cog.listener()
    async def on_member_join(self, member:discord.Member):
        self._tambah_stat("member_bergabung")

    @commands.Cog.listener()
    async def on_member_remove(self, member:discord.Member):
        self._tambah_stat("member_keluar")

    @commands.Cog.listener()
    async def on_member_ban(self, guild:discord.Guild, user:discord.User|discord.Member):
        self._tambah_stat("member_diban")

    @commands.Cog.listener()
    async def on_user_update(self, before:discord.User, after:discord.User):
        if before.name != after.name:
            self._tambah_stat("member_ubah_username")

    @commands.Cog.listener()
    async def on_member_update(self, before:discord.Member, after:discord.Member):
        if before.guild_avatar != after.guild_avatar:
            self.data_stats["member_ubah_foto_profil"] += 1
        if before.guild_banner != after.guild_banner:
            self.data_stats["member_ubah_foto_sampul"] += 1
        if before.nick != after.nick:
            self.data_stats["member_ubah_nickname"] += 1
        if before.roles != after.roles:
            self.data_stats["member_berganti_role"] += 1
        if before.timed_out_until != after.timed_out_until and after.timed_out_until is not None:
            self.data_stats["member_timeout"] += 1
        if before.premium_since is None and after.premium_since is not None:
            self.data_stats["member_boost_server"] += 1

        self._simpan_statistik()

    @commands.Cog.listener()
    async def on_voice_state_update(self, member:discord.Member, before:discord.VoiceState, after:discord.VoiceState):
        if before.channel != after.channel:
            if before.channel is None and after.channel:
                self.data_stats["vc_bergabung"] += 1
            elif after.channel is None and before.channel:
                self.data_stats["vc_keluar"] += 1

        if before.self_stream != after.self_stream and after.self_stream:
            self.data_stats["vc_share_screen"] += 1

        self._simpan_statistik()

    @commands.Cog.listener()
    async def on_guild_channel_create(self, channel:discord.abc.GuildChannel):
        self._tambah_stat("channel_dibuat")

    @commands.Cog.listener()
    async def on_guild_channel_update(self, before:discord.abc.GuildChannel, after:discord.abc.GuildChannel):
        if before.name != after.name:
            self._tambah_stat("channel_nama_diubah")

    @commands.Cog.listener()
    async def on_guild_channel_delete(self, channel:discord.abc.GuildChannel):
        self._tambah_stat("channel_dihapus")

    @commands.Cog.listener()
    async def on_guild_role_create(self, role:discord.Role):
        self._tambah_stat("role_dibuat")

    @commands.Cog.listener()
    async def on_guild_role_update(self, before:discord.Role, after:discord.Role):
        if before.permissions != after.permissions or before.name != after.name or before.color != after.color:
            self._tambah_stat("role_pengaturan_diubah")

    @commands.Cog.listener()
    async def on_guild_update(self, before:discord.Guild, after:discord.Guild):
        if before.name != after.name:
            self.data_stats["server_nama_diubah"] += 1
        if before.icon != after.icon:
            self.data_stats["server_foto_diubah"] += 1
        if before.banner != after.banner:
            self.data_stats["server_sampul_diubah"] += 1

        self._simpan_statistik()

    @commands.Cog.listener()
    async def on_webhooks_update(self, channel:discord.abc.GuildChannel):
        self._tambah_stat("webhook_diubah")

    @commands.Cog.listener()
    async def on_integration_create(self, integration:discord.Integration):
        self._tambah_stat("integrasi_dibuat")

    @commands.Cog.listener()
    async def on_guild_emojis_update(self, guild:discord.Guild, before:list[discord.Emoji], after:list[discord.Emoji]):
        if len(after) > len(before):
            self._tambah_stat("emoji_ditambahkan", len(after) - len(before))
        elif len(before) > len(after):
            self._tambah_stat("emoji_dihapus", len(before) - len(after))

    @commands.Cog.listener()
    async def on_thread_create(self, thread:discord.Thread):
        self._tambah_stat("thread_dibuat")

    @commands.Cog.listener()
    async def on_thread_delete(self, thread:discord.Thread):
        self._tambah_stat("thread_dihapus")

    @commands.Cog.listener()
    async def on_thread_update(self, before:discord.Thread, after:discord.Thread):
        if before.archived != after.archived and after.archived:
            self.data_stats["thread_diarsipkan"] += 1
        if before.name != after.name:
            self.data_stats["thread_nama_diubah"] += 1

        self._simpan_statistik()

    @commands.Cog.listener()
    async def on_scheduled_event_create(self, event:discord.ScheduledEvent):
        self._tambah_stat("event_dibuat")

    @commands.Cog.listener()
    async def on_scheduled_event_delete(self, event:discord.ScheduledEvent):
        self._tambah_stat("event_dibatalkan")

    def catat_durasi_vc(self, detik: int):
        self.data_stats["vc_durasi_total"] += detik
        self.data_stats["vc_jumlah_sesi"] += 1
        self._simpan_statistik()

    # ==========================================
    # TUGAS OTOMATIS: PENGIRIM LAPORAN 00.00 WIB
    # ==========================================

    @tasks.loop(time=time(hour=0, minute=0, second=0, tzinfo=WIB))
    async def tugas_laporan_harian(self):
        kemarin = datetime.now(WIB) - timedelta(days=1)
        hari_str = HARI_INDONESIA.get(kemarin.strftime("%A"), kemarin.strftime("%A"))
        tgl_str = kemarin.strftime("%d")
        bulan_str = BULAN_INDONESIA.get(kemarin.month, kemarin.strftime("%B"))
        tahun_str = kemarin.strftime("%Y")

        judul = f"Laporan Stats Harian Server\n[{hari_str}, {tgl_str} {bulan_str} {tahun_str}]"
        embed = discord.Embed(title=judul, color=discord.Color.from_str("#D675C1"))

        # ------------------------------------
        # FIELD 1: Aktivitas Chat
        # ------------------------------------
        poin_f1 = []
        if self.data_stats["pesan_dikirim"] > 0:
            poin_f1.append(f"• {self.data_stats['pesan_dikirim']} pesan dikirim")
        if self.data_stats["pesan_dihapus"] > 0:
            poin_f1.append(f"• {self.data_stats['pesan_dihapus']} pesan dihapus")
        if self.data_stats["pesan_diedit"] > 0:
            poin_f1.append(f"• {self.data_stats['pesan_diedit']} pesan diedit")
        if self.data_stats["media_dikirim"] > 0:
            poin_f1.append(f"• {self.data_stats['media_dikirim']} media/attachment dikirim")

        if poin_f1:
            embed.add_field(name="Aktivitas Chat", value="\n".join(poin_f1), inline=True)

        # ------------------------------------
        # FIELD 2: Reaction dan Emoji
        # ------------------------------------
        poin_f2 = []
        total_emoji = sum(self.data_stats["emoji_digunakan"].values())
        if total_emoji > 0:
            poin_f2.append(f"• {total_emoji} emoji digunakan")
            top_emoji, top_count = self.data_stats["emoji_digunakan"].most_common(1)[0]
            poin_f2.append(f"• {top_emoji} paling banyak digunakan hari ini ({top_count}x)")
        if self.data_stats["reaction_ditambahkan"] > 0:
            poin_f2.append(f"• {self.data_stats['reaction_ditambahkan']} reaction ditambahkan")

        if poin_f2:
            embed.add_field(name="Reaction dan Emoji", value="\n".join(poin_f2), inline=True)

        # ------------------------------------
        # FIELD 3: Keanggotaan
        # ------------------------------------
        poin_f3 = []
        if self.data_stats["member_bergabung"] > 0:
            poin_f3.append(f"• {self.data_stats['member_bergabung']} member bergabung")
        if self.data_stats["member_keluar"] > 0:
            poin_f3.append(f"• {self.data_stats['member_keluar']} member keluar")
        if self.data_stats["member_dikick"] > 0:
            poin_f3.append(f"• {self.data_stats['member_dikick']} member di-kick")
        if self.data_stats["member_diban"] > 0:
            poin_f3.append(f"• {self.data_stats['member_diban']} member di-ban")
        if self.data_stats["member_timeout"] > 0:
            poin_f3.append(f"• {self.data_stats['member_timeout']} member di-timeout")
        if self.data_stats["member_ubah_username"] > 0:
            poin_f3.append(f"• {self.data_stats['member_ubah_username']} member mengubah username")
        if self.data_stats["member_ubah_foto_profil"] > 0:
            poin_f3.append(f"• {self.data_stats['member_ubah_foto_profil']} member mengubah foto profil dalam server")
        if self.data_stats["member_ubah_foto_sampul"] > 0:
            poin_f3.append(f"• {self.data_stats['member_ubah_foto_sampul']} member mengubah foto sampul dalam server")
        if self.data_stats["member_ubah_nickname"] > 0:
            poin_f3.append(f"• {self.data_stats['member_ubah_nickname']} member berganti nickname dalam server")
        if self.data_stats["member_berganti_role"] > 0:
            poin_f3.append(f"• {self.data_stats['member_berganti_role']} member berganti role")
        if self.data_stats["member_boost_server"] > 0:
            poin_f3.append(f"• {self.data_stats['member_boost_server']} member mem-boost server")

        if poin_f3:
            embed.add_field(name="Keanggotaan", value="\n".join(poin_f3), inline=True)

        # ------------------------------------
        # FIELD 4: Aktivitas Voice
        # ------------------------------------
        poin_f4 = []
        if self.data_stats["vc_bergabung"] > 0:
            poin_f4.append(f"• {self.data_stats['vc_bergabung']} member bergabung di VC")
        if self.data_stats["vc_keluar"] > 0:
            poin_f4.append(f"• {self.data_stats['vc_keluar']} member keluar dari VC")
        if self.data_stats["vc_jumlah_sesi"] > 0:
            rata_rata = self.data_stats["vc_durasi_total"] / self.data_stats["vc_jumlah_sesi"]
            poin_f4.append(f"• {self.format_durasi(rata_rata)} rata-rata waktu member dalam VC")
        if self.data_stats["vc_share_screen"] > 0:
            poin_f4.append(f"• {self.data_stats['vc_share_screen']} member men-share screen")

        if poin_f4:
            embed.add_field(name="Aktivitas Voice", value="\n".join(poin_f4), inline=True)

        # ------------------------------------
        # FIELD 5: Pengaturan Server
        # ------------------------------------
        poin_f5 = []
        if self.data_stats["channel_dibuat"] > 0:
            poin_f5.append(f"• {self.data_stats['channel_dibuat']} channel dibuat")
        if self.data_stats["channel_nama_diubah"] > 0:
            poin_f5.append(f"• {self.data_stats['channel_nama_diubah']} nama channel diubah")
        if self.data_stats["channel_dihapus"] > 0:
            poin_f5.append(f"• {self.data_stats['channel_dihapus']} channel dihapus")
        if self.data_stats["role_dibuat"] > 0:
            poin_f5.append(f"• {self.data_stats['role_dibuat']} role dibuat")
        if self.data_stats["role_pengaturan_diubah"] > 0:
            poin_f5.append(f"• {self.data_stats['role_pengaturan_diubah']} pengaturan role diubah")
        if self.data_stats["server_nama_diubah"] > 0:
            poin_f5.append(f"• {self.data_stats['server_nama_diubah']} nama server diubah")
        if self.data_stats["server_foto_diubah"] > 0:
            poin_f5.append(f"• {self.data_stats['server_foto_diubah']} foto server diubah")
        if self.data_stats["server_sampul_diubah"] > 0:
            poin_f5.append(f"• {self.data_stats['server_sampul_diubah']} foto sampul server diubah")
        if self.data_stats["webhook_diubah"] > 0:
            poin_f5.append(f"• {self.data_stats['webhook_diubah']} perubahan webhook channel")
        if self.data_stats["integrasi_dibuat"] > 0:
            poin_f5.append(f"• {self.data_stats['integrasi_dibuat']} integrasi aplikasi dibuat")
        if self.data_stats["emoji_ditambahkan"] > 0:
            poin_f5.append(f"• {self.data_stats['emoji_ditambahkan']} emoji ditambahkan")
        if self.data_stats["emoji_dihapus"] > 0:
            poin_f5.append(f"• {self.data_stats['emoji_dihapus']} emoji dihapus")
        if self.data_stats["thread_dibuat"] > 0:
            poin_f5.append(f"• {self.data_stats['thread_dibuat']} thread dibuat")
        if self.data_stats["thread_dihapus"] > 0:
            poin_f5.append(f"• {self.data_stats['thread_dihapus']} thread dihapus")
        if self.data_stats["thread_diarsipkan"] > 0:
            poin_f5.append(f"• {self.data_stats['thread_diarsipkan']} thread diarsipkan")
        if self.data_stats["thread_nama_diubah"] > 0:
            poin_f5.append(f"• {self.data_stats['thread_nama_diubah']} nama thread diubah")
        if self.data_stats["event_dibuat"] > 0:
            poin_f5.append(f"• {self.data_stats['event_dibuat']} event server dibuat")
        if self.data_stats["event_dibatalkan"] > 0:
            poin_f5.append(f"• {self.data_stats['event_dibatalkan']} event server dibatalkan")
        
        if poin_f5:
            embed.add_field(name="Pengaturan Server", value="\n".join(poin_f5), inline=True)
        
        if len(embed.fields) > 0:
            for guild in self.bot.guilds:
                channel = guild.get_channel(ID_CHANNEL_LOG)
                if isinstance(channel, discord.TextChannel):
                    icon_url = guild.icon.url if guild.icon else None
                    embed.set_author(name=guild.name, icon_url=icon_url)
                    embed.set_thumbnail(url=icon_url)
                    
                    try:
                        await channel.send(embed=embed)
                    except discord.HTTPException:
                        pass
        
        self._reset_statistik() #reset buat besok
    
    @tugas_laporan_harian.before_loop
    async def sebelum_tugas_laporan_harian(self):
        await self.bot.wait_until_ready()


async def setup(bot:commands.Bot):
    await bot.add_cog(StatistikHarian(bot))