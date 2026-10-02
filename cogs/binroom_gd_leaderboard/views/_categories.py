import datetime
import math

import discord

from .._config import META_KATEGORI_LEADERBOARD
from .._utils import atur_row_leaderboard_gd, buat_embed_gd, normalisasi_kategori_gd


class TampilanKategoriLeaderboard(discord.ui.LayoutView):
    def __init__(
        self,
        judul_kategori: str,
        data_player: list[tuple],
        kunci_stat: str,
        emoji_stat: str,
        warna_aksen: discord.Colour,
        gambar_banner: str | None = None
    ):
        super().__init__()
        
        container = discord.ui.Container(accent_color=warna_aksen)
        
        if gambar_banner:
            container.add_item(discord.ui.MediaGallery(discord.MediaGalleryItem(media=gambar_banner)))
        
        container.add_item(discord.ui.TextDisplay(content=f"## {judul_kategori}"))
        container.add_item(discord.ui.Separator(spacing=discord.SeparatorSpacing.large))
        
        tiga_besar = data_player[:3]
        sisanya = data_player[3:20]
        simbol_medali = ["<:GD_rank1:1543409072718483536>", "<:GD_rank2:1543409162438836244>", "<:GD_rank3:1543409208102232175>"]
        
        semua_nilai = [getattr(p[0], kunci_stat, 0) for p in data_player[:20]]
        max_len_stat = max([len(f"{v:,}") for v in semua_nilai], default=1)
        
        for indeks, (player, dict_db) in enumerate(tiga_besar):
            username = getattr(player, "username", dict_db.get("nama_user_gd", "Tidak Diketahui"))
            
            stars = getattr(player, "stars", 0)
            moons = getattr(player, "moons", 0)
            user_coins = getattr(player, "userCoins", 0)
            demons = getattr(player, "demons", 0)
            cp = getattr(player, "creatorPoints", 0)
            
            gambar_icon = player.get_icon_url()
            val_stat = getattr(player, kunci_stat, 0)
            str_val_padded = f"{val_stat:,}".rjust(max_len_stat)
            
            sub_stats = []
            if kunci_stat != "demons":
                sub_stats.append(f"<:hard_demon:1285063566742781984> `{demons:,}`")
            if kunci_stat != "stars":
                sub_stats.append(f"<:gd_star:1285063657839136869> `{stars:,}`")
            if kunci_stat != "moons":
                sub_stats.append(f"<:gd_moon:1285063495154536480> `{moons:,}`")
            if kunci_stat != "userCoins":
                sub_stats.append(f"<:user_coin:1543218797794697346> `{user_coins:,}`")
            if kunci_stat != "creatorPoints" and cp > 0:
                sub_stats.append(f"<:creator_icon:1543402506355212409> `{cp:,}`")
            
            teks_sub = " ".join(sub_stats)
            teks_konten = f"## {simbol_medali[indeks]} {username}\n{emoji_stat} **`{str_val_padded}`** | {teks_sub}"
            
            container.add_item(discord.ui.Section(discord.ui.TextDisplay(content=teks_konten), accessory=discord.ui.Thumbnail(media=gambar_icon)))
            if indeks < len(tiga_besar) - 1:
                container.add_item(discord.ui.Separator(spacing=discord.SeparatorSpacing.large))
        
        if sisanya:
            container.add_item(discord.ui.Separator(spacing=discord.SeparatorSpacing.large))
            baris_sisa = []
            ikon_peringkat = ["4️⃣", "5️⃣", "6️⃣", "7️⃣", "8️⃣", "9️⃣", "🔟"]
            
            for idx, (player, dict_db) in enumerate(sisanya):
                username = getattr(player, "username", dict_db.get("nama_user_gd", "Tidak Diketahui"))
                val_stat = getattr(player, kunci_stat, 0)
                str_val_padded = f"{val_stat:,}".rjust(max_len_stat)
                
                prefix = ikon_peringkat[idx] if idx < 7 else f"{idx + 4}. "
                baris_sisa.append(f"{prefix} {emoji_stat} **`{str_val_padded}`** | {username}")
                
                if idx == 6:
                    baris_sisa.append("")
            
            container.add_item(discord.ui.TextDisplay(content="\n".join(baris_sisa)))
        
        container.add_item(discord.ui.Separator(spacing=discord.SeparatorSpacing.large))
        timestamp_sekarang = int(datetime.datetime.now(datetime.timezone.utc).timestamp())
        container.add_item(discord.ui.TextDisplay(content=f"-# **Edisi: <t:{timestamp_sekarang}:D>**"))
        
        self.add_item(container)


class GDLeaderboardCategoryView(discord.ui.View):
    def __init__(self, cog, daftar_player:list[dict], category:str="stars", timeout_seconds:float=180.0):
        super().__init__(timeout=timeout_seconds)
        self.cog = cog
        self.daftar_player = daftar_player
        self.category = normalisasi_kategori_gd(category)
        self.page = 0
        self.per_page = 20
        self.message: discord.Message | None = None
        self.data = atur_row_leaderboard_gd(self.category, self.daftar_player)
        self.total_pages = max(1, math.ceil(len(self.data) / self.per_page))
        self._sync_category_buttons()
    
    def _sync_category_buttons(self):
        self.clear_items()
        
        for category_name in ["demons", "moons", "stars", "secret coins", "user coins", "diamonds", "creator points"]:
            meta = META_KATEGORI_LEADERBOARD[category_name]
            button = discord.ui.Button(
                emoji=meta["button_emoji"],
                style=meta["button_style"],
                disabled=(category_name == self.category),
                custom_id=f"gd_lb_cat_{category_name}"
            )
            
            async def handle_category(interaction: discord.Interaction, category_name=category_name):
                await self.switch_category(interaction, category_name)
            
            button.callback = handle_category
            self.add_item(button)
        
        prev_button = discord.ui.Button(emoji="◀", style=discord.ButtonStyle.success, disabled=(self.page <= 0), custom_id="gd_lb_prev")
        page_indicator_button = discord.ui.Button(label=f"{self.page + 1}/{self.total_pages}", style=discord.ButtonStyle.primary, disabled=True, custom_id="gd_lb_page_num")
        next_button = discord.ui.Button(emoji="▶", style=discord.ButtonStyle.success, disabled=(self.page >= self.total_pages - 1), custom_id="gd_lb_next")
        
        async def handle_prev(interaction: discord.Interaction):
            await self.go_previous(interaction)
        
        async def handle_next(interaction: discord.Interaction):
            await self.go_next(interaction)
        
        prev_button.callback = handle_prev
        next_button.callback = handle_next
        
        self.add_item(prev_button)
        self.add_item(page_indicator_button)
        self.add_item(next_button)
    
    def build_embed(self) -> discord.Embed:
        meta = META_KATEGORI_LEADERBOARD[self.category]
        start = self.page * self.per_page
        end = start + self.per_page
        current_players = self.data[start:end]
        
        lines = []
        value_width = max((len(f"{getattr(player, meta['key'], 0):,}") for player, _ in current_players), default=1)
        for position, (player, player_data) in enumerate(current_players, start=start + 1):
            username = getattr(player, "username", player_data.get("nama_user_gd", "Tidak Diketahui"))
            discord_id = player_data.get("id_user_discord")
            mention = f" (<@{discord_id}>)" if discord_id else ""
            value = getattr(player, meta["key"], 0)
            padded_value = f"{value:,}".rjust(value_width)
            lines.append(f"{position}. {meta['emoji']} `{padded_value}` | {username}{mention}")
        
        if not lines:
            lines.append("Belum ada data player untuk kategori ini.")
        
        embed = buat_embed_gd(
            title=meta["title"],
            description="\n".join(lines),
            color=discord.Colour(meta["accent"])
        )
        embed.set_thumbnail(url=meta["thumbnail"])
        
        if self.category == "creator points":
            subject_label = "creator"
            info_tambahan = "  ·  Hanya member yang punya CP yang ditampilkan"
        else:
            subject_label = "player"
            info_tambahan = ''
        
        embed.set_footer(text=f"Total {subject_label} terdaftar: {len(self.data)}{info_tambahan}")
        return embed
    
    async def switch_category(self, interaction:discord.Interaction, category_name:str):
        self.category = normalisasi_kategori_gd(category_name)
        self.data = atur_row_leaderboard_gd(self.category, self.daftar_player)
        self.total_pages = max(1, math.ceil(len(self.data) / self.per_page))
        self.page = 0
        self._sync_category_buttons()
        await interaction.response.edit_message(embed=self.build_embed(), view=self)
    
    async def go_previous(self, interaction:discord.Interaction):
        if self.page > 0:
            self.page -= 1
            self._sync_category_buttons()
            await interaction.response.edit_message(embed=self.build_embed(), view=self)
    
    async def go_next(self, interaction:discord.Interaction):
        if self.page < self.total_pages - 1:
            self.page += 1
            self._sync_category_buttons()
            await interaction.response.edit_message(embed=self.build_embed(), view=self)
    
    async def on_timeout(self):
        for child in self.children:
            if isinstance(child, discord.ui.Button):
                child.disabled = True
        if self.message:
            try:
                await self.message.edit(view=self)
            except discord.HTTPException:
                pass