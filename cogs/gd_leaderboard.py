import discord, database, asyncio, aiohttp, datetime, os, random, string, math
from discord import app_commands
from discord.ext import commands, tasks
from dotenv import load_dotenv

load_dotenv()

ID_CHANNEL_LEADERBOARD = 1545795446214098975 

NAMA_AKUN_GD_BOT = "AikaBot"
account_id_gd_BOT = 43800101
HASH_GJP2_BOT = os.getenv("HASH_GJP2_BOT")
BOOMLINGS_SECRET = os.getenv("BOOMLINGS_SECRET")

GAMBAR_HEADER = "https://cdn.discordapp.com/attachments/863959650448703538/1543244407145373829/Untitled-1.png"
AUTHOR_ICON_LEADERBOARD = "https://cdn.discordapp.com/attachments/863959650448703538/1543780342379319337/rankIcon_1_001.png?ex=6a961cfb&is=6a94cb7b&hm=33bf6524a61776ae3bf21ccd07c9aab07260085a9c0dddf098ad73ea4bd19f59&"
AUTHOR_NAME_LEADERBOARD = "BinRoom Geometry Dash Players Leaderboard"


class GDPlayer:
    __slots__ = (
        "username", "accountID", "playerID", "stars", "moons", 
        "diamonds", "secretCoins", "userCoins", "demons", 
        "creatorPoints", "icon", "color1", "color2", "glow"
    )

    def __init__(self, data: dict):
        self.username = data.get("username", "Tidak Diketahui")
        self.accountID = int(data.get("accountID", 0))
        self.playerID = int(data.get("playerID", 0))
        self.stars = int(data.get("stars", 0))
        self.moons = int(data.get("moons", 0))
        self.diamonds = int(data.get("diamonds", 0))
        self.secretCoins = int(data.get("coins", 0))
        self.userCoins = int(data.get("userCoins", 0))
        self.demons = int(data.get("demons", 0))
        self.creatorPoints = int(data.get("cp", 0))
        self.icon = int(data.get("icon", 1))
        self.color1 = int(data.get("col1", 0))
        self.color2 = int(data.get("col2", 0))
        self.glow = 1 if data.get("glow") else 0

    def get_icon_url(self) -> str:
        if self.glow:
            return f"https://gdicon.oat.zone/icon.png?type=cube&value={self.icon}&color1={self.color1}&color2={self.color2}&glow={self.glow}"
        return f"https://gdicon.oat.zone/icon.png?type=cube&value={self.icon}&color1={self.color1}&color2={self.color2}"


async def load_daftar_player_async() -> list[dict]:
    def _load():
        try:
            return database.load_all_gd_players()
        except Exception as e:
            print(f"[Aika] GD Leaderboard: gagal memuat data player SQLite: {e}")
            return []
    return await asyncio.to_thread(_load)


async def simpan_daftar_player_async(players: list[dict]):
    def _save():
        try:
            database.save_all_gd_players(players)
        except Exception as e:
            print(f"[Aika] GD Leaderboard: gagal memperbarui data player SQLite: {e}")
    await asyncio.to_thread(_save)


PENYIMPANAN_VERIFIKASI = {}

META_KATEGORI_LEADERBOARD = {
    "demons": {
        "key": "demons",
        "title": "Kategori Demons",
        "emoji": "<:GD_harddemon:1543546992234598490>",
        "button_emoji": discord.PartialEmoji(name="GD_harddemon", id=1543546992234598490),
        "button_style": discord.ButtonStyle.secondary,
        "thumbnail": "https://cdn.discordapp.com/attachments/863959650448703538/1544331593529954425/diffIcon_06_btn_001.png?ex=6a981e60&is=6a96cce0&hm=f4b0f3290440d6909c146def46ea989e9a01aa2f3fdb4a9fdc7a668e1fe877ca&",
        "accent": 0xFF3950,
    },
    "moons": {
        "key": "moons",
        "title": "Kategori Moons",
        "emoji": "<:GD_moon:1543545864071544924>",
        "button_emoji": discord.PartialEmoji(name="GD_moon", id=1543545864071544924),
        "button_style": discord.ButtonStyle.secondary,
        "thumbnail": "https://cdn.discordapp.com/attachments/863959650448703538/1544331593949118525/GJ_bigMoon_noShadow_001.png?ex=6a981e60&is=6a96cce0&hm=7c4de3b9a9f5d0cda75d308955b73050747079464e15930ccdbf0407203360b4&",
        "accent": 0x00E2FF,
    },
    "stars": {
        "key": "stars",
        "title": "Kategori Stars",
        "emoji": "<:GD_star:1543545805888295012>",
        "button_emoji": discord.PartialEmoji(name="GD_star", id=1543545805888295012),
        "button_style": discord.ButtonStyle.secondary,
        "thumbnail": "https://cdn.discordapp.com/attachments/863959650448703538/1544331594301710356/GJ_bigStar_noShadow_001.png?ex=6a981e60&is=6a96cce0&hm=c65df29a2a5657f8566ed24a36c634b307d1b2ccf6e01b49f38620559374845e&",
        "accent": 0xFFFA88,
    },
    "secret coins": {
        "key": "secretCoins",
        "title": "Kategori Secret Coins",
        "emoji": "<:GD_secretcoin:1543546398065295430>",
        "button_emoji": discord.PartialEmoji(name="GD_secretcoin", id=1543546398065295430),
        "button_style": discord.ButtonStyle.secondary,
        "thumbnail": "https://cdn.discordapp.com/attachments/863959650448703538/1544331595002150912/secretCoinUI_001.png?ex=6a981e60&is=6a96cce0&hm=0435f71f15984169b864d143a5ace0dd9b46c39a1f11e627390c6de7e82fcaaa&",
        "accent": 0xF5B000,
    },
    "user coins": {
        "key": "userCoins",
        "title": "Kategori User Coins",
        "emoji": "<:GD_usercoin:1543545917179699250>",
        "button_emoji": discord.PartialEmoji(name="GD_usercoin", id=1543545917179699250),
        "button_style": discord.ButtonStyle.secondary,
        "thumbnail": "https://cdn.discordapp.com/attachments/863959650448703538/1544331595366797482/secretCoinUI2_001.png?ex=6a981e60&is=6a96cce0&hm=569c8c330436bc06f885c732ff9b1bf84c8ff5813df7afc9cb4b286fc2479bb1&",
        "accent": 0x929292,
    },
    "diamonds": {
        "key": "diamonds",
        "title": "Kategori Diamonds",
        "emoji": "<:GD_diamond:1543546461675851776>",
        "button_emoji": discord.PartialEmoji(name="GD_diamond", id=1543546461675851776),
        "button_style": discord.ButtonStyle.secondary,
        "thumbnail": "https://cdn.discordapp.com/attachments/863959650448703538/1544343625008291910/GJ_bigDiamond_noShadow_001.png?ex=6a982994&is=6a96d814&hm=1292275544f326d2aa3ff4c2d75be1ae7b63d61d3823aeeed86de47a3d4b6d23&",
        "accent": 0x00C2FE,
    },
    "creator points": {
        "key": "creatorPoints",
        "title": "Kategori Creator Points",
        "emoji": "<:GD_creator:1543546308848132106>",
        "button_emoji": discord.PartialEmoji(name="GD_creator", id=1543546308848132106),
        "button_style": discord.ButtonStyle.secondary,
        "thumbnail": "https://cdn.discordapp.com/attachments/863959650448703538/1544331594645504121/GJ_hammerIcon_001.png?ex=6a981e60&is=6a96cce0&hm=05ac09934fad19f4c1192b97260c1f287f113c13f3a1b6eeb35acab264ba459b&",
        "accent": 0xEBEBEB,
    },
}

ALIASES_MAP = {
    "moons": "moons", "moon": "moons",
    "secretcoin": "secret coins", "secretcoins": "secret coins", "secret coin": "secret coins",
    "usercoin": "user coins", "usercoins": "user coins",
    "creatorpoint": "creator points", "creatorpoints": "creator points",
    "diamonds": "diamonds", "user coins": "user coins", "secret coins": "secret coins",
    "creator points": "creator points"
}


def normalisasi_kategori_gd(value:str|None) -> str:
    if not value:
        return "stars"
    normalized = " ".join(value.strip().lower().replace("_", " ").replace("-", " ").split())
    return ALIASES_MAP.get(normalized, normalized)


def atur_row_leaderboard_gd(category_name:str, daftar_player:list[dict]) -> list[tuple[GDPlayer,dict]]:
    category = normalisasi_kategori_gd(category_name)
    if category not in META_KATEGORI_LEADERBOARD:
        category = "stars"

    rows = []
    for player_data in daftar_player:
        stats = player_data.get("statistik", {})
        mock_data = {
            "username": player_data.get("nama_user_gd", "Tidak Diketahui"),
            "accountID": player_data.get("account_id_gd", 0),
            "playerID": player_data.get("player_id_gd", 0),
            "stars": stats.get("stars", 0),
            "moons": stats.get("moons", 0),
            "diamonds": stats.get("diamonds", 0),
            "coins": stats.get("secret_coins", 0),
            "userCoins": stats.get("user_coins", 0),
            "demons": stats.get("demons", 0),
            "cp": stats.get("creator_points", 0),
            "icon": player_data.get("icon", stats.get("icon", 1)),
            "col1": player_data.get("col1", player_data.get("color1", stats.get("color1", 0))),
            "col2": player_data.get("col2", player_data.get("color2", stats.get("color2", 0))),
            "glow": player_data.get("glow", stats.get("glow", 0)),
        }
        rows.append((GDPlayer(mock_data), player_data))

    stat_key = META_KATEGORI_LEADERBOARD[category]["key"]
    rows.sort(key=lambda pair: getattr(pair[0], stat_key, 0), reverse=True)

    if category == "creator points":
        rows = [pair for pair in rows if getattr(pair[0], stat_key, 0) > 0]

    return rows


def buat_embed_gd(title:str="", description:str="", color:discord.Colour=None) -> discord.Embed:
    embed = discord.Embed(
        title=title,
        description=description,
        color=color or discord.Colour.default()
    )
    embed.set_author(name=AUTHOR_NAME_LEADERBOARD, icon_url=AUTHOR_ICON_LEADERBOARD)
    return embed


async def cek_koneksi_robtop(session:aiohttp.ClientSession) -> bool:
    url_ping = "http://www.boomlings.com/database/getGJUserInfo20.php"
    muatan = {"targetAccountID": str(account_id_gd_BOT), "secret": BOOMLINGS_SECRET}
    header = {"User-Agent": ""}
    try:
        async with session.post(url_ping, data=muatan, headers=header, timeout=aiohttp.ClientTimeout(total=4)) as resp:
            tek = await resp.text()
            return resp.status == 200 and tek != "-1"
    except Exception:
        return False


async def cari_profil_gd(session:aiohttp.ClientSession, username:str) -> tuple[int,int,str] | None:
    api_gdbrowser = f"https://gdbrowser.com/api/profile/{username}"
    try:
        async with session.get(api_gdbrowser, ssl=False, timeout=aiohttp.ClientTimeout(total=8)) as tanggapan:
            if tanggapan.status == 200:
                data = await tanggapan.json()
                if not isinstance(data, dict) or "accountID" not in data:
                    return None
                return int(data.get("accountID", 0)), int(data.get("playerID", 0)), data.get("username")
            return None
    except Exception as e:
        print(f"[Aika] Error pencarian profil {username}: {e}")
        return None


async def baca_data_tunggal_player_async(session:aiohttp.ClientSession, player_dict:dict) -> tuple[GDPlayer|None,dict]:
    account_id_gd = player_dict.get("account_id_gd", 0)
    username = player_dict.get("nama_user_gd", "")
    
    target = account_id_gd if account_id_gd != 0 else username
    if not target:
        return None, player_dict

    api_url = f"https://gdbrowser.com/api/profile/{target}"
    try:
        async with session.get(api_url, ssl=False, timeout=aiohttp.ClientTimeout(total=8)) as response:
            if response.status == 200:
                data = await response.json()
                obj_player = GDPlayer(data)
                
                player_dict["statistik"] = {
                    "stars": obj_player.stars,
                    "moons": obj_player.moons,
                    "diamonds": obj_player.diamonds,
                    "secret_coins": obj_player.secretCoins,
                    "user_coins": obj_player.userCoins,
                    "demons": obj_player.demons,
                    "creator_points": obj_player.creatorPoints,
                }

                player_dict["icon"] = obj_player.icon
                player_dict["col1"] = obj_player.color1
                player_dict["col2"] = obj_player.color2
                player_dict["glow"] = obj_player.glow

                if player_dict.get("account_id_gd") == 0 and obj_player.accountID:
                    player_dict["account_id_gd"] = obj_player.accountID
                if player_dict.get("player_id_gd") == 0 and obj_player.playerID:
                    player_dict["player_id_gd"] = obj_player.playerID

                return obj_player, player_dict
            return None, player_dict
    except Exception as err:
        print(f"[Aika] GD Leaderboard: gagal membaca {target} -> {err}")
        return None, player_dict


async def baca_pesan_masuk_gd(session:aiohttp.ClientSession) -> list[dict]:
    database_robtop = "http://www.boomlings.com/database/getGJMessages20.php"
    muatan = {
        "accountID": str(account_id_gd_BOT),
        "gjp2": HASH_GJP2_BOT,
        "page": "0",
        "total": "0",
        "secret": BOOMLINGS_SECRET,
    }
    header = {"User-Agent": ""}

    try:
        async with session.post(database_robtop, data=muatan, headers=header, timeout=aiohttp.ClientTimeout(total=6)) as tanggapan:
            teks = await tanggapan.text()
            if not teks or teks == "-1" or teks.startswith("error") or "<html" in teks.lower() or "cloudflare" in teks.lower():
                return []

            daftar_pesan = []
            pesan_mentah = teks.split("#")[0].split("|")
            for baris_pesan in pesan_mentah:
                if not baris_pesan:
                    continue
                bidang = baris_pesan.split(":")
                dict_pesan = {bidang[i]: bidang[i+1] for i in range(0, len(bidang)-1, 2)}
                daftar_pesan.append({
                    "pengirim": dict_pesan.get("6", ""),
                    "subjek": dict_pesan.get("4", ""),
                    "id": dict_pesan.get("1", "")
                })
            return daftar_pesan
    except Exception:
        return []



class TampilanKategoriLeaderboard(discord.ui.LayoutView):
    def __init__(
        self,
        judul_kategori: str,
        data_player: list[tuple],
        kunci_stat: str,
        emoji_stat: str,
        warna_aksen: discord.Colour,
        gambar_banner: str = None
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



class PopUpPendaftaran(discord.ui.Modal):
    input_username_gd = discord.ui.TextInput(
        label="Username GD-mu (huruf kapital)", 
        placeholder="Contoh: TheHx",
        required=True,
    )

    def __init__(self, cog_leaderboard:"BinrumLeaderboard"):
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
    def __init__(self, cog_leaderboard:"BinrumLeaderboard"=None):
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
                f"Mau cek leaderboard selengkapnya? Gunakan `/binroom_gd_leaderboard` atau klik tombol di bawah.\n\n"
                f"Mau join leaderboard BinRoom? Klik tombol **Daftarkan akunmu** di bawah."
            ),
            color=0xFFE700
        ).set_thumbnail(url="https://cdn.discordapp.com/attachments/863959650448703538/1543780342379319337/rankIcon_1_001.png?ex=6a961cfb&is=6a94cb7b&hm=33bf6524a61776ae3bf21ccd07c9aab07260085a9c0dddf098ad73ea4bd19f59&")
        return embed


class TombolKonfirmasiVerifikasi(discord.ui.View):
    def __init__(self, cog_leaderboard:"BinrumLeaderboard", user_id:int):
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



class GDLeaderboardCategoryView(discord.ui.View):
    def __init__(self, cog:"BinrumLeaderboard", daftar_player:list[dict], category:str="stars", timeout_seconds:float=180.0):
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

            async def handle_category(interaction:discord.Interaction, category_name=category_name):
                await self.switch_category(interaction, category_name)

            button.callback = handle_category
            self.add_item(button)

        prev_button = discord.ui.Button(emoji="◀", style=discord.ButtonStyle.success, disabled=(self.page <= 0), custom_id="gd_lb_prev")
        page_indicator_button = discord.ui.Button(label=f"{self.page + 1}/{self.total_pages}", style=discord.ButtonStyle.primary, disabled=True, custom_id="gd_lb_page_num")
        next_button = discord.ui.Button(emoji="▶", style=discord.ButtonStyle.success, disabled=(self.page >= self.total_pages - 1), custom_id="gd_lb_next")

        async def handle_prev(interaction:discord.Interaction):
            await self.go_previous(interaction)

        async def handle_next(interaction:discord.Interaction):
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
            if isinstance(child,discord.ui.Button):
                child.disabled = True
        if self.message:
            try:
                await self.message.edit(view=self)
            except discord.HTTPException:
                pass


class BinrumLeaderboard(commands.Cog):
    def __init__(self, bot:commands.Bot):
        self.bot = bot
        self.session = aiohttp.ClientSession()
        self.semaphore = asyncio.Semaphore(6)
        self.update_otomatis.start()

    async def cog_unload(self):
        self.update_otomatis.cancel()
        await self.session.close()

    async def cog_load(self):
        self.bot.add_view(TampilanRegistrasiContainer(self))

    async def cog_app_command_error(self, interaction:discord.Interaction, error:app_commands.AppCommandError):
        msg = "<:GD_x:1543409414843662346> Hanya atmint yang bisa pakai fitur ini!" if isinstance(error, (app_commands.MissingPermissions, app_commands.CheckFailure)) else f"<:GD_x:1543409414843662346> Terjadi kesalahan: `{error}`"
        try:
            if interaction.response.is_done():
                await interaction.followup.send(msg, ephemeral=True)
            else:
                await interaction.response.send_message(msg, ephemeral=True)
        except discord.HTTPException:
            pass

    async def cog_command_error(self, ctx:commands.Context, error:commands.CommandError):
        msg = "<:GD_x:1543409414843662346> Hanya atmint yang bisa pakai fitur ini!" if isinstance(error, (commands.MissingPermissions, commands.CheckFailure)) else f"<:GD_x:1543409414843662346> Terjadi kesalahan: `{error}`"
        if ctx.interaction:
            try:
                if ctx.interaction.response.is_done():
                    await ctx.interaction.followup.send(msg, ephemeral=True)
                else:
                    await ctx.interaction.response.send_message(msg, ephemeral=True)
            except discord.HTTPException:
                pass
        else:
            await ctx.send(msg)

    async def update_tampilan_leaderboard(self, target_channel=None):
        channel_leaderboard = target_channel or self.bot.get_channel(ID_CHANNEL_LEADERBOARD)
        if not channel_leaderboard:
            return

        daftar_id_player = await load_daftar_player_async()

        if not daftar_id_player:
            await channel_leaderboard.purge(limit=10)
            reg_view = TampilanRegistrasiContainer(self)
            embed_reg = await reg_view.generate_embed_async()
            await channel_leaderboard.send(embed=embed_reg, view=reg_view)
            return

        async def fetch_with_semaphore(p_dict):
            async with self.semaphore:
                obj, updated_dict = await baca_data_tunggal_player_async(self.session, p_dict)
                return (obj, updated_dict) if obj is not None else None

        tugas_fetch = [fetch_with_semaphore(p) for p in daftar_id_player]
        hasil = await asyncio.gather(*tugas_fetch)
        player_valid = [pair for pair in hasil if pair is not None]

        await simpan_daftar_player_async(daftar_id_player)

        data_demons = sorted(player_valid, key=lambda pair: getattr(pair[0], "demons", 0), reverse=True)
        data_stars = sorted(player_valid, key=lambda pair: getattr(pair[0], "stars", 0), reverse=True)
        data_cp = sorted([pair for pair in player_valid if getattr(pair[0], "creatorPoints", 0) > 0], key=lambda pair: getattr(pair[0], "creatorPoints", 0), reverse=True)

        try:
            await channel_leaderboard.purge(limit=10)

            view_demons = TampilanKategoriLeaderboard(
                judul_kategori="<:GD_harddemon:1543546992234598490> BinRoom GD Players Leaderboard — Kategori Demons",
                data_player=data_demons,
                kunci_stat="demons",
                emoji_stat="<:hard_demon:1285063566742781984>",
                warna_aksen=discord.Colour.red(),
                gambar_banner=GAMBAR_HEADER
            )
            await channel_leaderboard.send(view=view_demons)

            view_stars = TampilanKategoriLeaderboard(
                judul_kategori="<:GD_star:1543545805888295012> BinRoom GD Players Leaderboard — Kategori Stars",
                data_player=data_stars,
                kunci_stat="stars",
                emoji_stat="<:gd_star:1285063657839136869>",
                warna_aksen=discord.Colour.gold()
            )
            await channel_leaderboard.send(view=view_stars)

            if data_cp:
                view_cp = TampilanKategoriLeaderboard(
                    judul_kategori="<:GD_creator:1543546308848132106> BinRoom GD Players Leaderboard — Kategori Creator Points",
                    data_player=data_cp,
                    kunci_stat="creatorPoints",
                    emoji_stat="<:creator_icon:1543402506355212409>",
                    warna_aksen=discord.Colour.light_grey()
                )
                await channel_leaderboard.send(view=view_cp)

            view_reg = TampilanRegistrasiContainer(self)
            embed_reg = await view_reg.generate_embed_async()
            await channel_leaderboard.send(embed=embed_reg, view=view_reg)
        except discord.DiscordException as galat:
            print(f"[Aika] GD Leaderboard: gagal mengirim pesan: {galat}")

    async def render_tampilan_leaderboard_lokal(self, target_channel=None):
        channel_leaderboard = target_channel or self.bot.get_channel(ID_CHANNEL_LEADERBOARD)
        if not channel_leaderboard:
            return

        daftar_db = await load_daftar_player_async()
        if not daftar_db:
            await channel_leaderboard.purge(limit=10)
            reg_view = TampilanRegistrasiContainer(self)
            embed_reg = await reg_view.generate_embed_async()
            await channel_leaderboard.send(embed=embed_reg, view=reg_view)
            return

        player_valid = []
        for p in daftar_db:
            stats = p.get("statistik", {})
            mock_data = {
                "username": p.get("nama_user_gd", "Tidak Diketahui"),
                "accountID": p.get("account_id_gd", 0),
                "playerID": p.get("player_id_gd", 0),
                "stars": stats.get("stars", 0),
                "moons": stats.get("moons", 0),
                "diamonds": stats.get("diamonds", 0),
                "coins": stats.get("secret_coins", 0),
                "userCoins": stats.get("user_coins", 0),
                "demons": stats.get("demons", 0),
                "cp": stats.get("creator_points", 0),
                "icon": p.get("icon", stats.get("icon", 1)),
                "col1": p.get("col1", p.get("color1", stats.get("color1", 0))),
                "col2": p.get("col2", p.get("color2", stats.get("color2", 0))),
                "glow": p.get("glow", stats.get("glow", 0)),
            }
            player_valid.append((GDPlayer(mock_data), p))

        data_demons = sorted(player_valid, key=lambda pair: getattr(pair[0], "demons", 0), reverse=True)
        data_stars = sorted(player_valid, key=lambda pair: getattr(pair[0], "stars", 0), reverse=True)
        data_cp = sorted([pair for pair in player_valid if getattr(pair[0], "creatorPoints", 0) > 0], key=lambda pair: getattr(pair[0], "creatorPoints", 0), reverse=True)

        try:
            await channel_leaderboard.purge(limit=10)

            view_demons = TampilanKategoriLeaderboard(
                judul_kategori="<:GD_harddemon:1543546992234598490> BinRoom GD Players Leaderboard — Kategori Demons",
                data_player=data_demons,
                kunci_stat="demons",
                emoji_stat="<:hard_demon:1285063566742781984>",
                warna_aksen=discord.Colour.red(),
                gambar_banner=GAMBAR_HEADER
            )
            await channel_leaderboard.send(view=view_demons)

            view_stars = TampilanKategoriLeaderboard(
                judul_kategori="<:GD_star:1543545805888295012> BinRoom GD Players Leaderboard — Kategori Stars",
                data_player=data_stars,
                kunci_stat="stars",
                emoji_stat="<:gd_star:1285063657839136869>",
                warna_aksen=discord.Colour.gold()
            )
            await channel_leaderboard.send(view=view_stars)

            if data_cp:
                view_cp = TampilanKategoriLeaderboard(
                    judul_kategori="<:GD_creator:1543546308848132106> BinRoom GD Players Leaderboard — Kategori Creator Points",
                    data_player=data_cp,
                    kunci_stat="creatorPoints",
                    emoji_stat="<:creator_icon:1543402506355212409>",
                    warna_aksen=discord.Colour.light_grey()
                )
                await channel_leaderboard.send(view=view_cp)

            view_reg = TampilanRegistrasiContainer(self)
            embed_reg = await view_reg.generate_embed_async()
            await channel_leaderboard.send(embed=embed_reg, view=view_reg)
        except discord.DiscordException as galat:
            print(f"[Aika] GD Leaderboard: gagal memperbarui tampilan lokal: {galat}")

    @tasks.loop(hours=24)
    async def update_otomatis(self):
        await self.update_tampilan_leaderboard()

    @update_otomatis.before_loop
    async def sebelum_update_otomatis(self):
        await self.bot.wait_until_ready()

    @commands.hybrid_command(
        name="reset_leaderboard",
        aliases=["refresh_leaderboard"],
        description="Memperbarui tampilan leaderboard GD secara manual."
    )
    @commands.has_permissions(administrator=True)
    async def reset_leaderboard(self, ctx:commands.Context):
        await ctx.defer(ephemeral=False)
        try:
            await self.update_tampilan_leaderboard(target_channel=ctx.channel)
            await ctx.send("<:GD_complete:1543409457940267078> Leaderboard berhasil diperbarui.")
        except Exception as e:
            await ctx.send(f"Gagal, coba lagi.\n`{e}`")

    @commands.hybrid_command(
        name="rebuild_leaderboard",
        aliases=["render_leaderboard", "repost_leaderboard"],
        description="Merender ulang leaderboard dari database lokal tanpa memanggil API GD."
    )
    @commands.has_permissions(administrator=True)
    async def rebuild_leaderboard(self, ctx:commands.Context):
        await ctx.defer(ephemeral=False)
        try:
            await self.render_tampilan_leaderboard_lokal(target_channel=ctx.channel)
            await ctx.send("<:GD_complete:1543409457940267078> Berhasil merender ulang leaderboard")
        except Exception as e:
            await ctx.send(f"Gagal merender ulang leaderboard.\n`{e}`")

    @commands.hybrid_command(
        name="binroom_gd_leaderboard",
        aliases=["gd_leaderboard", "leaderboard_gd"],
        description="Menampilkan leaderboard GD per kategori dengan navigasi paginasi dan tombol kategori."
    )
    async def binroom_gd_leaderboard(self, ctx:commands.Context, category:str="stars"):
        await ctx.defer(ephemeral=False)

        normalized = normalisasi_kategori_gd(category)
        if normalized not in META_KATEGORI_LEADERBOARD:
            normalized = "stars"

        daftar_player = await load_daftar_player_async()
        view = GDLeaderboardCategoryView(self, daftar_player, normalized, timeout_seconds=180.0)
        embed = view.build_embed()
        pesan = await ctx.send(embed=embed, view=view)
        view.message = pesan

    @commands.hybrid_command(
        name="admin_daftar_leaderboard",
        description="Command admin untuk mendaftarkan player GD ke leaderboard secara manual."
    )
    @commands.has_permissions(administrator=True)
    async def admin_register_gd(self, ctx:commands.Context, gd_username:str, discord_user:discord.User=None):
        await ctx.defer(ephemeral=False)
        nama_input = gd_username.strip()

        data_user = await cari_profil_gd(self.session, nama_input)
        if not data_user:
            await ctx.send("<:GD_x:1543409414843662346> Username GD tidak valid, gagal mendaftarkan...", ephemeral=True)
            return

        account_id, player_id, nama_asli = data_user
        id_discord = discord_user.id if discord_user else None

        daftar_player = await load_daftar_player_async()
        player_ada = next(
            (p for p in daftar_player if p.get("account_id_gd") == account_id or p.get("nama_user_gd").lower() == nama_asli.lower()),
            None
        )

        if player_ada:
            player_ada["nama_user_gd"] = nama_asli
            player_ada["account_id_gd"] = account_id
            player_ada["player_id_gd"] = player_id
            if id_discord:
                player_ada["id_user_discord"] = id_discord
        else:
            data_baru = {
                "nama_user_gd": nama_asli,
                "account_id_gd": account_id,
                "player_id_gd": player_id,
                "id_user_discord": id_discord,
                "statistik": {
                    "stars": 0, "moons": 0, "diamonds": 0,
                    "secret_coins": 0, "user_coins": 0, "demons": 0, "creator_points": 0
                }
            }
            daftar_player.append(data_baru)

        await simpan_daftar_player_async(daftar_player)
        
        info_discord = f" (Discord: <@{id_discord}>)" if id_discord else ""
        embed_berhasil_daftar_manual = buat_embed_gd(
            title="<:GD_complete:1543409457940267078> Berhasil",
            description=f"**{nama_asli}**{info_discord} berhasil didaftarkan ke leaderboard",
            color=discord.Color.green()
        )

        await ctx.send(embed=embed_berhasil_daftar_manual)

    @commands.hybrid_command(
        name="admin_hapus_leaderboard",
        aliases=["admin_remove_gd"],
        description="Command admin untuk menghapus player dari leaderboard GD BinRoom."
    )
    @commands.has_permissions(administrator=True)
    async def admin_hapus_gd(self, ctx:commands.Context):
        await ctx.defer(ephemeral=True)
        daftar_player = await load_daftar_player_async()

        if not daftar_player:
            await ctx.send("<:GD_x:1543409414843662346> Data player di database kosong!", ephemeral=True)
            return

        view_select = MenuPilihHapusPlayer(daftar_player, timeout_seconds=60.0)
        pesan = await ctx.send(embed=view_select.get_content(), view=view_select, ephemeral=True)
        view_select.pesan = pesan


async def setup(bot:commands.Bot):
    cog = BinrumLeaderboard(bot)
    await bot.add_cog(cog)