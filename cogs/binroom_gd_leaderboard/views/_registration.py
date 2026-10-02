import datetime
import random
import string

import discord

from .._config import NAMA_AKUN_GD_BOT, PENYIMPANAN_VERIFIKASI
from .._utils import (
    baca_pesan_masuk_gd,
    buat_embed_gd,
    cari_profil_gd,
    cek_koneksi_robtop,
    load_daftar_player_async,
    simpan_daftar_player_async,
)
from ._categories import GDLeaderboardCategoryView


class PopUpPendaftaran(discord.ui.Modal):
    input_username_gd = discord.ui.TextInput(
        label="Username GD-mu (huruf kapital)", 
        placeholder="Contoh: TheHx",
        required=True,
    )
    
    def __init__(self, cog_leaderboard):
        super().__init__(title="Pendaftaran Leaderboard GD BinRoom")
        self.cog_leaderboard = cog_leaderboard
    
    async def on_submit(self, interaksi:discord.Interaction):
        await interaksi.response.defer(ephemeral=True)
        nama_input = self.input_username_gd.value.strip()
        
        data_user = await cari_profil_gd(self.cog_leaderboard.session, nama_input)
        discord_user_id = interaksi.user.id
        
        if not data_user:
            await interaksi.followup.send(f"<:GD_x:1543409414843662346> Username GD **{nama_input}** tidak ditemukan.", ephemeral=True)
            return
        
        account_id, player_id, nama_asli = data_user
        daftar_player = await load_daftar_player_async()
        
        sudah_terdaftar = any(
            p.get("id_user_discord") == discord_user_id or p.get("account_id_gd") == account_id
            for p in daftar_player
        )
        if sudah_terdaftar:
            await interaksi.followup.send(f"ℹ️ Kamu atau akun GD **{nama_asli}** sudah terdaftar di leaderboard!", ephemeral=True)
            return
        
        kode_random = f"VERIFY-{''.join(random.choices(string.ascii_uppercase + string.digits, k=6))}"
        PENYIMPANAN_VERIFIKASI[interaksi.user.id] = {
            "username": nama_asli,
            "kode": kode_random,
            "account_id": account_id,
            "id_player": player_id
        }
        
        embed_instruksi = buat_embed_gd(
            title="Verifikasi Akun",
            description=(
                f"Untuk memverifikasi bahwa akun **{nama_asli}** benar milikmu:\n\n"
                f"1. <:GD_logo:1543417301175640126> Buka Geometry Dash.\n"
                f"2. <:GD_usersearch:1543408830719729756> Cari profil bot: **{NAMA_AKUN_GD_BOT}**\n"
                f"3. <:GD_accountBtn_messages:1543408766555259000> Kirim pesan ke akun bot tersebut dengan:\n"
                f"   - Subject/judul: `{kode_random}`\n"
                f"   - Isi pesan: *opsional*\n"
                f"4. <:GD_achImage:1543417920389124257> Setelah pesan terkirim, tekan tombol **Verifikasi** di bawah."
            ),
            color=0xFFAC33
        )
        embed_instruksi.set_thumbnail(url="https://cdn.discordapp.com/attachments/863959650448703538/1543577215629795360/GJ_bigGoldKey_001.png?ex=6a955fce&is=6a940e4e&hm=058ba4a94ebaaca9d4d5c43868676f685eacec199a2c001f3cfe21ff9533878b&")
        
        waktu_kadaluarsa = datetime.datetime.now(datetime.timezone.utc) + datetime.timedelta(minutes=2)
        embed_instruksi.description += f"\n\n⏳ **Kadaluarsa** <t:{int(waktu_kadaluarsa.timestamp())}:R>"
        
        tampilan_konfirmasi = TombolKonfirmasiVerifikasi(self.cog_leaderboard, interaksi.user.id)
        
        pesan = await interaksi.followup.send(
            embed=embed_instruksi, 
            view=tampilan_konfirmasi, 
            ephemeral=True, 
            wait=True
        )
        tampilan_konfirmasi.message = pesan


class TampilanRegistrasiContainer(discord.ui.View):
    def __init__(self, cog_leaderboard=None):
        super().__init__(timeout=None)
        self.cog_leaderboard = cog_leaderboard
    
    @discord.ui.button(
        label="Daftarkan akunmu",
        style=discord.ButtonStyle.secondary,
        custom_id="gd_leaderboard_tombol_daftar_v1"
    )
    async def callback_daftar(self, interaksi: discord.Interaction, tombol: discord.ui.Button):
        await interaksi.response.defer(ephemeral=True)
        
        players = await load_daftar_player_async()
        if any(p.get("id_user_discord") == interaksi.user.id for p in players):
            await interaksi.followup.send("Kamu sudah terdaftar!", ephemeral=True)
            return
        
        session = self.cog_leaderboard.session
        koneksi_aman = await cek_koneksi_robtop(session)
        pesan_uji = await baca_pesan_masuk_gd(session)
        
        if not koneksi_aman or not pesan_uji:
            await interaksi.followup.send(
                "<:GD_x:1543409414843662346> Opsi ini belum tersedia untuk sekarang.\n Silakan hubungi admin jika ingin mendaftar.", 
                ephemeral=True
            )
            return
        
        await interaksi.response.send_modal(PopUpPendaftaran(self.cog_leaderboard))
    
    @discord.ui.button(
        label="Lihat leaderboard lengkap",
        style=discord.ButtonStyle.secondary,
        custom_id="gd_leaderboard_tombol_lengkap_v1"
    )
    async def callback_lihat_lengkap(self, interaksi: discord.Interaction, tombol: discord.ui.Button):
        players = await load_daftar_player_async()
        view = GDLeaderboardCategoryView(self.cog_leaderboard, players, "stars", timeout_seconds=180.0)
        await interaksi.response.send_message(embed=view.build_embed(), view=view, ephemeral=True)
        view.message = interaksi.message
    
    async def generate_embed_async(self) -> discord.Embed:
        daftar_player = await load_daftar_player_async()
        jumlah_player = len(daftar_player)
        
        embed = discord.Embed(
            description=(
                f"Jumlah terdaftar di leaderboard BinRoom: **{jumlah_player}** player.\n"
                f"Hanya top 20 ditampilkan. Namamu gak masuk? Semangat grinding-nya~\n\n"
                f"Mau cek leaderboard selengkapnya? Gunakan `/leaderboard gd` atau klik tombol di bawah.\n\n"
                f"Mau join leaderboard BinRoom? Klik tombol **Daftarkan akunmu** di bawah."
            ),
            color=0xFFE700
        ).set_thumbnail(url="https://cdn.discordapp.com/attachments/863959650448703538/1543780342379319337/rankIcon_1_001.png?ex=6a961cfb&is=6a94cb7b&hm=33bf6524a61776ae3bf21ccd07c9aab07260085a9c0dddf098ad73ea4bd19f59&")
        return embed


class TombolKonfirmasiVerifikasi(discord.ui.View):
    def __init__(self, cog_leaderboard, user_id: int):
        super().__init__(timeout=120.0)
        self.cog_leaderboard = cog_leaderboard
        self.user_id = user_id
        self.message: discord.WebhookMessage | None = None
    
    @discord.ui.button(label="Verifikasi", style=discord.ButtonStyle.green)
    async def konfirmasi_verifikasi(self, interaksi:discord.Interaction, tombol:discord.ui.Button):
        await interaksi.response.defer(ephemeral=True)
        
        if self.user_id not in PENYIMPANAN_VERIFIKASI:
            embed_gagal = buat_embed_gd(
                title="<:GD_x:1543409414843662346> Verifikasi gagal",
                description="Sesi verifikasi kamu sudah kedaluwarsa.\nSilakan klik tombol pendaftaran ulang di channel.",
                color=discord.Color.red()
            )
            await interaksi.edit_original_response(embed=embed_gagal, view=None)
            self.stop()
            return
        
        data_sesi = PENYIMPANAN_VERIFIKASI[self.user_id]
        kode_diharapkan = data_sesi["kode"]
        target_accountid = data_sesi["account_id"]
        target_userid_player = data_sesi.get("id_player", 0)
        nama_target = data_sesi["username"]
        
        pesan_masuk = await baca_pesan_masuk_gd(self.cog_leaderboard.session)
        berhasil_verifikasi = any(pesan["pengirim"].lower() == nama_target.lower() and kode_diharapkan in pesan["subjek"] for pesan in pesan_masuk)
        
        if berhasil_verifikasi:
            del PENYIMPANAN_VERIFIKASI[self.user_id]
            daftar_player = await load_daftar_player_async()
            player_ada = next((p for p in daftar_player if p.get("account_id_gd") == target_accountid or p.get("nama_user_gd").lower() == nama_target.lower()), None)
            
            if player_ada:
                player_ada["id_user_discord"] = self.user_id
                player_ada["account_id_gd"] = target_accountid
                player_ada["player_id_gd"] = target_userid_player
            else:
                data_player_baru = {
                    "nama_user_gd": nama_target,
                    "account_id_gd": target_accountid,
                    "player_id_gd": target_userid_player,
                    "id_user_discord": self.user_id,
                    "statistik": {
                        "stars": 0, "moons": 0, "diamonds": 0,
                        "secret_coins": 0, "user_coins": 0, "demons": 0, "creator_points": 0
                    }
                }
                daftar_player.append(data_player_baru)
            
            await simpan_daftar_player_async(daftar_player)
            
            embed_sukses = buat_embed_gd(
                title="<:GD_complete:1543409457940267078> Verifikasi berhasil!",
                description=f"Akun **{nama_target}** berhasil didaftarkan ke leaderboard BinRoom\nHappy grinding!",
                color=discord.Color.green()
            )
            
            await interaksi.edit_original_response(content="<:GD_complete:1543409457940267078> Verifikasi selesai!", embed=None, view=None)
            await interaksi.channel.send(embed=embed_sukses)
            self.stop()
        else:
            await interaksi.followup.send("<:GD_x:1543409414843662346> Pesan tidak ditemukan! Ikuti langkah di atas dengan seksama dan coba lagi.", ephemeral=True)
    
    @discord.ui.button(label="Batal", style=discord.ButtonStyle.red)
    async def tombol_batal(self, interaksi:discord.Interaction, tombol:discord.ui.Button):
        if self.user_id in PENYIMPANAN_VERIFIKASI:
            del PENYIMPANAN_VERIFIKASI[self.user_id]
        
        embed_batal = buat_embed_gd(
            title="<:GD_x:1543409414843662346> Dibatalkan",
            description="Proses verifikasi telah dibatalkan.",
            color=discord.Color.red()
        )
        await interaksi.response.edit_message(embed=embed_batal, view=None)
        self.stop()
    
    async def on_timeout(self):
        if self.user_id in PENYIMPANAN_VERIFIKASI:
            del PENYIMPANAN_VERIFIKASI[self.user_id]
            if self.message:
                embed_timeout = buat_embed_gd(
                    title="⌛ Waktu Habis",
                    description="Sesi verifikasi ini sudah kadaluarsa karena melewati batas 2 menit. Silakan daftar ulang jika ingin melanjutkan.",
                    color=discord.Color.red()
                )
                try:
                    await self.message.edit(embed=embed_timeout, view=None)
                except discord.HTTPException:
                    pass