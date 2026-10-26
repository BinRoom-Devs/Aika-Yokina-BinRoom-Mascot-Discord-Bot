import asyncio
import io

import aiohttp
import discord
from discord import app_commands
from discord.ext import commands

#from PIL import Image, ImageDraw (baris 57)
import config


class UserInfo(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self._session: aiohttp.ClientSession | None = None
    
    @property
    def session(self) -> aiohttp.ClientSession:
        if self._session is None or self._session.closed:
            self._session = aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=10))
        return self._session
    
    async def cog_unload(self):
        if self._session and not self._session.closed:
            await self._session.close()
    
    async def baca_application_emojis(self) -> dict[str, str]:
        fallback = {
            "online": "🟢", "idle": "🌙", "dnd": "⛔", "offline": "⚪",
            "streaming": "🟣", "mobile": "📱", "hypesquad_bravery": "🛡️",
            "hypesquad_brilliance": "💎", "hypesquad_balance": "⚖️",
            "server_muted": "🔇", "server_deafen": "🔇", "self_deafen": "🔇",
            "screen_sharing": "🖥️", "unmuted_speaking": "🎤", "open_cam": "📹",
            "self_muted": "🎤",
        }
        try:
            emojis = await self.bot.fetch_application_emojis()
            get_e = lambda name: discord.utils.get(emojis, name=name)
            return {
                k: str(get_e(v)) if get_e(v) else fallback[k]
                for k, v in {
                    "online": "available_online", "idle": "idle", "dnd": "do_not_disturb",
                    "offline": "offline_or_invisible", "streaming": "streaming", "mobile": "online_mobile",
                    "hypesquad_bravery": "hypesquad_bravery", "hypesquad_brilliance": "hypesquad_brilliance",
                    "hypesquad_balance": "hypesquad_balance", "server_muted": "server_muted",
                    "server_deafen": "server_deafen", "self_deafen": "self_deafen",
                    "screen_sharing": "screen_sharing", "unmuted_speaking": "unmuted_speaking",
                    "open_cam": "open_cam", "self_muted": "self_muted",
                }.items()
            }
        except Exception:  # noqa: BLE001
            return fallback
    
    @staticmethod
    def _gabung_avatar_frame_blocking(avatar_bytes: bytes, frame_bytes: bytes | None) -> tuple[bytes, str]:
        from PIL import Image, ImageDraw
        
        canvas_size = 256
        avatar_size = int(canvas_size * 0.78)
        offset = (canvas_size - avatar_size) // 2
        
        mask = Image.new("L", (avatar_size, avatar_size), 0)
        draw = ImageDraw.Draw(mask)
        draw.ellipse((0, 0, avatar_size, avatar_size), fill=255)
        
        try:
            with Image.open(io.BytesIO(avatar_bytes)) as avatar_img:
                avatar_animated = getattr(avatar_img, "is_animated", False)
                avatar_n_frames = getattr(avatar_img, "n_frames", 1) if avatar_animated else 1
                avatar_duration = avatar_img.info.get('duration', 40)
                
                frame_animated = False
                frame_n_frames = 1
                frame_duration = 40
                frame_img = None
                
                if frame_bytes:
                    try:
                        frame_img = Image.open(io.BytesIO(frame_bytes))
                        frame_animated = getattr(frame_img, "is_animated", False)
                        frame_n_frames = getattr(frame_img, "n_frames", 1) if frame_animated else 1
                        frame_duration = frame_img.info.get('duration', 40)
                    except Exception:  # noqa: BLE001
                        frame_img = None
                
                if not avatar_animated and not frame_animated:
                    avatar = avatar_img.convert("RGBA").resize((avatar_size, avatar_size), Image.Resampling.LANCZOS)
                    base = Image.new("RGBA", (canvas_size, canvas_size), (0, 0, 0, 0))
                    base.paste(avatar, (offset, offset), mask)
                    
                    if frame_img:
                        with frame_img.convert("RGBA") as f_img:
                            f_img = f_img.resize((canvas_size, canvas_size), Image.Resampling.LANCZOS)
                            base.paste(f_img, (0, 0), f_img)
                        frame_img.close()
                    
                    output = io.BytesIO()
                    base.save(output, format="PNG")
                    output.seek(0)
                    return output.read(), "avatar_frame.png"
                
                total_frames = max(avatar_n_frames, frame_n_frames)
                duration = max(avatar_duration, frame_duration)
                frames_output = []
                
                for i in range(total_frames):
                    base = Image.new("RGBA", (canvas_size, canvas_size), (0, 0, 0, 0))
                    
                    if avatar_animated:
                        avatar_img.seek(i % avatar_n_frames)
                    curr_avatar = avatar_img.convert("RGBA").resize((avatar_size, avatar_size), Image.Resampling.BILINEAR)
                    
                    avatar_masked = Image.new("RGBA", (avatar_size, avatar_size), (0, 0, 0, 0))
                    avatar_masked.paste(curr_avatar, (0, 0), mask)
                    
                    base.paste(avatar_masked, (offset, offset), avatar_masked)
                    
                    if frame_img:
                        if frame_animated:
                            frame_img.seek(i % frame_n_frames)
                        curr_frame = frame_img.convert("RGBA").resize((canvas_size, canvas_size), Image.Resampling.BILINEAR)
                        base.paste(curr_frame, (0, 0), curr_frame)
                    
                    p_frame = base.convert("P", palette=Image.Palette.ADAPTIVE, colors=255)
                    mask_transparan = base.split()[3].point(lambda p: 255 if p < 128 else 0)
                    p_frame.paste(255, mask_transparan)
                    
                    frames_output.append(p_frame)
                
                if frame_img:
                    frame_img.close()
                
                output = io.BytesIO()
                if frames_output:
                    frames_output[0].save(
                        output,
                        format="GIF",
                        save_all=True,
                        append_images=frames_output[1:],
                        duration=duration,
                        loop=0,
                        transparency=255,
                        disposal=2
                    )
                output.seek(0)
                return output.read(), "avatar_frame.gif"
        except Exception:  # noqa: BLE001
            return avatar_bytes, "avatar.png"
    
    async def _unduh_bytes(self, url: str) -> bytes | None:
        try:
            async with self.session.get(url) as resp:
                if resp.status == 200:
                    return await resp.read()
        except Exception:  # noqa: BLE001, S110
            pass
        return None
    
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
        await ctx.defer()
        
        target = target_user or ctx.author
        if ctx.guild and isinstance(target, discord.User):
            target = ctx.guild.get_member(target.id) or target
        
        if not hasattr(target, "avatar_decoration") or target.avatar_decoration is None:
            try:
                target = await self.bot.fetch_user(target.id)
            except discord.HTTPException:
                pass
        
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
        
        accent = target.accent_color.value if getattr(target, 'accent_color', None) else config.pengaturan.warna_aika
        if is_member and target.top_role and target.top_role.color.value != 0:
            accent = target.top_role.color.value
        
        container = discord.ui.Container(accent_color=accent)
        header_1 = f"### {'👤' if not target.bot else '🤖'}  Informasi {'Pengguna' if not target.bot else 'Bot'} — {target.mention}"
        container.add_item(discord.ui.TextDisplay(content=header_1))
        container.add_item(discord.ui.Separator(spacing=discord.SeparatorSpacing.small))
        
        created_at = f"<t:{int(target.created_at.timestamp())}:R> (<t:{int(target.created_at.timestamp())}:F>)"
        
        avatar_obj = target.display_avatar
        avatar_url = avatar_obj.with_size(4096).url
        
        decoration = getattr(target, "avatar_decoration", None)
        decoration_url = decoration.with_size(4096).url if decoration else None
        
        container_sementara = discord.ui.Container(accent_color=accent)
        container_sementara.add_item(discord.ui.TextDisplay(content=header_1))
        container_sementara.add_item(discord.ui.Separator(spacing=discord.SeparatorSpacing.small))
        
        bagian_1 = [
            f"- **Username:** __{target.name}__",
            f"- **Nama akun:** {target.global_name or 'Tidak ada'}",
            f"- **ID:** `{target.id}`",
            f"- **Dibuat:** {created_at}",
            f"- **Bot:** {'Ya' if target.bot else 'Bukan'}"
        ]
        
        badge_list = []
        if target.public_flags.hypesquad_bravery:
            badge_list.append(f"{app_emojis['hypesquad_bravery']} HypeSquad Bravery")
        if target.public_flags.hypesquad_brilliance:
            badge_list.append(f"{app_emojis['hypesquad_brilliance']} HypeSquad Brilliance")
        if target.public_flags.hypesquad_balance:
            badge_list.append(f"{app_emojis['hypesquad_balance']} HypeSquad Balance")
        
        for flag, value in target.public_flags:
            if value and not flag.startswith("hypesquad"):
                badge_list.append(f"🏅 {flag.replace('_', ' ').title()}")
        
        if badge_list:
            bagian_1.append(f"- **Lencana publik:** {', '.join(badge_list)}")
        
        container_sementara.add_item(discord.ui.Section(
            discord.ui.TextDisplay(content='\n'.join(bagian_1)),
            accessory=discord.ui.Thumbnail(media=avatar_url)
        ))
        
        container_sementara.add_item(discord.ui.Separator(spacing=discord.SeparatorSpacing.small))
        
        if is_member:
            joined_at = f"<t:{int(target.joined_at.timestamp())}:R> (<t:{int(target.joined_at.timestamp())}:F>)" if target.joined_at else "tidak diketahui"
            join_position = "tidak diketahui"
            if ctx.guild and target.joined_at:
                sorted_members = sorted([m for m in ctx.guild.members if m.joined_at], key=lambda m: m.joined_at)
                try:
                    pos = sorted_members.index(target) + 1
                    join_position = f"ke-{pos}"
                except ValueError:
                    pass
            
            bagian_guild = [
                f"- **Nickname Server:** {target.nick or 'Tidak ada'}",
                f"- **Bergabung ke Server:** {joined_at}",
                f"- **Member keberapa bergabung:** {join_position}",
                f"- **Role Tertinggi:** {target.top_role.mention if target.top_role else 'Tidak ada'}",
            ]
            
            if target.premium_since:
                boosted_at = f"<t:{int(target.premium_since.timestamp())}:R>"
                bagian_guild.append(f"- **Mulai Boost Server:** {boosted_at}")
            
            if target.voice:
                vc = target.voice.channel
                vc_info = f"{vc.mention}"
                if target.voice.self_mute or target.voice.mute: vc_info += " (Muted)"
                if target.voice.self_deaf or target.voice.deaf: vc_info += " (Deafened)"
                if target.voice.self_stream: vc_info += " (Live/Screen Share)"
                bagian_guild.append(f"- **Sedang VC di:** {vc_info}")
            
            container_sementara.add_item(discord.ui.TextDisplay(content='\n'.join(bagian_guild)))
            container_sementara.add_item(discord.ui.Separator(spacing=discord.SeparatorSpacing.small))
            
            act_list = []
            for act in target.activities:
                if isinstance(act, discord.CustomActivity):
                    emoji = f"{act.emoji} " if act.emoji else ""
                    if not act.name or act.name == "Custom Status":
                        status_kustom = f"**Status Kustom:**\n## {emoji}\n"
                    else:
                        status_kustom = f"**Status Kustom:**\n> {emoji} {act.name}"
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
            
            if not act_list:
                act_list.append("- **Aktivitas:** Tidak ada aktivitas aktif.")
            
            container_sementara.add_item(discord.ui.TextDisplay(content='\n'.join(act_list)))
            container_sementara.add_item(discord.ui.Separator(spacing=discord.SeparatorSpacing.small))
            
            roles = [r.mention for r in reversed(target.roles) if not r.is_default()]
            total_roles = len(roles)
            if total_roles > 0:
                role_text = f"- **Role ({total_roles}):** {', '.join(roles[:8])}"
                if total_roles > 8:
                    role_text += f" *(dan {total_roles - 8} role lainnya)*"
            else:
                role_text = "- **Role:** Tidak memiliki role khusus."
            container_sementara.add_item(discord.ui.TextDisplay(content=role_text))
            container_sementara.add_item(discord.ui.Separator(spacing=discord.SeparatorSpacing.small))
            
            perms = target.guild_permissions
            if perms.administrator:
                perm_text = "- **Izin Kunci:** ⚠️ administrator (akses penuh server)"
            else:
                key_perms = []
                if perms.manage_guild: key_perms.append("Kelola Server")
                if perms.manage_roles: key_perms.append("Kelola Role")
                if perms.manage_channels: key_perms.append("Kelola Saluran")
                if perms.kick_members or perms.ban_members: key_perms.append("Kick/Ban")
                if perms.moderate_members: key_perms.append("Timeout")
                if perms.manage_messages: key_perms.append("Kelola Pesan")
                
                perm_text = f"- **Izin Kunci:** {', '.join(key_perms)}" if key_perms else "- **Izin Kunci:** Anggota Biasa"
            container_sementara.add_item(discord.ui.TextDisplay(content=perm_text))
            container_sementara.add_item(discord.ui.Separator(spacing=discord.SeparatorSpacing.small))
        
        footer = f"-# {status_emoji}  {target.name} saat ini sedang {status_str}."
        container_sementara.add_item(discord.ui.TextDisplay(content=f"{footer}  •  Memuat ikon avatar beserta animasi frame..."))
        
        view_sementara = discord.ui.LayoutView().add_item(container_sementara)
        pesan_terkirim = await ctx.reply(view=view_sementara, allowed_mentions=discord.AllowedMentions.none())
        
        avatar_bytes, frame_bytes = await asyncio.gather(
            self._unduh_bytes(avatar_url),
            self._unduh_bytes(decoration_url)
        )
        
        if avatar_bytes:
            img_bytes, filename = await asyncio.to_thread(
                self._gabung_avatar_frame_blocking, avatar_bytes, frame_bytes
            )
            file_lampiran = discord.File(io.BytesIO(img_bytes), filename=filename)
            thumbnail_target = f"attachment://{filename}"
            
            container_final = discord.ui.Container(accent_color=accent)
            container_final.add_item(discord.ui.TextDisplay(content=header_1))
            container_final.add_item(discord.ui.Separator(spacing=discord.SeparatorSpacing.small))
            container_final.add_item(discord.ui.Section(
                discord.ui.TextDisplay(content='\n'.join(bagian_1)),
                accessory=discord.ui.Thumbnail(media=thumbnail_target)
            ))
            container_final.add_item(discord.ui.Separator(spacing=discord.SeparatorSpacing.small))
            
            if is_member:
                container_final.add_item(discord.ui.TextDisplay(content='\n'.join(bagian_guild)))
                container_final.add_item(discord.ui.Separator(spacing=discord.SeparatorSpacing.small))
                container_final.add_item(discord.ui.TextDisplay(content='\n'.join(act_list)))
                container_final.add_item(discord.ui.Separator(spacing=discord.SeparatorSpacing.small))
                container_final.add_item(discord.ui.TextDisplay(content=role_text))
                container_final.add_item(discord.ui.Separator(spacing=discord.SeparatorSpacing.small))
                container_final.add_item(discord.ui.TextDisplay(content=perm_text))
                container_final.add_item(discord.ui.Separator(spacing=discord.SeparatorSpacing.small))
            
            container_final.add_item(discord.ui.TextDisplay(content=footer))
            
            view_final = discord.ui.LayoutView().add_item(container_final)
            
            try:
                await pesan_terkirim.edit(
                    view=view_final,
                    attachments=[file_lampiran],
                    allowed_mentions=discord.AllowedMentions.none()
                )
            except discord.HTTPException:
                pass


async def setup(bot: commands.Bot):
    await bot.add_cog(UserInfo(bot))