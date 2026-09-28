import discord
from discord.ext import commands


class ServerInfo(commands.Cog):
    def __init__(self, bot:commands.Bot):
        self.bot = bot
    
    async def get_status_emojis(self) -> dict[str, str]:
        fallback = {
            "online": "🟢",
            "idle": "🌙",
            "dnd": "⛔",
            "offline": "⚪",
        }
        try:
            emojis = await self.bot.fetch_application_emojis()
            
            e_online = discord.utils.get(emojis, name="available_online")
            e_idle = discord.utils.get(emojis, name="idle")
            e_dnd = discord.utils.get(emojis, name="do_not_disturb")
            e_offline = discord.utils.get(emojis, name="offline_or_invisible")
            
            return {
                "online": str(e_online) if e_online else fallback["online"],
                "idle": str(e_idle) if e_idle else fallback["idle"],
                "dnd": str(e_dnd) if e_dnd else fallback["dnd"],
                "offline": str(e_offline) if e_offline else fallback["offline"],
            }
        except Exception as e:  # noqa: BLE001
            print(f"⚠️ [Aika] Gagal membaca application emojis: {e}", flush=True)
            return fallback
    
    @commands.hybrid_command(
        name="serverinfo",
        description="Menampilkan informasi lengkap dan statistik tentang server ini.",
        aliases=["sinfo", "server", "guild", "guildinfo"],
    )
    @commands.guild_only()
    async def server_info(self, ctx:commands.Context):
        guild = ctx.guild
        if not guild:
            return
        
        app_emojis = await self.get_status_emojis()
        
        online_cnt = sum(1 for m in guild.members if m.status == discord.Status.online)
        idle_cnt = sum(1 for m in guild.members if m.status == discord.Status.idle)
        dnd_cnt = sum(1 for m in guild.members if m.status == discord.Status.dnd)
        offline_cnt = sum(1 for m in guild.members if m.status == discord.Status.offline)
        
        bot_count = sum(1 for m in guild.members if m.bot)
        human_count = guild.member_count - bot_count if guild.member_count else 0
        
        text_channels = len(guild.text_channels)
        voice_channels = len(guild.voice_channels)
        stage_channels = len(guild.stage_channels)
        forum_channels = len(guild.forums)
        categories = len(guild.categories)
        total_channels = text_channels + voice_channels + stage_channels + forum_channels
        
        verif_levels = {
            discord.VerificationLevel.none: "tidak ada (bebas)",
            discord.VerificationLevel.low: "rendah (email terverifikasi)",
            discord.VerificationLevel.medium: "sedang (terdaftar lebih dari 5 menit)",
            discord.VerificationLevel.high: "tinggi (member lebih dari 10 menit)",
            discord.VerificationLevel.highest: "sangat tinggi (no. HP terverifikasi)",
        }
        verif_str = verif_levels.get(guild.verification_level, str(guild.verification_level).title())
        
        tier_boost = f"Level {guild.premium_tier}" if guild.premium_tier > 0 else "belum ada Level"
        
        container = discord.ui.Container(accent_color=0xD675C1)
        
        header_text = f"### 🏡  Informasi Server — {guild.name}"
        container.add_item(discord.ui.TextDisplay(content=header_text))
        
        container.add_item(discord.ui.Separator(spacing=discord.SeparatorSpacing.small))
        
        created_at = f"<t:{int(guild.created_at.timestamp())}:R> (<t:{int(guild.created_at.timestamp())}:F>)"
        icon_url = guild.icon.url if guild.icon else "https://cdn.jsdelivr.net/gh/jdecked/twemoji@latest/assets/72x72/1f3f0.png"
        bagian_1 = [
            f"- **Nama:** __{guild.name}__",
            f"- **ID:** `{guild.id}`",
            f"- **Pemilik:** {guild.owner.mention if guild.owner else 'Tidak diketahui'}",
            f"- **Dibuat:** {created_at}",
            f"- **Tingkat verifikasi:** {verif_str}",
        ]
        if guild.description:
            bagian_1.insert(1, f"- **Deskripsi:** {guild.description}")
        container.add_item(
            discord.ui.Section(
                discord.ui.TextDisplay(content="\n".join(bagian_1)),
                accessory=discord.ui.Thumbnail(media=icon_url),
            )
        )
        
        container.add_item(discord.ui.Separator(spacing=discord.SeparatorSpacing.small))
        
        bagian_2 = [
            f"- **Total member:** `{guild.member_count}` ({human_count} orang, {bot_count} bot)",
            f"- **Total role:** `{len(guild.roles)}`",
            f"- **Total emoji & stiker:** `{len(guild.emojis)}` emoji, `{len(guild.stickers)}` stiker",
        ]
        container.add_item(discord.ui.TextDisplay(content="\n".join(bagian_2)))
        
        container.add_item(discord.ui.Separator(spacing=discord.SeparatorSpacing.small))
        
        bagian_3 = [
            f"- **Total channel ({total_channels}):** {text_channels} text, {voice_channels} voice, {forum_channels} forum, {stage_channels} stage",
            f"- **Total kategori:** `{categories}`",
        ]
        if guild.rules_channel:
            bagian_3.append(f"- **Channel aturan:** {guild.rules_channel.mention}")
        if guild.afk_channel:
            bagian_3.append(f"- **Channel AFK:** {guild.afk_channel.mention} *(Timeout: {guild.afk_timeout // 60}m)*")
        
        container.add_item(discord.ui.TextDisplay(content="\n".join(bagian_3)))
        container.add_item(discord.ui.Separator(spacing=discord.SeparatorSpacing.small))
        
        bagian_4 = [
            f"- **Status boost:** {tier_boost} ({guild.premium_subscription_count} Booster)",
            f"- **Batas bitrate voice:** `{guild.bitrate_limit // 1000} kbps`",
            f"- **Batas upload:** `{int(guild.filesize_limit / (1024 * 1024))} MB`",
        ]
        container.add_item(discord.ui.TextDisplay(content="\n".join(bagian_4)))
        
        if guild.emojis:
            container.add_item(discord.ui.Separator(spacing=discord.SeparatorSpacing.small))
            
            title = f"**Daftar Emoji [{len(guild.emojis)}]:**\n# "
            max_emoji_chars = 950
            
            truncated_emojis = []
            current_len = 0
            
            for emoji in guild.emojis:
                emoji_str = str(emoji)
                if current_len + len(emoji_str) + 1 > max_emoji_chars:
                    break
                truncated_emojis.append(emoji_str)
                current_len += len(emoji_str) + 1
            
            sisa = len(guild.emojis) - len(truncated_emojis)
            emoji_body = " ".join(truncated_emojis)
            
            if sisa > 0:
                display_text = f"{title}{emoji_body} *(+{sisa} emoji lainnya)*"
            else:
                display_text = f"{title}{emoji_body}"
            
            container.add_item(discord.ui.TextDisplay(content=display_text))
        
        container.add_item(discord.ui.Separator(spacing=discord.SeparatorSpacing.small))
        
        presence_summary = (
            f"{app_emojis['online']} {online_cnt}     "
            f"{app_emojis['idle']} {idle_cnt}     "
            f"{app_emojis['dnd']} {dnd_cnt}    "
            f"{app_emojis['offline']} {offline_cnt}"
        )
        footer = f"-# {presence_summary}"
        container.add_item(discord.ui.TextDisplay(content=footer))
        
        await ctx.send(
            view=discord.ui.LayoutView().add_item(container),
            allowed_mentions=discord.AllowedMentions.none(),
        )


async def setup(bot:commands.Bot):
    await bot.add_cog(ServerInfo(bot))