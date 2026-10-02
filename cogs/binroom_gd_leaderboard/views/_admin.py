import datetime
import math

import discord

from .._utils import buat_embed_gd, load_daftar_player_async, simpan_daftar_player_async


class TampilanKonfirmasiHapus(discord.ui.View):
    def __init__(self, target_player:dict, timeout_seconds:float=60.0):
        super().__init__(timeout=timeout_seconds)
        self.target_player = target_player
        self.pesan: discord.WebhookMessage | None = None
    
    async def on_timeout(self):
        embed_timeout = buat_embed_gd(
            description="<:GD_x:1543409414843662346> <:GD_trash:1543822477153800353> Sesi konfirmasi penghapusan telah kadaluarsa.",
            color=discord.Color.red()
        )
        if self.pesan:
            try:
                await self.pesan.edit(embed=embed_timeout, view=None)
            except discord.HTTPException:
                pass
    
    @discord.ui.button(label="Konfirmasi Hapus", style=discord.ButtonStyle.danger)
    async def konfirmasi_hapus(self, interaksi:discord.Interaction, tombol:discord.ui.Button):
        daftar_player = await load_daftar_player_async()
        target_acc_id = self.target_player.get("account_id_gd")
        target_name = self.target_player.get("nama_user_gd")
        
        daftar_baru = [p for p in daftar_player if not (p.get("account_id_gd") == target_acc_id or p.get("nama_user_gd").lower() == target_name.lower())]
        
        if len(daftar_baru) == len(daftar_player):
            await interaksi.response.edit_message(
                embed=None,
                content=f"<:GD_x:1543409414843662346> Gagal: Player **{target_name}** tidak ditemukan di database.",
                view=None
            )
            self.stop()
            return
        
        await simpan_daftar_player_async(daftar_baru)
        
        embed_berhasil = buat_embed_gd(
            title="<:GD_complete:1543409457940267078> <:GD_trash:1543822477153800353> Player dihapus",
            description=f"**{target_name}** telah dihapus dari leaderboard GD BinRoom.",
            color=discord.Color.green()
        )
        
        await interaksi.response.edit_message(content="<:GD_complete:1543409457940267078> Penghapusan selesai.", embed=None, view=None)
        await interaksi.channel.send(embed=embed_berhasil)
        self.stop()
    
    @discord.ui.button(label="Batal", style=discord.ButtonStyle.secondary)
    async def tombol_batal(self, interaksi:discord.Interaction, tombol:discord.ui.Button):
        embed_batal = buat_embed_gd(
            description="<:GD_x:1543409414843662346> <:GD_trash:1543822477153800353> Proses penghapusan player dibatalkan."
        )
        await interaksi.response.edit_message(embed=embed_batal, view=None)
        self.stop()


class SelectPilihHapusPlayer(discord.ui.Select):
    def __init__(self, daftar_player:list[dict], parent_view:"MenuPilihHapusPlayer"):
        players_sorted = sorted(daftar_player, key=lambda p: p.get("nama_user_gd", "").lower())
        options = [
            discord.SelectOption(
                label=p.get("nama_user_gd", "Tidak Diketahui"),
                value=str(p.get("account_id_gd", 0))
            )
            for p in players_sorted
        ]
        
        super().__init__(
            placeholder="Pilih player yang ingin dihapus...",
            min_values=1,
            max_values=1,
            options=options
        )
        self.parent_view = parent_view
    
    async def callback(self, interaksi:discord.Interaction):
        selected_acc_id = int(self.values[0])
        target_player = next((p for p in self.parent_view.semua_player if p.get("account_id_gd") == selected_acc_id), None)
        
        if not target_player:
            await interaksi.response.send_message("<:GD_x:1543409414843662346> Player tidak ditemukan!", ephemeral=True)
            return
        
        self.parent_view.stop()
        nama_target = target_player.get("nama_user_gd")
        waktu_kadaluarsa = int(datetime.datetime.now(datetime.timezone.utc).timestamp() + 60.0)
        
        view_konfirmasi = TampilanKonfirmasiHapus(target_player, timeout_seconds=60.0)
        embed_konfirmasi = buat_embed_gd(
            title="<:GD_exmark:1543821165141696613> Konfirmasi penghapusan",
            description=(
                f"Yakin ingin menghapus player **{nama_target}** dari leaderboard GD BinRoom?\n\n"
                f"-# Batal otomatis <t:{waktu_kadaluarsa}:R>"
            ),
            color=discord.Color.red()
        )
        
        await interaksi.response.edit_message(embed=embed_konfirmasi, view=view_konfirmasi)
        view_konfirmasi.pesan = await interaksi.original_response()


class MenuPilihHapusPlayer(discord.ui.View):
    def __init__(self, daftar_player:list[dict], timeout_seconds:float=60.0):
        super().__init__(timeout=timeout_seconds)
        self.semua_player = sorted(daftar_player, key=lambda p: p.get("nama_user_gd", "").lower())
        self.halaman = 0
        self.max_per_halaman = 25
        self.total_halaman = math.ceil(len(self.semua_player) / self.max_per_halaman)
        self.pesan: discord.WebhookMessage | None = None
        self.waktu_kadaluarsa = int(datetime.datetime.now(datetime.timezone.utc).timestamp() + timeout_seconds)
        
        self.perbarui_komponen()
    
    def get_content(self):
        embed_penghapusan = buat_embed_gd(
            title="<:GD_trash:1543822477153800353> Penghapusan player",
            description=(
                "Silakan pilih player yang ingin dihapus dari leaderboard GD BinRoom\n\n"
                f"-# Halaman {self.halaman+1}/{self.total_halaman} • Batal otomatis <t:{self.waktu_kadaluarsa}:R>"
            ),
            color=discord.Color.gold()
        )
        return embed_penghapusan
    
    def perbarui_komponen(self):
        self.clear_items()
        
        mulai = self.halaman * self.max_per_halaman
        selesai = mulai + self.max_per_halaman
        chunk_saat_ini = self.semua_player[mulai:selesai]
        
        self.add_item(SelectPilihHapusPlayer(chunk_saat_ini, self))
        
        tombol_prev = discord.ui.Button(label="◀", style=discord.ButtonStyle.secondary, disabled=(self.halaman == 0), custom_id="btn_prev_page")
        tombol_next = discord.ui.Button(label="▶", style=discord.ButtonStyle.secondary, disabled=(self.halaman >= self.total_halaman - 1), custom_id="btn_next_page")
        tombol_batal = discord.ui.Button(label="Batal", style=discord.ButtonStyle.secondary, custom_id="btn_cancel_select")
        
        tombol_prev.callback = self.halaman_sebelumnya
        tombol_next.callback = self.halaman_selanjutnya
        tombol_batal.callback = self.tombol_batal_select
        
        self.add_item(tombol_prev)
        self.add_item(tombol_next)
        self.add_item(tombol_batal)
    
    async def halaman_sebelumnya(self, interaksi:discord.Interaction):
        if self.halaman > 0:
            self.halaman -= 1
            self.perbarui_komponen()
            await interaksi.response.edit_message(embed=self.get_content(), view=self)
    
    async def halaman_selanjutnya(self, interaksi:discord.Interaction):
        if self.halaman < self.total_halaman - 1:
            self.halaman += 1
            self.perbarui_komponen()
            await interaksi.response.edit_message(embed=self.get_content(), view=self)
    
    async def tombol_batal_select(self, interaksi:discord.Interaction):
        embed_batal = buat_embed_gd(
            description="<:GD_x:1543409414843662346> <:GD_trash:1543822477153800353> Sesi pemilihan player dibatalkan.",
            color=discord.Color.dark_gray()
        )
        await interaksi.response.edit_message(embed=embed_batal, view=None)
        self.stop()
    
    async def on_timeout(self):
        for child in self.children:
            child.disabled = True
        if self.pesan:
            try:
                await self.pesan.edit(content="⌛ Sesi pemilihan player telah berakhir (waktu habis).", embed=None, view=self)
            except discord.HTTPException:
                pass