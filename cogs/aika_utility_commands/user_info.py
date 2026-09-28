import discord
from discord import app_commands
from discord.ext import commands


class UserInfo(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
    
    async def baca_application_emojis(self) -> dict[str, str]:
        """Fetch custom status, badge, dan voice state emojis dari Developer Portal secara dinamis."""
        fallback = {
            "online": "🟢",
            "idle": "🌙",
            "dnd": "⛔",
            "offline": "⚪",
            "streaming": "🟣",
            "mobile": "📱",
            "hypesquad_bravery": "🛡️",
            "hypesquad_brilliance": "💎",
            "hypesquad_balance": "⚖️",
            "server_muted": "🔇",
            "server_deafen": "🔇",
            "self_deafen": "🔇",
            "screen_sharing": "🖥️",
            "unmuted_speaking": "🎤",
            "open_cam": "📹",
            "self_muted": "🎤",
        }
        try:
            emojis = await self.bot.fetch_application_emojis()
            
            get_e = lambda name: discord.utils.get(emojis, name=name)
            
            e_online = get_e("available_online")
            e_idle = get_e("idle")
            e_dnd = get_e("do_not_disturb")
            e_offline = get_e("offline_or_invisible")
            e_stream = get_e("streaming")
            e_mobile = get_e("online_mobile")
            
            e_bravery = get_e("hypesquad_bravery")
            e_brilliance = get_e("hypesquad_brilliance")
            e_balance = get_e("hypesquad_balance")
            
            e_server_muted = get_e("server_muted")
            e_server_deafen = get_e("server_deafen")
            e_self_deafen = get_e("self_deafen")
            e_screen_sharing = get_e("screen_sharing")
            e_unmuted_speaking = get_e("unmuted_speaking")
            e_open_cam = get_e("open_cam")
            e_self_muted = get_e("self_muted")
            
            return {
                "online": str(e_online) if e_online else fallback["online"],
                "idle": str(e_idle) if e_idle else fallback["idle"],
                "dnd": str(e_dnd) if e_dnd else fallback["dnd"],
                "offline": str(e_offline) if e_offline else fallback["offline"],
                "streaming": str(e_stream) if e_stream else fallback["streaming"],
                "mobile": str(e_mobile) if e_mobile else fallback["mobile"],
                "hypesquad_bravery": str(e_bravery) if e_bravery else fallback["hypesquad_bravery"],
                "hypesquad_brilliance": str(e_brilliance) if e_brilliance else fallback["hypesquad_brilliance"],
                "hypesquad_balance": str(e_balance) if e_balance else fallback["hypesquad_balance"],
                "server_muted": str(e_server_muted) if e_server_muted else fallback["server_muted"],
                "server_deafen": str(e_server_deafen) if e_server_deafen else fallback["server_deafen"],
                "self_deafen": str(e_self_deafen) if e_self_deafen else fallback["self_deafen"],
                "screen_sharing": str(e_screen_sharing) if e_screen_sharing else fallback["screen_sharing"],
                "unmuted_speaking": str(e_unmuted_speaking) if e_unmuted_speaking else fallback["unmuted_speaking"],
                "open_cam": str(e_open_cam) if e_open_cam else fallback["open_cam"],
                "self_muted": str(e_self_muted) if e_self_muted else fallback["self_muted"],
            }
        except Exception as e:  # noqa: BLE001
            print(f"⚠️ [Aika] Gagal mengambil application emojis: {e}", flush=True)
            return fallback
    
    @commands.hybrid_command(
        name="userinfo",
        description="Nampilin informasi lengkap tentang akun seseorang.",
        aliases=["uinfo", "user", "pengguna", "whois"]
    )
    @app_commands.describe(target_user="Pengguna yang ingin diperiksa (Default: diri sendiri)")
    async def user_info(
        self,
        ctx: commands.Context,
        target_user: discord.Member | discord.User | None = None
    ):
        target = target_user or ctx.author
        
        if ctx.guild and isinstance(target, discord.User):
            target = ctx.guild.get_member(target.id) or target
        
        is_member = isinstance(target, discord.Member)
        
        app_emojis = await self.baca_application_emojis()
        
        status_str = "__offline/invisible__"
        status_emoji = app_emojis["offline"]
        
        if is_member:
            status_map = {
                discord.Status.online: app_emojis["online"],
                discord.Status.idle: app_emojis["idle"],
                discord.Status.dnd: app_emojis["dnd"],
                discord.Status.offline: app_emojis["offline"],
            }
            status_emoji = status_map.get(target.status, app_emojis["offline"])
            status_str = str(target.status)
            
            if any(isinstance(act, discord.Streaming) for act in target.activities):
                status_emoji = app_emojis["streaming"]
                status_str = "__streaming__"
            elif target.mobile_status != discord.Status.offline and target.desktop_status == discord.Status.offline:
                status_emoji = app_emojis["mobile"]
                status_str = "__online di perangkat mobile__"
            elif target.status == discord.Status.dnd:
                status_str = "dalam __mode jangan ganggu (DND)__"
            elif target.status == discord.Status.idle:
                status_str = "__idling__"
        
        accent = target.accent_color.value if getattr(target, 'accent_color', None) else 0xDE82CF
        if is_member and target.top_role and target.top_role.color.value != 0:
            accent = target.top_role.color.value
        
        container = discord.ui.Container(accent_color=accent)
        
        header_1 = f"### {'👤' if not target.bot else '🤖'}  Informasi {'Pengguna' if not target.bot else 'Bot'} — {target.mention}"
        container.add_item(discord.ui.TextDisplay(content=header_1))
        
        container.add_item(discord.ui.Separator(spacing=discord.SeparatorSpacing.small))
        
        created_at = f"<t:{int(target.created_at.timestamp())}:R> (<t:{int(target.created_at.timestamp())}:F>)"
        avatar_url = target.display_avatar.url
        
        bagian_1 = [
            f"- **Username:** __{target.name}__",
            f"- **Nama akun:** {target.global_name or 'Tidak ada'}",
            f"- **ID:** `{target.id}`",
            f"- **Dibuat:** {created_at}",
            f"- **Bot:** {'Ya' if target.bot else 'Bukan'}"
        ]
        
        badge_list = []
        if target.public_flags.hypesquad_bravery:
            badge_list.append(f"{app_emojis['hypesquad_bravery']}")
        if target.public_flags.hypesquad_brilliance:
            badge_list.append(f"{app_emojis['hypesquad_brilliance']}")
        if target.public_flags.hypesquad_balance:
            badge_list.append(f"{app_emojis['hypesquad_balance']}")
        
        for flag, value in target.public_flags:
            if value and not flag.startswith("hypesquad"):
                badge_list.append(f"🏅 {flag.replace('_', ' ').title()}")
        
        if badge_list:
            bagian_1.append(f"- **Lencana publik:** {'  '.join(badge_list)}")
        
        container.add_item(discord.ui.Section(
            discord.ui.TextDisplay(content='\n'.join(bagian_1)),
            accessory=discord.ui.Thumbnail(media=avatar_url)
        ))
        
        container.add_item(discord.ui.Separator(spacing=discord.SeparatorSpacing.small))
        
        if is_member:
            joined_at = f"<t:{int(target.joined_at.timestamp())}:R> (<t:{int(target.joined_at.timestamp())}:F>)" \
                        if target.joined_at else "tidak diketahui"
            
            join_position = "tidak diketahui"
            if ctx.guild and target.joined_at:
                sorted_members = sorted([m for m in ctx.guild.members if m.joined_at], key=lambda m: m.joined_at)
                try:
                    pos = sorted_members.index(target) + 1
                    join_position = f"ke-{pos}"
                except ValueError:
                    pass
            
            bagian_guild = [
                f"- **Nickname server:** {target.nick or 'Tidak ada'}",
                f"- **Bergabung ke server:** {joined_at}",
                f"- **Member keberapa bergabung:** {join_position}",
                f"- **Role tertinggi:** {target.top_role.mention if target.top_role else 'tidak ada'}",
            ]
            
            if target.premium_since:
                boosted_at = f"<t:{int(target.premium_since.timestamp())}:R>"
                bagian_guild.append(f"- **Mulai boost server:** {boosted_at}")
            
            if target.voice:
                vc = target.voice.channel
                vc_states = []
                
                if target.voice.mute:
                    vc_states.append(app_emojis["server_muted"])
                elif target.voice.self_mute:
                    vc_states.append(app_emojis["self_muted"])
                else:
                    vc_states.append(app_emojis["unmuted_speaking"])
                
                if target.voice.deaf:
                    vc_states.append(app_emojis["server_deafen"])
                elif target.voice.self_deaf:
                    vc_states.append(app_emojis["self_deafen"])
                
                if target.voice.self_stream:
                    vc_states.append(app_emojis["screen_sharing"])
                
                if target.voice.self_video:
                    vc_states.append(app_emojis["open_cam"])
                
                state_str = f" {' '.join(vc_states)}" if vc_states else ""
                vc_info = f"{vc.mention} {state_str}"
                bagian_guild.append(f"- **Sedang VC di:** {vc_info}")
            
            container.add_item(discord.ui.TextDisplay(content='\n'.join(bagian_guild)))
            
            container.add_item(discord.ui.Separator(spacing=discord.SeparatorSpacing.small))
            
            act_list = []
            for act in target.activities:
                if isinstance(act, discord.CustomActivity):
                    emoji = f"{act.emoji} " if act.emoji else ""
                    if not act.name or act.name == "Custom Status":
                        status_kustom = f"**Status kustom:**\n## {emoji}\n"
                    else:
                        status_kustom = f"**Status kustom:**\n> {emoji} {act.name}"
                    act_list.append(status_kustom)
                    
                elif act.type == discord.ActivityType.playing or isinstance(act, discord.Game):
                    details = f" *({act.details})*" if getattr(act, 'details', None) else ""
                    act_list.append(f"- **Bermain/membuka:** **{act.name}**{details}")
                    
                elif isinstance(act, discord.Streaming):
                    act_list.append(f"- **Streaming:** [{act.name}]({act.url})")
                    
                elif isinstance(act, discord.Spotify):
                    act_list.append(f"- **Mendengarkan Spotify:** {act.title} — *{act.artist}*")
                    
                elif act.type == discord.ActivityType.listening:
                    act_list.append(f"- **Mendengarkan:** {act.name}")
                    
                elif act.type == discord.ActivityType.watching:
                    act_list.append(f"- **Menonton:** {act.name}")
            
            if act_list:
                container.add_item(discord.ui.TextDisplay(content='\n'.join(act_list)))
                container.add_item(discord.ui.Separator(spacing=discord.SeparatorSpacing.small))
            
            roles = [r.mention for r in reversed(target.roles) if not r.is_default()]
            total_roles = len(roles)
            if total_roles > 0:
                role_text = f"- **Role ({total_roles}):** {', '.join(roles[:8])}"
                if total_roles > 8:
                    role_text += f" *(dan {total_roles - 8} role lainnya)*"
            else:
                role_text = "- **Role:** tidak memiliki role khusus."
            container.add_item(discord.ui.TextDisplay(content=role_text))
            
            container.add_item(discord.ui.Separator(spacing=discord.SeparatorSpacing.small))
            
            perms = target.guild_permissions
            perm_text = None
            
            if perms.administrator:
                perm_text = "- **Izin utama:** ⚠️ administrator (akses penuh server)"
            else:
                key_perms = []
                if perms.manage_guild: key_perms.append("kelola server")
                if perms.manage_roles: key_perms.append("kelola role")
                if perms.manage_channels: key_perms.append("kelola channel")
                if perms.kick_members or perms.ban_members: key_perms.append("kick/ban")
                if perms.moderate_members: key_perms.append("timeout")
                if perms.manage_messages: key_perms.append("kelola pesan")
                
                if key_perms:
                    perm_text = f"- **Izin utama:** {', '.join(key_perms)}"
            
            if perm_text:
                container.add_item(discord.ui.TextDisplay(content=perm_text))
                container.add_item(discord.ui.Separator(spacing=discord.SeparatorSpacing.small))
        
        footer = f"-# {status_emoji}  {target.name} saat ini sedang {status_str}."
        container.add_item(discord.ui.TextDisplay(content=footer))
        
        await ctx.send(
            view=discord.ui.LayoutView().add_item(container),
            allowed_mentions=discord.AllowedMentions.none()
        )


async def setup(bot: commands.Bot):
    await bot.add_cog(UserInfo(bot))