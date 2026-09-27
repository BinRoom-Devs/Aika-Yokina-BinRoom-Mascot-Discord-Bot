import discord
from discord import app_commands
from discord.ext import commands


class ThreadCategoryInfo(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
    
    @commands.hybrid_command(
        name="threadinfo",
        description="Nampilin info tentang thread ini atau yang dipilih.",
        aliases=["tinfo", "thread"]
    )
    @app_commands.describe(target_thread="Thread yang ingin diliat infonya (Default: thread saat ini)")
    async def thread_info(
        self,
        ctx: commands.Context,
        target_thread: discord.Thread | None = None
    ):
        if target_thread is None:
            if isinstance(ctx.channel, discord.Thread):
                th = ctx.channel
            else:
                await ctx.send("❌ Channel ini bukan sebuah thread! Silakan tentukan thread target.", ephemeral=True)
                return
        else:
            th = target_thread
        
        thumb_url = "https://cdn.jsdelivr.net/gh/jdecked/twemoji@latest/assets/72x72/1f9f5.png"  # 🧵
        
        container = discord.ui.Container(accent_color=0xD675C1)
        
        header_1 = f"### ℹ️  Informasi Thread — {th.mention}"
        container.add_item(discord.ui.TextDisplay(content=header_1))
        
        container.add_item(discord.ui.Separator(spacing=discord.SeparatorSpacing.small))
        
        created_at = f"<t:{int(th.created_at.timestamp())}:R> (<t:{int(th.created_at.timestamp())}:F>)"
        detail_thread = [
            f"- **Nama:** __{th.name}__",
            f"- **ID:** `{th.id}`",
            f"- **Pembuat thread:** {th.owner.mention if th.owner else f'<@{th.owner_id}>'}",
            f"- **Dibuat pada:** {created_at}",
            f"- **Channel induk:** {th.parent.mention if th.parent else 'Tidak diketahui'}",
            f"- **Diarsipkan:** {'Ya' if th.archived else 'Tidak'}",
            f"- **Dikunci:** {'Ya' if th.locked else 'Tidak'}",
            f"- **Durasi arsip otomatis:** {th.auto_archive_duration} menit",
            f"- **Jumlah pesan:** {th.message_count}",
            f"- **Jumlah anggota:** {th.member_count}",
            f"- **Mode lambat:** {th.slowmode_delay} detik" if th.slowmode_delay else "- **Mode lambat:** Nonaktif"
        ]
        container.add_item(discord.ui.Section(
            discord.ui.TextDisplay(content='\n'.join(detail_thread)),
            accessory=discord.ui.Thumbnail(media=thumb_url)
        ))
        
        await ctx.send(
            view=discord.ui.LayoutView().add_item(container),
            allowed_mentions=discord.AllowedMentions.none()
        )


async def setup(bot:commands.Bot):
    await bot.add_cog(ThreadCategoryInfo(bot))