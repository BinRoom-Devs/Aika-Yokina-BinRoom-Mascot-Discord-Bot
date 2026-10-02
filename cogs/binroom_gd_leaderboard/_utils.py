import asyncio

import aiohttp
import discord

import database

from ._config import (
    ACCOUNT_ID_GD_BOT,
    ALIASES_MAP,
    AUTHOR_ICON_LEADERBOARD,
    AUTHOR_NAME_LEADERBOARD,
    BOOMLINGS_SECRET,
    HASH_GJP2_BOT,
    META_KATEGORI_LEADERBOARD,
)
from ._models import GDPlayer


async def load_daftar_player_async() -> list[dict]:
    try:
        return await database.get_all_gd_players()
    except Exception as e:  # noqa: BLE001
        print(f"[SQLite] GD Leaderboard: gagal memuat data player: {e}")
        return []

async def simpan_daftar_player_async(players:list[dict]):
    try:
        await database.save_all_gd_players(players)
    except Exception as e:  # noqa: BLE001
        print(f"[SQLite] GD Leaderboard: gagal memperbarui data player: {e}")

def normalisasi_kategori_gd(value:str|None) -> str:
    if not value:
        return "stars"
    normalized = " ".join(value.strip().lower().replace("_", " ").replace("-", " ").split())
    return ALIASES_MAP.get(normalized, normalized)

def atur_row_leaderboard_gd(category_name:str, daftar_player:list[dict|tuple]) -> list[tuple[GDPlayer, dict]]:
    category = normalisasi_kategori_gd(category_name)
    if category not in META_KATEGORI_LEADERBOARD:
        category = "stars"
    
    rows = []
    for item in daftar_player:
        if isinstance(item, tuple):
            rows.append(item)
            continue
        
        player_data = item
        stats = player_data.get("statistik") or {}
        mock_data = {
            "username": player_data.get("nama_user_gd", "Tidak Diketahui"),
            "accountID": player_data.get("account_id_gd", 0),
            "playerID": player_data.get("player_id_gd", 0),
            "stars": stats.get("stars", player_data.get("stars", 0)),
            "moons": stats.get("moons", player_data.get("moons", 0)),
            "diamonds": stats.get("diamonds", player_data.get("diamonds", 0)),
            "coins": stats.get("secret_coins", player_data.get("secret_coins", 0)),
            "userCoins": stats.get("user_coins", player_data.get("user_coins", 0)),
            "demons": stats.get("demons", player_data.get("demons", 0)),
            "cp": stats.get("creator_points", player_data.get("creator_points", 0)),
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
    muatan = {"targetAccountID": str(ACCOUNT_ID_GD_BOT), "secret": BOOMLINGS_SECRET}
    header = {"User-Agent": ""}
    try:
        async with session.post(url_ping, data=muatan, headers=header, timeout=aiohttp.ClientTimeout(total=4)) as resp:
            tek = await resp.text()
            return resp.status == 200 and tek != "-1"
    except (aiohttp.ClientError, asyncio.TimeoutError):
        return False

async def cari_profil_gd(session: aiohttp.ClientSession, username: str) -> tuple[int, int, str] | None:
    api_gdbrowser = f"https://gdbrowser.com/api/profile/{username}"
    try:
        async with session.get(api_gdbrowser, ssl=False, timeout=aiohttp.ClientTimeout(total=8)) as tanggapan:
            if tanggapan.status == 200:
                data = await tanggapan.json()
                if not isinstance(data, dict) or "accountID" not in data:
                    return None
                return int(data.get("accountID", 0)), int(data.get("playerID", 0)), data.get("username")
            return None
    except (aiohttp.ClientError, asyncio.TimeoutError, ValueError) as e:
        print(f"[Aika] GD Leaderboard: error saat mencari profil {username}: {e}")
        return None

async def baca_data_tunggal_player_async(session: aiohttp.ClientSession, player_dict: dict) -> tuple[GDPlayer | None, dict]:
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
                
                stats = {
                    "stars": obj_player.stars,
                    "moons": obj_player.moons,
                    "diamonds": obj_player.diamonds,
                    "secret_coins": obj_player.secretCoins,
                    "user_coins": obj_player.userCoins,
                    "demons": obj_player.demons,
                    "creator_points": obj_player.creatorPoints,
                }
                player_dict["statistik"] = stats
                player_dict.update(stats)
                
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
        
    except (aiohttp.ClientError, asyncio.TimeoutError, ValueError, KeyError) as err:
        print(f"[Aika] GD Leaderboard: gagal membaca {target} -> {err}")
        return None, player_dict
    
async def baca_pesan_masuk_gd(session:aiohttp.ClientSession) -> list[dict]:
    database_robtop = "http://www.boomlings.com/database/getGJMessages20.php"
    muatan = {
        "accountID": str(ACCOUNT_ID_GD_BOT),
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
        
    except (aiohttp.ClientError, asyncio.TimeoutError, IndexError, ValueError):
        return []