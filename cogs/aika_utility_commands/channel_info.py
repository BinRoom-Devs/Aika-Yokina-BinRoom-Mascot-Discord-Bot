import discord
from discord import app_commands
from discord.ext import commands


class ChannelInfo(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @commands.hybrid_command(
        name="channelinfo",
        description="Menampilkan informasi lengkap tentang channel ini atau channel yang dipilih.",
        aliases=["ch-info", "cinfo", "channel", "saluran"]
    )
    @app_commands.describe(target_channel="Channel yang ingin dilihat detailnya. (Default: channel saat ini)")
    async def channel_info(
        self,
        ctx: commands.Context,
        target_channel: discord.TextChannel | discord.VoiceChannel | discord.StageChannel | discord.ForumChannel | None = None
    ):
        ch = target_channel or ctx.channel
        
        emoji_urls = {
            discord.ChannelType.text: "https://cdn.jsdelivr.net/gh/twitter/twemoji@latest/assets/72x72/1f4ac.png",         # #️⃣
            discord.ChannelType.voice: "https://cdn.jsdelivr.net/gh/twitter/twemoji@latest/assets/72x72/1f50a.png",        # 🔊
            discord.ChannelType.stage_voice: "https://cdn.jsdelivr.net/gh/jdecked/twemoji@latest/assets/72x72/1f5fc.png",  # 🗼
            discord.ChannelType.forum: "https://cdn.jsdelivr.net/gh/jdecked/twemoji@latest/assets/72x72/1f5e3.png",        # 🗣️
            discord.ChannelType.news: "https://cdn.jsdelivr.net/gh/jdecked/twemoji@latest/assets/72x72/1f4e3.png",         # 📢
        }
        thumb_url = emoji_urls.get(ch.type, "https://cdn.jsdelivr.net/gh/jdecked/twemoji@latest/assets/72x72/1f4dd.png")
        
        channel_types = {
            discord.ChannelType.text: "Text channel (saluran teks)",
            discord.ChannelType.voice: "Voice channel (saluran suara)",
            discord.ChannelType.news: "Channel pengumuman",
            discord.ChannelType.stage_voice: "Stage channel",
            discord.ChannelType.forum: "Forum channel",
        }
        type_name = channel_types.get(ch.type, str(ch.type).replace('_', ' ').title())
        
        container = discord.ui.Container(accent_color=0xD675C1)
        
        header_1 = f"### ℹ️  Informasi Saluran — {ch.mention}"
        container.add_item(discord.ui.TextDisplay(content=header_1))
        container.add_item(discord.ui.Separator(spacing=discord.SeparatorSpacing.small))
        
        created_at = f"<t:{int(ch.created_at.timestamp())}:R> (<t:{int(ch.created_at.timestamp())}:F>)"
        bagian_1 = [
            f"- **Nama:** __{ch.name}__",
            f"- **ID:** `{ch.id}`",
            f"- **Tipe:** {type_name}",
            f"- **Dibuat:** {created_at}",
            f"- **Kategori:** {ch.category.mention if getattr(ch, 'category', None) else 'tidak ada'}",
            f"- **Posisi:** `{getattr(ch, 'position', 'Tidak Ada')}`",
        ]
        topik = getattr(ch, 'topic', None)
        if topik:
            bagian_1.insert(1, f"- **Deskripsi:** {topik if len(topik) <= 1024 else f'{topik[:1021]}...'}")
        container.add_item(discord.ui.Section(
            discord.ui.TextDisplay(content='\n'.join(bagian_1)),
            accessory=discord.ui.Thumbnail(media=thumb_url)
        ))
        
        container.add_item(discord.ui.Separator(spacing=discord.SeparatorSpacing.small))
        
        if isinstance(ch, (discord.TextChannel, discord.ForumChannel)):
            bagian_2 = []
            if hasattr(ch, 'slowmode_delay') and ch.slowmode_delay:
                bagian_2.append(f"- **Mode lambat:** {ch.slowmode_delay} detik")
            if hasattr(ch, 'is_nsfw') and ch.is_nsfw():
                bagian_2.append("- **NSFW/18+:** Ya")
            if hasattr(ch, 'default_auto_archive_duration'):
                bagian_2.append(f"- **Arsip thread otomatis:** {ch.default_auto_archive_duration} menit")
            
            if bagian_2:
                container.add_item(discord.ui.TextDisplay(content='\n'.join(bagian_2)))
                container.add_item(discord.ui.Separator(spacing=discord.SeparatorSpacing.small))
        
        if isinstance(ch, (discord.VoiceChannel, discord.StageChannel)):
            mode_video = {
                discord.VideoQualityMode.auto: "otomatis",
                discord.VideoQualityMode.full: "720p/1080p (tinggi)"
            }
            kualitas_video = mode_video.get(ch.video_quality_mode, "otomatis")
            
            kalau_vc = [
                f"- **Bitrate:** {ch.bitrate//1000} kbps",
                f"- **Orang yang lagi VC-an di dalam:** {len(ch.members)}",
                f"- **Wilayah server VC:** {ch.rtc_region or 'otomatis'}",
                f"- **Kualitas video:** {kualitas_video}"
            ]
            if ch.user_limit > 0:
                kalau_vc.insert(1, f"- **Batas orang:** {ch.user_limit}")
            
            container.add_item(discord.ui.TextDisplay(content='\n'.join(kalau_vc)))
            container.add_item(discord.ui.Separator(spacing=discord.SeparatorSpacing.small))
        
        
        if isinstance(ch, discord.ForumChannel):
            kalau_forum = []
            if ch.available_tags:
                nama_tag = [f"{tag.name}" + (f" (emoji: {tag.emoji})" if tag.emoji else '') for tag in ch.available_tags]
                kalau_forum.append(f"- **Label tersedia ({len(ch.available_tags)}):** {', '.join(nama_tag)}")
            if ch.default_reaction_emoji:
                kalau_forum.append(f"- **Emoji reaction bawaan:** {ch.default_reaction_emoji}")
            if ch.default_sort_order:
                pengurutan = {
                    discord.ForumOrderType.latest_activity: "aktivitas terbaru",
                    discord.ForumOrderType.creation_date: "waktu pembuatan"
                }
                kalau_forum.append(f"- **Pengurutan bawaan:** {pengurutan.get(ch.default_sort_order, 'default')}")
            if ch.default_layout:
                layouts = {
                    discord.ForumLayout.list_view: "daftar",
                    discord.ForumLayout.grid_view: "galeri/kotak-kotak"
                }
                kalau_forum.append(f"- **Tata letak bawaan:** {layouts.get(ch.default_layout, 'default')}")
            
            if kalau_forum:
                container.add_item(discord.ui.TextDisplay(content='\n'.join(kalau_forum)))
                container.add_item(discord.ui.Separator(spacing=discord.SeparatorSpacing.small))
        
        if isinstance(ch, (discord.TextChannel, discord.ForumChannel)):
            thread_aktif = ch.threads
            container.add_item(discord.ui.TextDisplay(content=f"- **Thread aktif:** {len(thread_aktif)}"))
            container.add_item(discord.ui.Separator(spacing=discord.SeparatorSpacing.small))
        
        if hasattr(ch, 'overwrites'):
            jumlah_overwrite = len(ch.overwrites)
            role_tertaut = getattr(ch, 'permissions_synced', None)
            
            info_izin = [f"- **Pengecualian izin kustom:** {jumlah_overwrite}"]
            if role_tertaut is not None:
                info_izin.append(f"- **Tersinkronisasi dengan kategori:** {'ya' if role_tertaut else 'tidak'}")
            
            container.add_item(discord.ui.TextDisplay(content='\n'.join(info_izin)))
        
        if isinstance(ch, (discord.TextChannel, discord.VoiceChannel, discord.ForumChannel, discord.StageChannel)):
            try:
                webhooks = await ch.webhooks()
                container.add_item(discord.ui.TextDisplay(content=f"- **Webhook:** {len(webhooks)} terpasang"))
            except (discord.Forbidden, discord.HTTPException):
                container.add_item(discord.ui.TextDisplay(content="- **Webhook:** (tidak ada izin akses)"))
        
        await ctx.send(view=discord.ui.LayoutView().add_item(container))


async def setup(bot: commands.Bot):
    await bot.add_cog(ChannelInfo(bot))