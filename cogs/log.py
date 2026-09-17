import asyncio
import json
import os
import secrets
import sys
import uuid
from datetime import datetime
from typing import Any

import discord
from discord import app_commands
from discord.ext import commands

BINROOM = 1537905133311230112
LOG_CHANNEL_ID = 1542006154744565870
CHANNEL_PENGECUALIAN = 1498144198577356831
WARNA_DISCORD = discord.Color.from_str("#5662f6")
WARNA_AIKA = discord.Color.from_str("#D675C1")
OWNER_ID = 1524951093560213638


class ServerLogger(commands.Cog):
    def __init__(self, bot:commands.Bot) -> None:
        self.bot = bot
        self._has_started = False
        self.bot.tree.on_error = self.on_app_command_error
        
        self.data_file = os.path.join("data", "vc_duration.json")
        self.voice_states: dict[int, datetime] = {}
        self.streaming_states: dict[int, datetime] = {}
        self.vc_empty_states: dict[int, datetime] = {}
    
    async def cog_load(self) -> None:
        await self._load_durations()
    
    async def _load_durations(self) -> None:
        if not os.path.exists(self.data_file):
            return
        
        def _read() -> dict[str, Any]:
            try:
                with open(self.data_file, "r", encoding="utf-8") as f:
                    return json.load(f)
            except (json.JSONDecodeError, OSError):
                return {}
        
        data = await asyncio.to_thread(_read)
        for k, v in data.get("voice_states", {}).items():
            self.voice_states[int(k)] = datetime.fromisoformat(v)
        for k, v in data.get("streaming_states", {}).items():
            self.streaming_states[int(k)] = datetime.fromisoformat(v)
        for k, v in data.get("vc_empty_states", {}).items():
            self.vc_empty_states[int(k)] = datetime.fromisoformat(v)
    
    async def _save_durations(self) -> None:
        data = {
            "voice_states": {str(k): v.isoformat() for k, v in self.voice_states.items()},
            "streaming_states": {str(k): v.isoformat() for k, v in self.streaming_states.items()},
            "vc_empty_states": {str(k): v.isoformat() for k, v in self.vc_empty_states.items()},
        }
        
        def _write() -> None:
            os.makedirs(os.path.dirname(self.data_file), exist_ok=True)
            with open(self.data_file, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=4)
        
        await asyncio.to_thread(_write)
    
    @staticmethod
    def format_durasi(detik:int) -> str:
        detik = max(detik, 0)
        menit = 60
        jam = 60 * menit
        hari = 24 * jam
        minggu = 7 * hari
        bulan = 30 * hari
        tahun = 365 * hari
        
        if detik < menit:
            return f"{detik} detik"
        if detik < jam:
            m, s = divmod(detik, menit)
            return f"{m} menit {s} detik" if s > 0 else f"{m} menit"
        if detik < hari:
            h, m = divmod(detik // menit, 60)
            return f"{h} jam {m} menit" if m > 0 else f"{h} jam"
        if detik < minggu:
            d, h = divmod(detik // jam, 24)
            return f"{d} hari {h} jam" if h > 0 else f"{d} hari"
        if detik < bulan:
            w, d = divmod(detik // hari, 7)
            return f"{w} minggu {d} hari" if d > 0 else f"{w} minggu"
        if detik < tahun:
            mo, w = divmod(detik // minggu, 4)
            return f"{mo} bulan {w} minggu" if w > 0 else f"{mo} bulan"
        
        y, mo = divmod(detik // bulan, 12)
        return f"{y} tahun {mo} bulan" if mo > 0 else f"{y} tahun"
    
    def cog_unload(self) -> None:
        try:
            loop = asyncio.get_running_loop()
            if loop.is_running():
                loop.create_task(self.kirim_log_shutdown())
        except RuntimeError:
            pass
    
    def _buat_footer_sistem(self) -> str:
        version = "v2.0.0"
        stats_cog = self.bot.get_cog("Stats") or self.bot.get_cog("stats")
        if stats_cog and hasattr(stats_cog, "__version__"):
            version = stats_cog.__version__
        elif "stats" in sys.modules and hasattr(sys.modules["stats"], "__version__"):
            version = sys.modules["stats"].__version__
        
        pid = os.getpid()
        hex_hash = secrets.token_hex(2).upper()
        bot_id = self.bot.user.id if self.bot.user else 1533821291134582896
        return f"Aika Core {version}  •  PID-{pid}:{hex_hash}  •  ID: {bot_id}"
    
    async def buka_channel_logging(self, guild_or_id:int|discord.Guild) -> discord.TextChannel|None:
        guild = self.bot.get_guild(guild_or_id) if isinstance(guild_or_id, int) else guild_or_id
        if not guild:
            return None
        channel = guild.get_channel(LOG_CHANNEL_ID)
        return channel if isinstance(channel, discord.TextChannel) else None
    
    async def baca_audit_log(self, guild:discord.Guild, action:discord.AuditLogAction, target_id:int|None=None) -> tuple[discord.User|discord.Member|str,str]:
        if not guild.me.guild_permissions.view_audit_log:
            return "Tidak Diketahui (Butuh Izin Audit Log)", "Tidak ada alasan"
        
        try:
            async for entry in guild.audit_logs(limit=5, action=action):
                if target_id is None or (entry.target and entry.target.id == target_id):
                    return entry.user, entry.reason or "Tidak ada alasan"
        except discord.HTTPException:
            pass
        return "Tidak Diketahui / Otomatis System", "Tidak ada alasan"
    
    async def kirim_log_lifecycle(self, title:str, description:str, color:discord.Color|int) -> None:
        for guild in self.bot.guilds:
            channel = await self.buka_channel_logging(guild)
            if channel and self.bot.user:
                embed = discord.Embed(title=title, description=description, color=color)
                embed.set_author(name=self.bot.user.name, icon_url=self.bot.user.display_avatar.url)
                embed.set_thumbnail(url=self.bot.user.display_avatar.url)
                embed.set_footer(text=self._buat_footer_sistem())
                try:
                    await channel.send(embed=embed)
                except discord.HTTPException:
                    pass
    
    async def kirim_log_restart(self) -> None:
        await self.kirim_log_lifecycle("🔄🌸 Aika Akan Restart", "Aika sedang melakukan proses restart.", discord.Color.gold())
    
    async def kirim_log_shutdown(self) -> None:
        await self.kirim_log_lifecycle("🛑🌸 Aika Akan Shutdown", "Sesaat lagi, Aika akan offline.", 0xDD2E44)
    
    # ==========================================
    # 0. AIKA CORE & COMMANDS
    # ==========================================
    @commands.Cog.listener()
    async def on_ready(self) -> None:
        if not self._has_started:
            self._has_started = True
            await self.kirim_log_lifecycle("🟢🌸 Aika Online", "Aika sudah online dan selesai proses inisialisasi.\nSiap melayani server!", 0x76AE58)
        else:
            await self.kirim_log_lifecycle("🔄🌸 Aika Tersambung Kembali", "Sambungan Aika sempat terputus dengan Discord.\nSekarang Aika sudah tersambung kembali dan siap melayani server!", 0x76AE58)
    
    @commands.Cog.listener()
    async def on_resumed(self) -> None:
        await self.kirim_log_lifecycle("➡️🌸 Sesi Aika Dilanjutkan", "Aika berhasil melanjutkan sesi gateway.", 0x76AE58)
    
    @commands.Cog.listener()
    async def on_app_command_completion(self, interaction:discord.Interaction, command:app_commands.Command|app_commands.ContextMenu) -> None:
        if not interaction.guild:
            return
        channel = await self.buka_channel_logging(interaction.guild)
        if not channel:
            return
        
        options_str = ""
        if interaction.data and "options" in interaction.data:
            def extract_opts(opts: list[dict[str, Any]]) -> list[str]:
                res = []
                for o in opts:
                    if "value" in o:
                        res.append(f"{o['name']}:{o['value']}")
                    if "options" in o:
                        res.extend(extract_opts(o["options"]))
                return res
            options_str = " " + " ".join(extract_opts(interaction.data["options"]))
        
        pesan_lengkap = f"/{command.qualified_name}{options_str}"
        delta = (discord.utils.utcnow() - interaction.created_at).total_seconds() * 1000
        waktu_proses = f"{delta:.2f}ms"
        
        footer_parts = [
            f"Interaction: {interaction.id}",
            f"Cmd: {interaction.data['id']}" if interaction.data and "id" in interaction.data else None,
            waktu_proses
        ]
        
        embed = discord.Embed(
            title="🌸 Command Aika Dijalankan",
            description=f"Perintah `/{command.qualified_name}` berhasil dieksekusi di {interaction.channel.mention if interaction.channel else 'DM'}.",
            color=WARNA_AIKA
        )
        embed.add_field(name="User", value=interaction.user.mention, inline=True)
        embed.add_field(name="Pesan Lengkap", value=f"`{pesan_lengkap}`", inline=True)
        embed.set_author(name=interaction.user.name, icon_url=interaction.user.display_avatar.url)
        if self.bot.user:
            embed.set_thumbnail(url=self.bot.user.display_avatar.url)
        embed.set_footer(text="  •  ".join(filter(None, footer_parts)))
        await channel.send(embed=embed)
    
    async def on_app_command_error(self, interaction:discord.Interaction, error:app_commands.AppCommandError) -> None:
        if not interaction.guild:
            return
        channel = await self.buka_channel_logging(interaction.guild)
        if not channel:
            return
        
        cmd_name = interaction.command.qualified_name if interaction.command else "Tidak Diketahui"
        error_id = f"ERR-{uuid.uuid4().hex[:8].upper()}"
        delta = (discord.utils.utcnow() - interaction.created_at).total_seconds() * 1000
        waktu_proses = f"{delta:.2f}ms"
        
        embed = discord.Embed(
            title="🌸🛑 Command Aika Eror",
            description=f"Gagal mengeksekusi perintah `/{cmd_name}` di {interaction.channel.mention if interaction.channel else 'DM'}.\n\n`{error!s}`",
            color=discord.Color.red()
        )
        embed.set_author(name=f"Pengguna: {interaction.user.name}", icon_url=interaction.user.display_avatar.url)
        embed.set_footer(text=f"Error ID: {error_id}  •  Waktu proses: {waktu_proses}")
        if self.bot.user:
            embed.set_thumbnail(url=self.bot.user.display_avatar.url)
        
        owner_id = int(os.getenv("OWNER_ID", str(OWNER_ID)))
        await channel.send(content=f"<@{owner_id}>, command Aika ada yang eror 😨", embed=embed)
    
    @commands.Cog.listener()
    async def on_command_completion(self, ctx:commands.Context) -> None:
        if not ctx.guild or ctx.interaction:
            return
        channel = await self.buka_channel_logging(ctx.guild)
        if not channel:
            return
        
        pesan_lengkap = ctx.message.content or "*Tidak ada teks*"
        waktu_proses = f"{(discord.utils.utcnow() - ctx.message.created_at).total_seconds() * 1000:.2f}ms" if ctx.message else "N/A"
        
        embed = discord.Embed(
            title="🌸 Command Aika Dijalankan",
            description=f"Perintah `{ctx.command.qualified_name if ctx.command else 'Unknown'}` berhasil dieksekusi di {ctx.channel.mention}.",
            color=WARNA_AIKA
        )
        embed.add_field(name="User", value=ctx.author.mention, inline=True)
        embed.add_field(name="Pesan Lengkap", value=f"`{pesan_lengkap}`", inline=True)
        embed.set_author(name=ctx.author.name, icon_url=ctx.author.display_avatar.url)
        if self.bot.user:
            embed.set_thumbnail(url=self.bot.user.display_avatar.url)
        embed.set_footer(text=f"Msg ID: {ctx.message.id}  •  Waktu proses: {waktu_proses}")
        await channel.send(embed=embed)
    
    @commands.Cog.listener()
    async def on_command_error(self, ctx:commands.Context, error:commands.CommandError) -> None:
        if not ctx.guild or ctx.interaction:
            return
        channel = await self.buka_channel_logging(ctx.guild)
        if not channel:
            return
        
        error_id = f"ERR-{uuid.uuid4().hex[:8].upper()}"
        waktu_proses = f"{(discord.utils.utcnow() - ctx.message.created_at).total_seconds() * 1000:.2f}ms" if ctx.message else "N/A"
        cmd_name = ctx.command.qualified_name if ctx.command else "Tidak Diketahui"
        
        embed = discord.Embed(
            title="🌸🛑 Command Aika Eror",
            description=f"Gagal mengeksekusi perintah `{cmd_name}` di {ctx.channel.mention}.\n\n`{error!s}`",
            color=discord.Color.red()
        )
        embed.set_author(name=f"Pengguna: {ctx.author.name}", icon_url=ctx.author.display_avatar.url)
        embed.set_footer(text=f"Error ID: {error_id}  •  Waktu proses: {waktu_proses}")
        if self.bot.user:
            embed.set_thumbnail(url=self.bot.user.display_avatar.url)
        
        owner_id = int(os.getenv("OWNER_ID", str(OWNER_ID)))
        await channel.send(content=f"<@{owner_id}>, command Aika ada yang eror 😨", embed=embed)
    
    # ==========================================
    # 1. PESAN & ELEMEN CHAT
    # ==========================================
    @commands.Cog.listener()
    async def on_message_edit(self, before:discord.Message, after:discord.Message) -> None:
        if before.content == after.content or not before.guild:
            return
        
        channel = await self.buka_channel_logging(before.guild)
        if not channel:
            return
        
        color = before.author.top_role.color if isinstance(before.author, discord.Member) else WARNA_AIKA
        embed = discord.Embed(
            title="✏️ Pesan Diedit",
            description=f"{before.channel.mention}, {before.author.mention}\n[Lompat ke Pesan]({after.jump_url})",
            color=color
        )
        embed.add_field(name="Sebelum", value=before.content or "*Tidak ada teks*", inline=True)
        embed.add_field(name="Sesudah", value=after.content or "*Tidak ada teks*", inline=True)
        embed.set_author(name=before.author.name, icon_url=before.author.display_avatar.url)
        embed.set_thumbnail(url=before.author.display_avatar.url)
        embed.set_footer(text=f"ID User: {before.author.id}  •  ID Pesan: {before.id}")
        await channel.send(embed=embed)
    
    @commands.Cog.listener()
    async def on_message_delete(self, message:discord.Message) -> None:
        if not message.guild:
            return
        channel = await self.buka_channel_logging(message.guild)
        if not channel:
            return
        
        content = message.content or "*Tidak ada isi teks*"
        attachments = message.attachments
        
        embed = discord.Embed(
            title="🗑️ Pesan Dihapus",
            description=f"{content}\n\n{message.author.mention}, {message.channel.mention}",
            color=discord.Color.red()
        )
        embed.set_author(name=message.author.name, icon_url=message.author.display_avatar.url)
        embed.set_thumbnail(url=message.author.display_avatar.url)
        embed.set_footer(text=f"ID User: {message.author.id}  •  ID Pesan: {message.id}")
        
        if len(attachments) == 1:
            att = attachments[0]
            embed.add_field(name="Lampiran (1)", value=f"[{att.filename}]({att.url})", inline=False)
            
            if att.content_type and att.content_type.startswith("image/"):
                embed.set_image(url=att.proxy_url or att.url)
            
            await channel.send(embed=embed)
            
        elif len(attachments) > 1:
            att_list = [f"[{att.filename}]({att.url})" for att in attachments]
            embed.add_field(
                name=f"Lampiran ({len(attachments)})",
                value="\n".join(att_list),
                inline=False
            )
            
            media_items = [
                discord.MediaGalleryItem(media=att.proxy_url or att.url, spoiler=True)
                for att in attachments
            ]
            
            gallery = discord.ui.MediaGallery(*media_items)
            container = discord.ui.Container(gallery, accent_color=discord.Color.red())
            
            view = discord.ui.LayoutView()
            view.add_item(container)
            
            await channel.send(embed=embed)
            await channel.send(view=view)
            
        else:
            await channel.send(embed=embed)
    
    @commands.Cog.listener()
    async def on_bulk_message_delete(self, messages:list[discord.Message]) -> None:
        if not messages or not messages[0].guild:
            return
        
        guild = messages[0].guild
        channel = await self.buka_channel_logging(guild)
        if not channel:
            return
        
        actor, reason = await self.baca_audit_log(guild, discord.AuditLogAction.message_bulk_delete)
        pelaksana = f" oleh {actor.mention}" if isinstance(actor, (discord.User, discord.Member)) else ""
        
        embed = discord.Embed(
            title="🗑️🧻 Penghapusan Pesan Masal (Bulk Delete)",
            description=f"Sebanyak __{len(messages)} pesan__ telah dihapus di {messages[0].channel.mention}{pelaksana}.",
            color=discord.Color.red()
        )
        if "Tidak ada alasan" not in reason:
            embed.add_field(name="Alasan", value=reason, inline=True)
        
        if isinstance(actor, (discord.User, discord.Member)):
            embed.set_author(name=actor.name, icon_url=actor.display_avatar.url)
            embed.set_thumbnail(url=actor.display_avatar.url)
            embed.set_footer(text=f"User ID: {actor.id}  •  Channel ID: {messages[0].channel.id}")
        else:
            embed.set_footer(text=f"Channel ID: {messages[0].channel.id}")
        
        await channel.send(embed=embed)
    
    @commands.Cog.listener()
    async def on_raw_reaction_remove(self, payload:discord.RawReactionActionEvent) -> None:
        if not payload.guild_id:
            return
        
        channel = await self.buka_channel_logging(payload.guild_id)
        if not channel:
            return
        
        guild = self.bot.get_guild(payload.guild_id)
        user = guild.get_member(payload.user_id) if guild else None
        user_mention = user.mention if user else f"<@{payload.user_id}>"
        
        if payload.emoji.is_custom_emoji():
            thumbnail = payload.emoji.url
            reaksi = f"'{payload.emoji}' `:{payload.emoji.name}:`"
            info_tambahan = f"  •  ID Emoji: {payload.emoji.id}"
        else:
            codepoints = "-".join(f"{ord(char):x}" for char in str(payload.emoji))
            thumbnail = f"https://cdn.jsdelivr.net/gh/twitter/twemoji@latest/assets/72x72/{codepoints}.png"
            reaksi = f"'{payload.emoji}'"
            info_tambahan = f"  •  ID User: {payload.user_id}"
        
        user_color = user.color if user else WARNA_AIKA
        embed = discord.Embed(
            title="➖ Reaction Dihapus",
            description=f"{user_mention} menghapus reaksi {reaksi} dari pesan di <#{payload.channel_id}>.",
            color=user_color
        ).set_footer(text=f"ID Pesan: {payload.message_id}{info_tambahan}")
        
        if user:
            embed.set_author(name=user.name, icon_url=user.display_avatar.url)
        embed.set_thumbnail(url=thumbnail)
        await channel.send(embed=embed)
    
    @commands.Cog.listener()
    async def on_raw_reaction_clear(self, payload:discord.RawReactionClearEvent) -> None:
        if not payload.guild_id:
            return
        channel = await self.buka_channel_logging(payload.guild_id)
        if not channel:
            return
        
        embed = discord.Embed(
            title="🗑️🚫 Semua Reaksi Dihapus",
            description=f"Semua reaksi telah dibersihkan dari pesan di <#{payload.channel_id}>.",
            color=discord.Color.red()
        )
        embed.set_footer(text=f"ID Channel: {payload.channel_id}  •  ID Pesan: {payload.message_id}")
        await channel.send(embed=embed)
    
    @commands.Cog.listener()
    async def on_reaction_add(self, reaction:discord.Reaction, user:discord.Member|discord.User) -> None:
        if not reaction.message.guild:
            return
        channel = await self.buka_channel_logging(reaction.message.guild)
        if not channel:
            return
        
        if isinstance(reaction.emoji, (discord.Emoji, discord.PartialEmoji)):
            thumbnail = reaction.emoji.url
            reaksi = f"'{reaction.emoji}' `:{reaction.emoji.name}:`"
            info_tambahan = f"  •  ID Emoji: {reaction.emoji.id}"
        else:
            codepoints = "-".join(f"{ord(char):x}" for char in str(reaction.emoji))
            thumbnail = f"https://cdn.jsdelivr.net/gh/twitter/twemoji@latest/assets/72x72/{codepoints}.png"
            reaksi = f"'{reaction.emoji}'"
            info_tambahan = f"  •  ID User: {user.id}"
        
        user_color = user.color if isinstance(user, discord.Member) else WARNA_AIKA
        embed = discord.Embed(
            title="➕ Reaction Ditambahkan",
            description=f"{user.mention} menambahkan reaksi {reaksi} pada pesan di {reaction.message.channel.mention}.",
            color=user_color
        ).set_footer(text=f"ID Pesan: {reaction.message.id}{info_tambahan}")
        embed.set_author(name=user.name, icon_url=user.display_avatar.url)
        embed.set_thumbnail(url=thumbnail)
        await channel.send(embed=embed)
    
    # ==========================================
    # 2. ANGGOTA & PROFIL
    # ==========================================
    @commands.Cog.listener()
    async def on_member_join(self, member:discord.Member) -> None:
        channel = await self.buka_channel_logging(member.guild)
        if not channel:
            return
        
        if member.bot:
            actor, reason = await self.baca_audit_log(member.guild, discord.AuditLogAction.bot_add, member.id)
            pelaksana = f" oleh {actor.mention}" if isinstance(actor, (discord.User, discord.Member)) else ""
            id_pelaksana = f"  •  ID User: {actor.id}" if isinstance(actor, (discord.User, discord.Member)) else ""
            
            embed = discord.Embed(
                title="📥🤖 Bot Bergabung ke Server",
                description=f"Bot {member.mention} telah ditambahkan ke server{pelaksana}.",
                color=discord.Color.green()
            )
            if "Tidak ada alasan" not in reason:
                embed.add_field(name="Alasan", value=reason, inline=True)
            embed.set_footer(text=f"ID Bot: {member.id}{id_pelaksana}")
        else:
            embed = discord.Embed(
                title="📥🚪👤 Member Bergabung",
                description=f"{member.mention} telah bergabung ke server.",
                color=discord.Color.green()
            )
            embed.set_footer(text=f"ID User: {member.id}")
        
        embed.set_author(name=str(member), icon_url=member.display_avatar.url)
        embed.set_thumbnail(url=member.display_avatar.url)
        
        await channel.send(embed=embed)
    
    @commands.Cog.listener()
    async def on_member_remove(self, member:discord.Member) -> None:
        channel = await self.buka_channel_logging(member.guild)
        if not channel:
            return
        
        kick_entry = None
        if member.guild.me.guild_permissions.view_audit_log:
            try:
                async for entry in member.guild.audit_logs(limit=3, action=discord.AuditLogAction.kick):
                    if entry.target and entry.target.id == member.id:
                        time_diff = (discord.utils.utcnow() - entry.created_at).total_seconds()
                        if time_diff < 10:
                            kick_entry = entry
                            break
            except discord.HTTPException:
                pass
        
        if kick_entry:
            cog_stats = self.bot.get_cog("StatistikHarian")
            if cog_stats and hasattr(cog_stats, "_tambah_stat"):
                cog_stats._tambah_stat("member_dikick")
            
            actor = kick_entry.user
            reason = kick_entry.reason or "Tidak ada alasan"
            
            embed = discord.Embed(
                title="📤🦵🏻👤 Member Di-kick",
                description=f"{member.mention} telah dikeluarkan dari server.",
                color=discord.Color.red()
            )
            embed.add_field(name="Di-kick oleh", value=actor.mention if actor else "Tidak Diketahui", inline=True)
            embed.add_field(name="Alasan", value=reason, inline=True)
        else:
            embed = discord.Embed(
                title="📤🚪👤 Member Keluar",
                description=f"{member.mention} meninggalkan server.",
                color=discord.Color.red()
            )
        
        embed.set_author(name=str(member), icon_url=member.display_avatar.url)
        embed.set_thumbnail(url=member.display_avatar.url)
        embed.set_footer(text=f"ID User: {member.id}")
        await channel.send(embed=embed)
    
    @commands.Cog.listener()
    async def on_user_update(self, before:discord.User, after:discord.User) -> None:
        for guild in self.bot.guilds:
            if guild.get_member(after.id):
                channel = await self.buka_channel_logging(guild)
                if not channel:
                    continue
                
                if before.name != after.name:
                    embed = discord.Embed(
                        title="✏️🏷️ Username Berubah",
                        description=f"User {after.mention} memperbarui username akun global.",
                        color=WARNA_AIKA
                    )
                    embed.add_field(name="Sebelum", value=f"`@{before.name}`", inline=True)
                    embed.add_field(name="Sesudah", value=f"`@{after.name}`", inline=True)
                    embed.set_author(name=str(after), icon_url=after.display_avatar.url)
                    embed.set_thumbnail(url=after.display_avatar.url)
                    embed.set_footer(text=f"ID User: {after.id}")
                    await channel.send(embed=embed)
    
    @commands.Cog.listener()
    async def on_invite_create(self, invite:discord.Invite) -> None:
        if not invite.guild:
            return
        channel = await self.buka_channel_logging(invite.guild)
        if not channel:
            return
        
        inviter = invite.inviter.mention if invite.inviter else "Tidak Diketahui"
        max_uses = "Tidak terbatas" if invite.max_uses == 0 else f"{invite.max_uses} kali"
        max_age = "Tidak pernah" if invite.max_age == 0 else f"{invite.max_age // 3600} jam"
        
        embed = discord.Embed(
            title="🔗 Link Invite Dibuat",
            color=discord.Color.green()
        )
        embed.add_field(name="Kode Invite", value=invite.code, inline=True)
        embed.add_field(name="Tujuan", value=invite.channel.mention if invite.channel else "N/A", inline=True)
        embed.add_field(name="Dibuat oleh", value=inviter, inline=True)
        embed.add_field(name="Batas Penggunaan", value=max_uses, inline=True)
        embed.add_field(name="Kedaluwarsa", value=max_age, inline=True)
        
        embed.set_author(name=invite.inviter.name, icon_url=invite.inviter.display_avatar.url)
        embed.set_thumbnail(url=invite.guild.icon.url)
        embed.set_footer(text=f"Inviter ID: {invite.inviter.id}  •  Server ID: {invite.guild.id}")
        await channel.send(embed=embed)
    
    @commands.Cog.listener()
    async def on_invite_delete(self, invite:discord.Invite) -> None:
        if not invite.guild:
            return
        channel = await self.buka_channel_logging(invite.guild)
        if not channel:
            return
        
        inviter_name = invite.inviter.name if invite.inviter else "Tidak Diketahui"
        inviter_icon = invite.inviter.display_avatar.url if invite.inviter else (invite.guild.icon.url if invite.guild.icon else None)
        inviter_id = invite.inviter.id if invite.inviter else "N/A"
        
        embed = discord.Embed(
            title="🔗🗑️ Link Invite Dihapus",
            description=f"Kode Invite `{invite.code}` di channel {invite.channel.mention if invite.channel else 'N/A'} telah dihapus.",
            color=discord.Color.red()
        )
        embed.set_author(name=inviter_name, icon_url=inviter_icon)
        if invite.guild.icon:
            embed.set_thumbnail(url=invite.guild.icon.url)
        embed.set_footer(text=f"Inviter ID: {inviter_id}  •  Server ID: {invite.guild.id}")
        await channel.send(embed=embed)
    
    @commands.Cog.listener()
    async def on_member_update(self, before:discord.Member, after:discord.Member) -> None:
        channel = await self.buka_channel_logging(after.guild)
        if not channel:
            return
        
        member_color = after.top_role.color
        
        if before.guild_banner != after.guild_banner:
            embed = discord.Embed(
                title="🖼️ Foto Sampul Dalam Server Diperbarui",
                description=f"{after.mention} memperbarui foto sambil khusus server ini.",
                color=member_color if member_color.value != 0 else WARNA_AIKA
            )
            embed.set_author(name=str(after), icon_url=after.display_avatar.url)
            
            if before.guild_banner:
                embed.add_field(name="Foto Sampul Server Lama", value=f"[Lihat Gambar]({before.guild_avatar.url})", inline=True)
            else:
                embed.add_field(name="Sebelum", value="*Menggunakan sampul global*", inline=True)
            
            if after.guild_banner:
                embed.set_thumbnail(url=after.guild_avatar.url)
                embed.add_field(name="Foto Sampul Server Baru", value=f"[Lihat Gambar]({after.guild_banner.url})", inline=True)
            else:
                embed.set_thumbnail(url=after.guild_avatar.url)
                embed.add_field(name="Sesudah", value="*Di-reset ke sampul global*", inline=True)
            
            embed.set_footer(text=f"ID User: {after.id}")
            await channel.send(embed=embed)
        
        if before.guild_avatar != after.guild_avatar:
            embed = discord.Embed(
                title="🖼️ Foto Profil Dalam Server Diperbarui",
                description=f"{after.mention} memperbarui foto profil khusus server ini.",
                color=member_color if member_color.value != 0 else WARNA_AIKA
            )
            embed.set_author(name=str(after), icon_url=after.display_avatar.url)
            
            if before.guild_avatar:
                embed.add_field(name="Foto Profil Server Lama", value=f"[Lihat Gambar]({before.guild_avatar.url})", inline=True)
            else:
                embed.add_field(name="Sebelum", value="*Menggunakan avatar global*", inline=True)
            
            if after.guild_avatar:
                embed.set_thumbnail(url=after.guild_avatar.url)
                embed.add_field(name="Foto Profil Server Baru", value=f"[Lihat Gambar]({after.guild_avatar.url})", inline=True)
            else:
                embed.set_thumbnail(url=after.display_avatar.url)
                embed.add_field(name="Sesudah", value="*Di-reset ke avatar global*", inline=True)
            
            embed.set_footer(text=f"ID User: {after.id}")
            await channel.send(embed=embed)
        
        if before.nick != after.nick:
            embed = discord.Embed(title="🏷️✏️ Nickname Berubah", description=after.mention, color=member_color)
            embed.set_author(name=str(after), icon_url=after.display_avatar.url)
            embed.set_thumbnail(url=after.display_avatar.url)
            embed.add_field(name="Sebelum", value=before.nick or "*Nama Asli*", inline=True)
            embed.add_field(name="Sesudah", value=after.nick or "*Nama Asli*", inline=True)
            embed.set_footer(text=f"ID User: {after.id}")
            await channel.send(embed=embed)
        
        if before.roles != after.roles:
            added = [role.mention for role in after.roles if role not in before.roles]
            removed = [role.mention for role in before.roles if role not in after.roles]
            actor, reason = await self.baca_audit_log(after.guild, discord.AuditLogAction.member_role_update, after.id)
            
            if added:
                embed = discord.Embed(
                    title="➕🏷️ Role Ditambahkan",
                    description=f"{after.mention} mendapatkan role {', '.join(added)}.",
                    color=discord.Color.green()
                )
                embed.set_author(name=after.name, icon_url=after.display_avatar.url)
                embed.set_thumbnail(url=after.display_avatar.url)
                if "Tidak ada alasan" not in reason:
                    embed.add_field(name="Alasan", value=reason, inline=True)
                if actor and isinstance(actor, discord.User) and actor.id != after.id:
                    embed.add_field(name="Diubah oleh", value=actor.mention, inline=True)
                role_id = f"  •  ID Role: {added[0].translate(str.maketrans('', '', '<@&>'))}" if len(added) == 1 else ""
                embed.set_footer(text=f"ID User: {after.id}{role_id}")
                await channel.send(embed=embed)
            
            if removed:
                embed = discord.Embed(
                    title="❌🏷️ Role Dicabut",
                    description=f"Role {', '.join(removed)} dicabut dari {after.mention}.",
                    color=discord.Color.red()
                )
                embed.set_author(name=after.name, icon_url=after.display_avatar.url)
                embed.set_thumbnail(url=after.display_avatar.url)
                if "Tidak ada alasan" not in reason:
                    embed.add_field(name="Alasan", value=reason, inline=True)
                if actor and isinstance(actor, discord.User) and actor.id != after.id:
                    embed.add_field(name="Diubah oleh", value=actor.mention, inline=True)
                role_id = f"  •  ID Role: {removed[0].translate(str.maketrans('', '', '<@&>'))}" if len(removed) == 1 else ""
                embed.set_footer(text=f"ID User: {after.id}{role_id}")
                await channel.send(embed=embed)
        
        if before.timed_out_until != after.timed_out_until:
            embed = None
            if after.timed_out_until and (before.timed_out_until is None or after.timed_out_until > before.timed_out_until):
                actor, reason = await self.baca_audit_log(after.guild, discord.AuditLogAction.member_update, after.id)
                actor_mention = actor.mention if isinstance(actor, (discord.User, discord.Member)) else str(actor)
                
                embed = discord.Embed(
                    title="🕑⚠️👤 Member Di-timeout",
                    description=f"{after.mention} telah di-timeout.",
                    color=discord.Color.gold()
                )
                embed.add_field(name="Penindak", value=actor_mention, inline=True)
                embed.add_field(name="Berlaku hingga", value=f"<t:{int(after.timed_out_until.timestamp())}:D>", inline=True)
                embed.add_field(name="Alasan", value=reason, inline=True)
                
            elif before.timed_out_until and after.timed_out_until is None:
                now = discord.utils.utcnow()
                if before.timed_out_until <= now:
                    embed = discord.Embed(
                        title="🕑✅👤 Timeout Selesai",
                        description=f"Masa timeout untuk {after.mention} telah selesai secara otomatis.",
                        color=discord.Color.green()
                    )
                else:
                    actor, reason = await self.baca_audit_log(after.guild, discord.AuditLogAction.member_update, after.id)
                    actor_mention = actor.mention if isinstance(actor, (discord.User, discord.Member)) else str(actor)
                    
                    embed = discord.Embed(
                        title="🕑✅👤 Timeout Dihapus",
                        description=f"Status timeout untuk {after.mention} telah dicabut oleh {actor_mention}.",
                        color=discord.Color.green()
                    )
                    if "Tidak ada alasan" not in reason:
                        embed.add_field(name="Alasan", value=reason, inline=True)
                
            if embed:
                embed.set_author(name=after.name, icon_url=after.display_avatar.url)
                embed.set_thumbnail(url=after.display_avatar.url)
                embed.set_footer(text=f"ID User: {after.id}")
                await channel.send(embed=embed)
        
        if before.premium_since is None and after.premium_since is not None:
            embed = discord.Embed(
                title="🔮 Server Di-boost",
                description=f"{after.mention} telah nge-boost server!",
                color=discord.Color.from_str("#ff73fa")
            )
            embed.set_author(name=after.name, icon_url=after.display_avatar.url)
            embed.set_thumbnail(url=after.display_avatar.url)
            embed.set_footer(text=f"ID User: {after.id}")
            await channel.send(embed=embed)
    
    # ==========================================
    # 3. VOICE CHANNEL & STREAMING
    # ==========================================
    @commands.Cog.listener()
    async def on_voice_state_update(self, member:discord.Member, before:discord.VoiceState, after:discord.VoiceState) -> None:
        channel = await self.buka_channel_logging(member.guild)
        if not channel:
            return
        
        state_changed = False
        embed_bubar = None
        
        if before.channel != after.channel:
            if before.channel is None and after.channel:  # Join VC
                self.voice_states[member.id] = discord.utils.utcnow()
                state_changed = True
                
                if len(after.channel.members) == 1:
                    self.vc_empty_states[after.channel.id] = discord.utils.utcnow()
                
                embed = discord.Embed(
                    title="📥🔊 Masuk Voice Channel",
                    description=f"{member.mention} bergabung ke {after.channel.mention}",
                    color=discord.Color.green()
                )
                info_tambahan = f"VC ID: {after.channel.id}"
                
            elif after.channel is None and before.channel:  # Leave VC
                waktu_join = self.voice_states.pop(member.id, None)
                state_changed = True
                
                str_durasi = ""
                total_detik = 0
                if waktu_join:
                    total_detik = int((discord.utils.utcnow() - waktu_join).total_seconds())
                    durasi_format = self.format_durasi(total_detik)
                    str_durasi = f"\n-# (Berada di VC selama __{durasi_format}__)"
                
                cog_stats = self.bot.get_cog("StatistikHarian")
                if cog_stats and hasattr(cog_stats, "catat_durasi_vc"):
                    cog_stats.catat_durasi_vc(total_detik)
                
                embed = discord.Embed(
                    title="📤🔊 Keluar Voice Channel",
                    description=f"{member.mention} meninggalkan {before.channel.mention}{str_durasi}",
                    color=discord.Color.red()
                )
                info_tambahan = f"VC ID: {before.channel.id}"
                
                if len(before.channel.members) == 0:  # VC is empty
                    waktu_mulai_vc = self.vc_empty_states.pop(before.channel.id, None)
                    str_durasi_vc = ""
                    if waktu_mulai_vc:
                        total_detik_vc = int((discord.utils.utcnow() - waktu_mulai_vc).total_seconds())
                        durasi_format_vc = self.format_durasi(total_detik_vc)
                        str_durasi_vc = f"\n-# Sempat VC selama __{durasi_format_vc}__"
                    
                    guild_icon = member.guild.icon.url if member.guild.icon else None
                    embed_bubar = discord.Embed(
                        title="🛑🔊 Sesi VC Selesai",
                        description=f"VC {before.channel.mention} `🔊 {before.channel.name}` sudah bubar.{str_durasi_vc}",
                        color=discord.Color.red()
                    )
                    embed_bubar.set_author(name=member.guild.name, icon_url=guild_icon)
                    if guild_icon:
                        embed_bubar.set_thumbnail(url=guild_icon)
                    embed_bubar.set_footer(text=f"VC ID: {before.channel.id}  •  Server ID: {member.guild.id}")
                
            elif before.channel and after.channel:  # Move VC
                if len(before.channel.members) == 0:
                    waktu_mulai_vc = self.vc_empty_states.pop(before.channel.id, None)
                    state_changed = True
                    
                    str_durasi_vc = ""
                    if waktu_mulai_vc:
                        total_detik_vc = int((discord.utils.utcnow() - waktu_mulai_vc).total_seconds())
                        durasi_format_vc = self.format_durasi(total_detik_vc)
                        str_durasi_vc = f"\n-# Sempat VC selama __{durasi_format_vc}__"
                    
                    guild_icon = member.guild.icon.url if member.guild.icon else None
                    temp_bubar = discord.Embed(
                        title="🛑🔊 Sesi VC Selesai",
                        description=f"VC {before.channel.mention} `🔊 {before.channel.name}` sudah bubar.{str_durasi_vc}",
                        color=discord.Color.red()
                    )
                    temp_bubar.set_author(name=member.guild.name, icon_url=guild_icon)
                    if guild_icon:
                        temp_bubar.set_thumbnail(url=guild_icon)
                    temp_bubar.set_footer(text=f"VC ID: {before.channel.id}  •  Server ID: {member.guild.id}")
                    await channel.send(embed=temp_bubar)
                
                if len(after.channel.members) == 1:
                    self.vc_empty_states[after.channel.id] = discord.utils.utcnow()
                    state_changed = True
                
                embed = discord.Embed(
                    title="↔️🔊 Pindah Voice Channel",
                    description=f"{member.mention} berpindah dari {before.channel.mention} ➡️ {after.channel.mention}",
                    color=member.top_role.color
                )
                info_tambahan = f"VC ID: {after.channel.id}"
            else:
                return
            
            embed.set_footer(text=f"ID User: {member.id}  •  {info_tambahan}")
            embed.set_author(name=member.name, icon_url=member.display_avatar.url)
            embed.set_thumbnail(url=member.display_avatar.url)
            await channel.send(embed=embed)
            
            if embed_bubar:
                await channel.send(embed=embed_bubar)
        
        if before.self_stream != after.self_stream:
            str_durasi_strm = ""
            if after.self_stream:
                self.streaming_states[member.id] = discord.utils.utcnow()
                state_text = "✅ memulai screen sharing"
                warna_role = discord.Color.green()
            else:
                waktu_streaming = self.streaming_states.pop(member.id, None)
                state_text = "🛑 menghentikan screen sharing."
                warna_role = discord.Color.red()
                if waktu_streaming:
                    total_detik_strm = int((discord.utils.utcnow() - waktu_streaming).total_seconds())
                    durasi_format_strm = self.format_durasi(total_detik_strm)
                    str_durasi_strm = f"\n-# (Sempat streaming selama __{durasi_format_strm}__)"
            state_changed = True
            
            embed = discord.Embed(
                title="📺🔊 Streaming di VC",
                description=f"{member.mention} {state_text} di {after.channel.mention if after.channel else 'VC'}.{str_durasi_strm}",
                color=warna_role
            )
            embed.set_author(name=member.name, icon_url=member.display_avatar.url)
            embed.set_thumbnail(url=member.display_avatar.url)
            embed.set_footer(text=f"ID User: {member.id}  •  VC ID: {after.channel.id if after.channel else 'N/A'}")
            await channel.send(embed=embed)
        
        if state_changed:
            await self._save_durations()
    
    # ==========================================
    # 4. STRUKTUR SERVER & INTEGRASI
    # ==========================================
    @commands.Cog.listener()
    async def on_guild_channel_create(self, channel:discord.abc.GuildChannel) -> None:
        log_ch = await self.buka_channel_logging(channel.guild)
        if not log_ch:
            return
        
        actor, reason = await self.baca_audit_log(channel.guild, discord.AuditLogAction.channel_create, channel.id)
        actor_mention = actor.mention if isinstance(actor, (discord.User, discord.Member)) else str(actor)
        
        if channel.type == discord.ChannelType.text:
            title_emoji, desc_emoji = "💬", "#"
        elif channel.type == discord.ChannelType.voice:
            title_emoji, desc_emoji = "🔊", "🔊 "
        elif channel.type == discord.ChannelType.stage_voice:
            title_emoji, desc_emoji = "🗼", "🗼 "
        elif channel.type == discord.ChannelType.forum:
            title_emoji, desc_emoji = "💭", "💭 "
        elif channel.type == discord.ChannelType.news:
            title_emoji, desc_emoji = "📢", "📢 "
        elif channel.type == discord.ChannelType.category:
            title_emoji, desc_emoji = "📁", "📁 "
        else:
            title_emoji, desc_emoji = "➕", ""
        
        embed = discord.Embed(
            title=f"{title_emoji} Channel Dibuat",
            description=f"Channel {channel.mention} `{desc_emoji}{channel.name}` telah dibuat oleh {actor_mention}.",
            color=discord.Color.green()
        )
        
        if "Tidak ada alasan" not in reason:
            embed.add_field(name="Alasan", value=reason, inline=True)
        
        embed.set_footer(text=f"ID Channel: {channel.id}")
        if channel.guild.icon:
            embed.set_thumbnail(url=channel.guild.icon.url)
            embed.set_author(name=channel.guild.name, icon_url=channel.guild.icon.url)
        
        await log_ch.send(embed=embed)
    
    @commands.Cog.listener()
    async def on_guild_channel_update(self, before:discord.abc.GuildChannel, after:discord.abc.GuildChannel) -> None:
        if after.id == CHANNEL_PENGECUALIAN:
            return
        
        log_ch = await self.buka_channel_logging(after.guild)
        if not log_ch:
            return
        
        if before.name != after.name:
            actor, reason = await self.baca_audit_log(after.guild, discord.AuditLogAction.channel_update, after.id)
            actor_mention = actor.mention if isinstance(actor, (discord.User, discord.Member)) else str(actor)
            
            if after.type == discord.ChannelType.category:
                embed = discord.Embed(
                    title="📁✏️ Nama Kategori Diperbarui",
                    description=f"Nama kategori **{after.name}** telah diubah oleh {actor_mention}.",
                    color=WARNA_AIKA
                )
            else:
                embed = discord.Embed(
                    title="#️⃣✏️ Nama Channel Diperbarui",
                    description=f"Nama channel {after.mention} telah diubah oleh {actor_mention}.",
                    color=WARNA_AIKA
                )
            
            embed.add_field(name="Sebelum", value=f"`{before.name}`", inline=True)
            embed.add_field(name="Sesudah", value=f"`{after.name}`", inline=True)
            embed.add_field(name="Alasan", value=reason, inline=True)
            
            embed.set_footer(text=f"ID Channel: {after.id}")
            if after.guild.icon:
                embed.set_thumbnail(url=after.guild.icon.url)
            embed.set_author(name=after.guild.name, icon_url=after.guild.icon.url if after.guild.icon else None)
            
            await log_ch.send(embed=embed)
    
    @commands.Cog.listener()
    async def on_guild_channel_delete(self, channel:discord.abc.GuildChannel) -> None:
        log_ch = await self.buka_channel_logging(channel.guild)
        if not log_ch:
            return
        
        actor, reason = await self.baca_audit_log(channel.guild, discord.AuditLogAction.channel_delete, channel.id)
        actor_mention = actor.mention if isinstance(actor, (discord.User, discord.Member)) else str(actor)
        
        embed = discord.Embed(
            title="#️⃣🗑️ Channel Dihapus",
            description=f"Channel `{channel.name}` telah dihapus.",
            color=discord.Color.red()
        )
        embed.add_field(name="Dihapus oleh", value=actor_mention, inline=True)
        embed.add_field(name="Alasan", value=reason, inline=True)
        
        if channel.guild.icon:
            embed.set_thumbnail(url=channel.guild.icon.url)
            embed.set_author(name=channel.guild.name, icon_url=channel.guild.icon.url)
        embed.set_footer(text=f"Channel ID: {channel.id}")
        
        await log_ch.send(embed=embed)
    
    @commands.Cog.listener()
    async def on_guild_role_create(self, role:discord.Role) -> None:
        channel = await self.buka_channel_logging(role.guild)
        if not channel:
            return
        
        actor, reason = await self.baca_audit_log(role.guild, discord.AuditLogAction.role_create, role.id)
        actor_mention = actor.mention if isinstance(actor, (discord.User, discord.Member)) else str(actor)
        
        embed = discord.Embed(
            title="🏷️➕ Role Dibuat",
            description=f"{role.mention} (`@{role.name}`) telah dibuat.",
            color=role.color if role.color.value != 0 else discord.Color.green()
        )
        embed.add_field(name="Dibuat oleh", value=actor_mention, inline=True)
        embed.add_field(name="Alasan", value=reason, inline=True)
        
        if role.guild.icon:
            embed.set_thumbnail(url=role.guild.icon.url)
            embed.set_author(name=role.guild.name, icon_url=role.guild.icon.url)
        embed.set_footer(text=f"ID Role: {role.id}")
        
        await channel.send(embed=embed)
    
    @commands.Cog.listener()
    async def on_guild_role_update(self, before:discord.Role, after:discord.Role) -> None:
        channel = await self.buka_channel_logging(after.guild)
        if not channel:
            return
        
        actor, reason = await self.baca_audit_log(after.guild, discord.AuditLogAction.role_update, after.id)
        actor_mention = actor.mention if isinstance(actor, (discord.User, discord.Member)) else str(actor)
        
        if before.name != after.name or before.color != after.color:
            embed = discord.Embed(
                title="🏷️✏️ Role Diperbarui",
                description=f"{after.mention}",
                color=after.color
            )
            embed.add_field(name="Sebelum", value=before.name, inline=True)
            embed.add_field(name="Sesudah", value=after.name, inline=True)
            embed.add_field(name="Diubah oleh", value=actor_mention, inline=True)
            
            if after.guild.icon:
                embed.set_author(name=after.guild.name, icon_url=after.guild.icon.url)
                embed.set_thumbnail(url=after.guild.icon.url)
            embed.set_footer(text=f"ID Role: {after.id}")
            
            await channel.send(embed=embed)
        
        if before.permissions != after.permissions:
            diff_added = [p[0].replace("_", " ").title() for p in after.permissions if p not in before.permissions]
            diff_removed = [p[0].replace("_", " ").title() for p in before.permissions if p not in after.permissions]
            
            embed = discord.Embed(
                title="🏷️⚙️ Permissions/Izin Role Diubah",
                description=f"Hak akses untuk role {after.mention} telah diperbarui.",
                color=after.color if after.color.value != 0 else discord.Color.gold()
            )
            if diff_added:
                embed.add_field(name="Izin Ditambahkan", value=", ".join(diff_added), inline=True)
            if diff_removed:
                embed.add_field(name="Izin Dicabut", value=", ".join(diff_removed), inline=True)
            
            embed.add_field(name="Diubah oleh", value=actor_mention, inline=False)
            if reason != "Tidak ada alasan":
                embed.add_field(name="Alasan", value=reason, inline=False)
            embed.set_footer(text=f"ID Role: {after.id}  •  ID Server: {after.guild.id}")
            await channel.send(embed=embed)
    
    @commands.Cog.listener()
    async def on_guild_role_delete(self, role:discord.Role) -> None:
        channel = await self.buka_channel_logging(role.guild)
        if not channel:
            return
        
        actor, reason = await self.baca_audit_log(role.guild, discord.AuditLogAction.role_delete, role.id)
        actor_mention = actor.mention if isinstance(actor, (discord.User, discord.Member)) else str(actor)
        
        embed = discord.Embed(
            title="🏷️🗑️ Role Dihapus",
            description=f"Role `@{role.name}` telah dihapus oleh {actor_mention}.",
            color=discord.Color.red()
        )
        if "Tidak ada alasan" not in reason:
            embed.add_field(name="Alasan", value=reason, inline=True)
        
        embed.set_footer(text=f"Role ID: {role.id}")
        if role.guild.icon:
            embed.set_thumbnail(url=role.guild.icon.url)
            embed.set_author(name=role.guild.name, icon_url=role.guild.icon.url)
        
        await channel.send(embed=embed)
    
    @commands.Cog.listener()
    async def on_guild_update(self, before:discord.Guild, after:discord.Guild) -> None:
        log_ch = await self.buka_channel_logging(after)
        if not log_ch:
            return
        
        actor, _reason = await self.baca_audit_log(after, discord.AuditLogAction.guild_update)
        actor_mention = actor.mention if isinstance(actor, (discord.User, discord.Member)) else str(actor)
        embed = None
        
        if before.name != after.name:
            embed = discord.Embed(
                title="🏠✏️ Nama Server Diubah",
                description=f"Nama server telah diperbarui oleh {actor_mention}.",
                color=WARNA_AIKA
            )
            embed.add_field(name="Sebelum", value=before.name, inline=True)
            embed.add_field(name="Sesudah", value=after.name, inline=True)
            
        elif before.icon != after.icon:
            embed = discord.Embed(
                title="🖼️✏️ Ikon Server Diubah",
                description=f"Ikon server telah diperbarui oleh {actor_mention}.",
                color=WARNA_AIKA
            )
            
        elif before.verification_level != after.verification_level:
            embed = discord.Embed(
                title="🏠🔒 Tingkat Verifikasi Server Diubah",
                description=f"Tingkat verifikasi diubah dari `{before.verification_level.name}` menjadi `{after.verification_level.name}`.",
                color=discord.Color.gold()
            )
            embed.add_field(name="Diubah oleh", value=actor_mention, inline=True)
        
        if embed:
            if after.icon:
                embed.set_thumbnail(url=after.icon.url)
                embed.set_author(name=after.name, icon_url=after.icon.url)
            embed.set_footer(text=f"Server ID: {after.id}")
            await log_ch.send(embed=embed)
    
    @commands.Cog.listener()
    async def on_webhooks_update(self, channel:discord.abc.GuildChannel) -> None:
        log_ch = await self.buka_channel_logging(channel.guild)
        if not log_ch:
            return
        
        actor, reason = await self.baca_audit_log(channel.guild, discord.AuditLogAction.webhook_create)
        actor_mention = actor.mention if isinstance(actor, (discord.User, discord.Member)) else str(actor)
        
        embed = discord.Embed(
            title="🌐✏️ Webhook Channel Diperbarui",
            description=f"Terjadi perubahan Webhook di channel {channel.mention}.",
            color=discord.Color.gold()
        )
        embed.add_field(name="Kemungkinan Pelaksana", value=actor_mention, inline=True)
        embed.add_field(name="Alasan", value=reason, inline=True)
        
        if channel.guild.icon:
            embed.set_thumbnail(url=channel.guild.icon.url)
            embed.set_author(name=channel.guild.name, icon_url=channel.guild.icon.url)
        embed.set_footer(text=f"ID Channel: {channel.id}")
        
        await log_ch.send(embed=embed)
    
    @commands.Cog.listener()
    async def on_integration_create(self, integration:discord.Integration) -> None:
        channel = await self.buka_channel_logging(integration.guild)
        if not channel:
            return
        
        actor, reason = await self.baca_audit_log(integration.guild, discord.AuditLogAction.integration_create)
        actor_mention = actor.mention if isinstance(actor, (discord.User, discord.Member)) else str(actor)
        
        embed = discord.Embed(
            title="🤖🔗 Integrasi Aplikasi Dibuat",
            description=f"Integrasi __{integration.name}__ (tipe: `{integration.type}`) telah ditambahkan.",
            color=discord.Color.green()
        )
        embed.add_field(name="Ditambahkan oleh", value=actor_mention, inline=True)
        embed.add_field(name="Alasan", value=reason, inline=True)
        
        if integration.guild.icon:
            embed.set_thumbnail(url=integration.guild.icon.url)
            embed.set_author(name=integration.guild.name, icon_url=integration.guild.icon.url)
        embed.set_footer(text=f"Integration ID: {integration.id}")
        
        await channel.send(embed=embed)
    
    # ==========================================
    # 5. STAGE, EMOJI, STICKER, THREADS & EVENTS
    # ==========================================
    @commands.Cog.listener()
    async def on_stage_instance_create(self, stage_instance:discord.StageInstance) -> None:
        if not stage_instance.guild:
            return
        channel = await self.buka_channel_logging(stage_instance.guild)
        if not channel:
            return
        
        embed = discord.Embed(
            title="🗼🔊 Stage Channel Dimulai",
            description=f"Stage {stage_instance.channel.mention if stage_instance.channel else 'N/A'} telah dimulai.\n**Topik:** {stage_instance.topic}",
            color=discord.Color.green()
        )
        embed.set_footer(text=f"Stage ID: {stage_instance.id}  •  ID Channel: {stage_instance.channel_id}")
        await channel.send(embed=embed)
    
    @commands.Cog.listener()
    async def on_stage_instance_delete(self, stage_instance:discord.StageInstance) -> None:
        if not stage_instance.guild:
            return
        channel = await self.buka_channel_logging(stage_instance.guild)
        if not channel:
            return
        
        embed = discord.Embed(
            title="🗼🛑 Stage Channel Selesai",
            description=f"Stage di {stage_instance.channel.mention if stage_instance.channel else 'N/A'} telah dihentikan.",
            color=discord.Color.red()
        )
        embed.set_footer(text=f"Stage ID: {stage_instance.id}")
        await channel.send(embed=embed)
    
    @commands.Cog.listener()
    async def on_guild_emojis_update(
        self, guild: discord.Guild, before:list[discord.Emoji], after:list[discord.Emoji]) -> None:
        channel = await self.buka_channel_logging(guild)
        if not channel:
            return
        
        if len(after) > len(before):
            added = [e for e in after if e not in before]
            if added:
                embed = discord.Embed(
                    title="🤨➕ Emoji Ditambahkan",
                    description=f"{added[0]} (`:{added[0].name}:`)",
                    color=discord.Color.green()
                )
                await channel.send(embed=embed)
        elif len(before) > len(after):
            removed = [e for e in before if e not in after]
            if removed:
                embed = discord.Embed(
                    title="🤨🗑️ Emoji Dihapus",
                    description=f"Emoji `:{removed[0].name}:` telah dihapus.",
                    color=discord.Color.red()
                )
                await channel.send(embed=embed)
    
    @commands.Cog.listener()
    async def on_guild_stickers_update(self, guild:discord.Guild, before:list[discord.Sticker], after:list[discord.Sticker]) -> None:
        channel = await self.buka_channel_logging(guild)
        if not channel:
            return
        
        embed = discord.Embed(title="💮✏️ Stiker Diperbarui", description="Terjadi perubahan pada daftar stiker server.", color=WARNA_AIKA)
        await channel.send(embed=embed)
    
    @commands.Cog.listener()
    async def on_thread_create(self, thread:discord.Thread) -> None:
        channel = await self.buka_channel_logging(thread.guild)
        if not channel:
            return
        
        creator = thread.owner.mention if thread.owner else f"<@{thread.owner_id}>"
        embed = discord.Embed(
            title="🧵➕ Thread Dibuat",
            description=f"{thread.mention} dibuat oleh {creator} di channel {thread.parent.mention if thread.parent else 'N/A'}.",
            color=discord.Color.green()
        )
        embed.set_footer(text=f"Thread ID: {thread.id}  •  Creator ID: {thread.owner_id}")
        await channel.send(embed=embed)
    
    @commands.Cog.listener()
    async def on_thread_delete(self, thread:discord.Thread) -> None:
        channel = await self.buka_channel_logging(thread.guild)
        if not channel:
            return
        
        embed = discord.Embed(
            title="🧵🗑️ Thread Dihapus",
            description=f"Thread `#{thread.name}` ({thread.id}) telah dihapus.",
            color=discord.Color.red()
        )
        await channel.send(embed=embed)
    
    @commands.Cog.listener()
    async def on_thread_update(self, before:discord.Thread, after:discord.Thread) -> None:
        channel = await self.buka_channel_logging(after.guild)
        if not channel:
            return
        
        embed = None
        if before.archived != after.archived:
            status = "Diarsipkan" if after.archived else "Buka Arsip"
            emoji = "🧵🗂️" if after.archived else "🧵📂"
            embed = discord.Embed(
                title=f"{emoji} Thread {status}",
                description=f"Status arsip thread {after.mention} telah diubah menjadi **{status}**.",
                color=discord.Color.orange() if after.archived else discord.Color.green()
            )
        elif before.locked != after.locked:
            status = "Dikunci" if after.locked else "Dibuka Kunci"
            embed = discord.Embed(
                title=f"Thread {status}",
                description=f"Thread {after.mention} telah **{status}** oleh moderator.",
                color=discord.Color.red() if after.locked else discord.Color.green()
            )
        elif before.name != after.name:
            embed = discord.Embed(
                title="🧵✏️ Nama Thread Diperbarui",
                description=f"Nama thread {after.mention} telah diubah.",
                color=WARNA_AIKA
            )
            embed.add_field(name="Sebelum", value=before.name, inline=True)
            embed.add_field(name="Sesudah", value=after.name, inline=True)
        
        if embed:
            embed.set_footer(text=f"Thread ID: {after.id}")
            await channel.send(embed=embed)
    
    @commands.Cog.listener()
    async def on_scheduled_event_create(self, event:discord.ScheduledEvent) -> None:
        if not event.guild:
            return
        channel = await self.buka_channel_logging(event.guild)
        if not channel:
            return
        
        creator = event.creator.mention if event.creator else f"<@{event.creator_id}>"
        embed = discord.Embed(
            title="🗓️➕ Event Server Dibuat",
            description=f"Event **{event.name}** telah dijadwalkan.",
            color=discord.Color.green()
        )
        embed.add_field(name="Dibuat oleh", value=creator, inline=True)
        embed.add_field(name="Lokasi / Channel", value=event.location or (event.channel.mention if event.channel else "N/A"), inline=True)
        if event.description:
            embed.add_field(name="Deskripsi", value=event.description, inline=False)
        embed.set_footer(text=f"Event ID: {event.id}")
        await channel.send(embed=embed)
    
    @commands.Cog.listener()
    async def on_scheduled_event_delete(self, event:discord.ScheduledEvent) -> None:
        if not event.guild:
            return
        channel = await self.buka_channel_logging(event.guild)
        if not channel:
            return
        
        embed = discord.Embed(
            title="🗓️🛑 Event Server Dibatalkan/Dihapus",
            description=f"Event **{event.name}** ({event.id}) telah dibatalkan.",
            color=discord.Color.red()
        )
        await channel.send(embed=embed)
    
    # ==========================================
    # 6. BAN, MODERASI, AUTOMOD & BOT COMMANDS
    # ==========================================
    @commands.Cog.listener()
    async def on_member_ban(self, guild:discord.Guild, user:discord.User|discord.Member) -> None:
        channel = await self.buka_channel_logging(guild)
        if not channel:
            return
        
        actor, reason = await self.baca_audit_log(guild, discord.AuditLogAction.ban, user.id)
        actor_mention = actor.mention if isinstance(actor, (discord.User, discord.Member)) else str(actor)
        
        embed = discord.Embed(
            title="🔨👤 Member Di-ban",
            description=f"User `@{user.name}` telah di-ban dari server.",
            color=discord.Color.red()
        )
        embed.add_field(name="Di-ban oleh", value=actor_mention, inline=True)
        embed.add_field(name="Alasan", value=reason, inline=True)
        
        embed.set_author(name=user.name, icon_url=user.display_avatar.url)
        embed.set_thumbnail(url=user.display_avatar.url)
        embed.set_footer(text=f"User ID: {user.id}")
        
        await channel.send(embed=embed)
    
    @commands.Cog.listener()
    async def on_member_unban(self, guild:discord.Guild, user:discord.User) -> None:
        channel = await self.buka_channel_logging(guild)
        if not channel:
            return
        
        actor, reason = await self.baca_audit_log(guild, discord.AuditLogAction.unban, user.id)
        actor_mention = actor.mention if isinstance(actor, (discord.User, discord.Member)) else str(actor)
        
        embed = discord.Embed(
            title="🔨👤✅ Ban Dicabut",
            description=f"`@{user.name}` telah di-unban.",
            color=discord.Color.green()
        )
        embed.add_field(name="Di-unban oleh", value=actor_mention, inline=True)
        embed.add_field(name="Alasan", value=reason, inline=True)
        
        embed.set_author(name=user.name, icon_url=user.display_avatar.url)
        embed.set_thumbnail(url=user.display_avatar.url)
        embed.set_footer(text=f"User ID: {user.id}")
        
        await channel.send(embed=embed)
    
    @commands.Cog.listener()
    async def on_socket_raw_dispatch(self, msg:dict[str,Any]) -> None:
        event_type = msg.get("t")
        data = msg.get("d", {})
        
        if event_type == "AUTO_MODERATION_ACTION_EXECUTION":
            guild_id = int(data.get("guild_id", 0))
            channel = await self.buka_channel_logging(guild_id)
            if not channel:
                return
            
            user_id = data.get("user_id")
            rule_id = data.get("rule_id")
            action_type = data.get("action", {}).get("type")
            matched_content = data.get("matched_content")
            
            LOGO_AUTOMOD = "https://cdn.discordapp.com/attachments/863959650448703538/1541927557501296711/632a24dc0918d34459738418_AutoMod-Final-Blog-Author.png"
            LOGO_DISCORD = "https://cdn.discordapp.com/attachments/863959650448703538/1541928366981128305/Discord-Symbol-Blurple.png"
            
            embed = discord.Embed(
                title="Discord AutoMod Action Intercepted",
                description=f"AutoMod memicu tindakan di channel <#{data.get('channel_id')}>.",
                color=WARNA_DISCORD
            )
            embed.add_field(name="Pelanggar", value=f"<@{user_id}>\n(`{user_id}`)", inline=True)
            embed.add_field(name="Rule ID", value=f"`{rule_id}`", inline=True)
            embed.add_field(name="Tindakan Tipe", value=f"`{action_type}`", inline=False)
            
            if matched_content:
                embed.add_field(name="Konten Terdeteksi", value=f"`{matched_content}`", inline=False)
            
            embed.set_thumbnail(url=LOGO_AUTOMOD)
            embed.set_author(name="Discord Built-in Moderation System", icon_url=LOGO_DISCORD)
            await channel.send(embed=embed)
            
        elif event_type == "VOICE_CHANNEL_STATUS_UPDATE":
            channel_id = int(data.get("id", 0))
            if channel_id == CHANNEL_PENGECUALIAN:
                return
            
            guild_id = int(data.get("guild_id", 0))
            guild = self.bot.get_guild(guild_id)
            if not guild:
                return
            
            log_ch = await self.buka_channel_logging(guild)
            if not log_ch:
                return
            
            channel = guild.get_channel(channel_id)
            channel_mention = channel.mention if channel else f"<#{channel_id}>"
            status_text = data.get("status") or "*Status Dihapus / Kosong*"
            
            embed = discord.Embed(
                title="🔊✏️ Status Voice Channel Diperbarui",
                description=f"Status di channel {channel_mention} telah diperbarui.",
                color=WARNA_AIKA
            )
            embed.add_field(name="Status Baru", value=status_text, inline=False)
            embed.set_footer(text=f"ID VC: {channel_id}  •  Server ID: {guild_id}")
            
            if guild.icon:
                embed.set_thumbnail(url=guild.icon.url)
            embed.set_author(name=guild.name, icon_url=guild.icon.url if guild.icon else None)
            
            await log_ch.send(embed=embed)
            
        elif event_type == "GUILD_MEMBER_UPDATE":
            guild_id = int(data.get("guild_id", 0))
            if guild_id != BINROOM:
                return
            
            primary_guild = data.get("primary_guild")
            if not primary_guild:
                return
            
            primary_guild_id = int(primary_guild.get("identity_guild_id") or primary_guild.get("id") or 0)
            if primary_guild_id == BINROOM:
                user_data = data.get("user", {})
                user_id = int(user_data.get("id", 0))
                
                guild = self.bot.get_guild(guild_id)
                if not guild:
                    return
                
                channel = await self.buka_channel_logging(guild)
                if not channel:
                    return
                
                member = guild.get_member(user_id) or await guild.fetch_member(user_id)
                tag_text = primary_guild.get("tag") or "*Tag Server*"
                
                embed_tag = discord.Embed(
                    title="🏷️ Member Memasang Tag Server!",
                    description=f"{member.mention} baru saja memasang Guild Tag server ini!",
                    color=WARNA_AIKA
                )
                embed_tag.add_field(name="Tag yang Dipakai", value=f"`{tag_text}`", inline=True)
                embed_tag.set_author(name=member.name, icon_url=member.display_avatar.url)
                embed_tag.set_footer(text=f"ID User: {member.id} • Server ID: {BINROOM}")
                
                if guild.icon:
                    embed_tag.set_thumbnail(url=guild.icon.url)
                
                owner_id = int(os.getenv("OWNER_ID", str(OWNER_ID)))
                await channel.send(content=f"<@{owner_id}> 😳", embed=embed_tag)
    
    # ==========================================
    # 7. AI CHATBOT LOGGING
    # ==========================================
    @commands.Cog.listener()
    async def on_ai_log(
        self,
        guild: discord.Guild,
        user: discord.User | discord.Member,
        action: str,
        details: str,
        color: discord.Color = WARNA_AIKA,
        fields: list[tuple[str, str, bool]] | None = None,
        chat_id: int | None = None,
    ) -> None:
        channel = await self.buka_channel_logging(guild)
        if not channel:
            return
        
        embed = discord.Embed(
            title=f"🌸🤖 AI Chatbot: {action}",
            description=details,
            color=color
        )
        if self.bot.user:
            embed.set_author(name=self.bot.user.name, icon_url=self.bot.user.display_avatar.url)
            embed.set_thumbnail(url=self.bot.user.display_avatar.url)
        
        if fields:
            for name, value, inline in fields:
                embed.add_field(name=name, value=value, inline=inline)
        
        footer_text = f"ID User: {user.id}"
        if chat_id is not None:
            footer_text += f"  •  Chat ID: {chat_id}"
        
        embed.set_footer(text=footer_text)
        await channel.send(embed=embed)


async def setup(bot:commands.Bot) -> None:
    await bot.add_cog(ServerLogger(bot))