import discord
from discord import app_commands
from discord.ext import commands


class RoleInfo(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
    
    @commands.hybrid_command(
        name="roleinfo",
        description="Nampilin informasi lengkap tentang role.",
        aliases=["rinfo", "role"]
    )
    @app_commands.describe(target_role="Role yang ingin dilihat detailnya")
    async def role_info(
        self,
        ctx: commands.Context,
        target_role: discord.Role
    ):
        role = target_role
        guild = ctx.guild
        
        thumb_url = "https://cdn.jsdelivr.net/gh/jdecked/twemoji@latest/assets/72x72/1f3ad.png"
        
        if role.display_icon and isinstance(role.display_icon, discord.Asset):
            thumb_url = role.display_icon.url
        
        accent = role.color.value if role.color.value != 0 else 0xD675C1
        container = discord.ui.Container(accent_color=accent)
        
        header_1 = f"### ℹ️  Informasi Role — {role.mention}"
        container.add_item(discord.ui.TextDisplay(content=header_1))
        
        container.add_item(discord.ui.Separator(spacing=discord.SeparatorSpacing.small))
        
        created_at = f"<t:{int(role.created_at.timestamp())}:R> (<t:{int(role.created_at.timestamp())}:F>)"
        tipe_role = "Biasa (Standard)"
        if role.is_bot_managed():
            tipe_role = "Dikelola oleh bot/aplikasi"
        elif role.is_premium_subscriber():
            tipe_role = "Booster Server (Server Booster)"
        elif role.is_integration():
            tipe_role = "Integrasi layanan luar"
        elif role.is_default():
            tipe_role = "Role default (@everyone)"
        
        bagian_1 = [
            f"- **Nama:** __{role.name}__",
            f"- **ID:** `{role.id}`",
            f"- **Tipe Role:** {tipe_role}",
            f"- **Dibuat:** {created_at}",
            f"- **Posisi urutan:** `{role.position}` / `{len(guild.roles) - 1}`",
            f"- **Warna:** `{str(role.color).upper()}`",
        ]
        if role.unicode_emoji:
            bagian_1.append(f"- **Emoji Role:** {role.unicode_emoji}")
        container.add_item(discord.ui.Section(
            discord.ui.TextDisplay(content='\n'.join(bagian_1)),
            accessory=discord.ui.Thumbnail(media=thumb_url)
        ))
        
        container.add_item(discord.ui.Separator(spacing=discord.SeparatorSpacing.small))
        
        bagian_2 = [
            f"- **Tampil terpisah (hoist):** {'Ya' if role.hoist else 'Tidak'}",
            f"- **Dapat di-mention siapa saja:** {'Ya' if role.mentionable else 'Tidak'}",
            f"- **Dikelola sistem (managed):** {'Ya' if role.managed else 'Tidak'}",
        ]
        if role.tags:
            if role.tags.bot_id:
                bagian_2.append(f"- **Terhubung ke bot:** <@{role.tags.bot_id}>")
            if role.tags.integration_id:
                bagian_2.append(f"- **ID integrasi:** `{role.tags.integration_id}`")
            if role.tags.subscription_listing_id:
                bagian_2.append(f"- **ID monetisasi/sub:** `{role.tags.subscription_listing_id}`")
        container.add_item(discord.ui.TextDisplay(content='\n'.join(bagian_2)))
        
        container.add_item(discord.ui.Separator(spacing=discord.SeparatorSpacing.small))
        
        total_anggota = len(role.members)
        if total_anggota > 0:
            sampel_anggota = [m.mention for m in role.members[:5]]
            sisa = total_anggota - len(sampel_anggota)
            text_anggota = f"- **Total member:** {total_anggota} orang\n"
            text_anggota += f"- **Daftar (Sebagian):** {', '.join(sampel_anggota)}"
            if sisa > 0:
                text_anggota += f" *(dan {sisa} lainnya)*"
        else:
            text_anggota = "- **Total anggota:** tidak ada yang memiliki role ini."
        container.add_item(discord.ui.TextDisplay(content=text_anggota))
        
        container.add_item(discord.ui.Separator(spacing=discord.SeparatorSpacing.small))
        
        perms = role.permissions
        if perms.administrator:
            text_perm = "- **Izin utama:** ⚠️ **administrator** *(akses penuh ke seluruh server)*"
        else:
            key_perms = []
            if perms.manage_guild: key_perms.append("Kelola Server")
            if perms.manage_roles: key_perms.append("Kelola role")
            if perms.manage_channels: key_perms.append("Kelola saluran")
            if perms.kick_members or perms.ban_members: key_perms.append("Kick/ban member")
            if perms.moderate_members: key_perms.append("Timeout member")
            if perms.manage_messages: key_perms.append("Kelola pesan")
            if perms.manage_webhooks: key_perms.append("Kelola webhook")
            if perms.mention_everyone: key_perms.append("Mention @everyone")
            
            if key_perms:
                text_perm = f"- **Izin utama:** {', '.join(key_perms)}"
            else:
                text_perm = "- **Izin utama:** anggota biasa (tidak ada izin administratif khusus)"
        container.add_item(discord.ui.TextDisplay(content=text_perm))
        
        await ctx.send(
            view=discord.ui.LayoutView().add_item(container),
            allowed_mentions=discord.AllowedMentions.none()
        )
    
    @role_info.error
    async def role_info_error(self, ctx:commands.Context, error:commands.CommandError):
        if isinstance(error, commands.MissingRequiredArgument) and error.param.name == "target_role":
            await ctx.send("Masukin role yang pengen kamu liat infonya.\nContoh: `!roleinfo @Admin` atau `!roleinfo 123456789012345678`", ephemeral=True)
            return
        
        if isinstance(error, commands.RoleNotFound):
            await ctx.send("❌ Role yang kamu masukin gak ditemukan.", ephemeral=True)
            return
        
        else:
            raise error


async def setup(bot:commands.Bot):
    await bot.add_cog(RoleInfo(bot))