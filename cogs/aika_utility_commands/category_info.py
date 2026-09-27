import discord
from discord import app_commands
from discord.ext import commands


class CategoryInfo(commands.Cog):
    def __init__(self, bot:commands.Bot):
        self.bot = bot
    
    @commands.hybrid_command(
        name="categoryinfo",
        description="Menampilkan informasi detail tentang kategori saluran ini atau yang dipilih.",
        aliases=["catinfo", "category", "kategori"]
    )
    @app_commands.describe(target_category="Kategori yang ingin diperiksa")
    async def category_info(
        self,
        ctx: commands.Context,
        target_category: discord.CategoryChannel | None = None
    ):
        cat = target_category or (ctx.channel.category if hasattr(ctx.channel, 'category') else None)
        
        if cat is None:
            await ctx.send("❌ Channel ini tidak berada di dalam kategori mana pun! Silakan tentukan kategori target.", ephemeral=True)
            return
        
        thumb_url = "https://cdn.jsdelivr.net/gh/jdecked/twemoji@latest/assets/72x72/1f4c1.png"  # 📁
        
        container = discord.ui.Container(accent_color=0xD675C1)
        
        header_1 = f"### ℹ️  Informasi Kategori — {cat.name}"
        container.add_item(discord.ui.TextDisplay(content=header_1))
        
        container.add_item(discord.ui.Separator(spacing=discord.SeparatorSpacing.small))
        
        created_at = f"<t:{int(cat.created_at.timestamp())}:R> (<t:{int(cat.created_at.timestamp())}:F>)"
        detail_kategori = [
            f"- **Nama:** __{cat.name}__",
            f"- **ID:** `{cat.id}`",
            f"- **Dibuat pada:** {created_at}",
            f"- **Posisi:** `{cat.position}`",
            f"- **NSFW/18+:** {'Ya' if cat.is_nsfw() else 'Tidak'}",
            f"- **Total channel di dalam:** {len(cat.channels)}",
            f"  • Text channel: `{len(cat.text_channels)}`",
            f"  • Voice channel: `{len(cat.voice_channels)}`",
            f"  • Stage channel: `{len(cat.stage_channels)}`",
            f"  • Forum channel: `{len(cat.forums)}`"
        ]
        container.add_item(discord.ui.Section(
            discord.ui.TextDisplay(content='\n'.join(detail_kategori)),
            accessory=discord.ui.Thumbnail(media=thumb_url)
        ))
        
        if hasattr(cat, 'overwrites'):
            container.add_item(discord.ui.Separator(spacing=discord.SeparatorSpacing.small))
            container.add_item(discord.ui.TextDisplay(content=f"- **Pengecualian izin kustom:** {len(cat.overwrites)}"))
        
        await ctx.send(
            view=discord.ui.LayoutView().add_item(container),
            allowed_mentions=discord.AllowedMentions.none()
        )


async def setup(bot:commands.Bot):
    await bot.add_cog(CategoryInfo(bot))