import discord
from discord import app_commands
from discord.ext import commands

import config


class VCStats(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
    
    async def baca_emoji_voice(self, member:discord.Member) -> str:
        app_emojis = {}
        cog_userinfo = self.bot.get_cog("UserInfo")
        if cog_userinfo and hasattr(cog_userinfo, "baca_application_emojis"):
            app_emojis = await cog_userinfo.baca_application_emojis()
        
        vc_states = []
        voice = member.voice
        if not voice:
            return ""
        
        if voice.mute or voice.suppress:
            vc_states.append(app_emojis.get("server_muted", "🔇"))
        elif voice.self_mute:
            vc_states.append(app_emojis.get("self_muted", "🎤"))
        else:
            vc_states.append(app_emojis.get("unmuted_speaking", "🎙️"))
        
        if voice.deaf:
            vc_states.append(app_emojis.get("server_deafen", "🔇"))
        elif voice.self_deaf:
            vc_states.append(app_emojis.get("self_deafen", "🔇"))
        
        if voice.self_stream:
            vc_states.append(app_emojis.get("screen_sharing", "🖥️"))
        if voice.self_video:
            vc_states.append(app_emojis.get("open_cam", "📹"))
        
        return " ".join(vc_states)
    
    @commands.hybrid_command(
        name="vc-stats",
        description="Menampilkan daftar member yang sedang berada di Voice Channel beserta durasinya.",
        aliases=["status-vc", "vclist"]
    )
    @app_commands.describe(target_channel="Voice channel yang ingin diperiksa (Default: VC tempat kamu berada)")
    async def vc_stats(
        self,
        ctx: commands.Context,
        target_channel: discord.VoiceChannel | discord.StageChannel | None = None
    ):
        channel = target_channel
        if not channel:
            if isinstance(ctx.author, discord.Member) and ctx.author.voice:
                channel = ctx.author.voice.channel
            else:
                await ctx.send("❌ Kamu harus berada di Voice Channel atau memilih channel target!", ephemeral=True)
                return
        
        if not channel.members:
            await ctx.send(f"⚠️ Voice channel {channel.mention} sedang kosong.", ephemeral=True)
            return
        
        logger_cog = self.bot.get_cog("ServerLogger")
        status_vc_map = getattr(logger_cog, "status_vc", {}) if logger_cog else {}
        
        daftar_member_str = []
        for member in channel.members:
            emojis = await self.baca_emoji_voice(member)
            waktu_join = status_vc_map.get(member.id)
            
            if waktu_join:
                unix_ts = int(waktu_join.timestamp())
                waktu_str = f"<t:{unix_ts}:R>"
            else:
                waktu_str = "*tidak terdata*"
            
            daftar_member_str.append(f"- {member.mention} {emojis}: {waktu_str}")
        
        container = discord.ui.Container(accent_color=config.pengaturan.warna_aika)
        
        container.add_item(discord.ui.TextDisplay(
            content=f"### 🔊 Statistik Voice Channel — {channel.mention}\n-# Total member: **{len(channel.members)} orang**"
        ))
        container.add_item(discord.ui.Separator(spacing=discord.SeparatorSpacing.small))
        container.add_item(discord.ui.TextDisplay(content="\n".join(daftar_member_str)))
        
        await ctx.send(
            view=discord.ui.LayoutView().add_item(container),
            allowed_mentions=discord.AllowedMentions.none()
        )


async def setup(bot:commands.Bot):
    await bot.add_cog(VCStats(bot))