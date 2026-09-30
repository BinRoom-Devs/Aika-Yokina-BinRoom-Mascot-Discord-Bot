import asyncio
import collections
import json
import os
from contextlib import asynccontextmanager
from datetime import datetime, timedelta, timezone
from typing import Any

import aiosqlite

try:
    import orjson
    
    def json_dumps(obj: Any) -> str:
        return orjson.dumps(obj).decode("utf-8")
    
    def json_loads(data: str) -> Any:
        return orjson.loads(data)
except ImportError:
    json_dumps = json.dumps
    json_loads = json.loads


BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATABASE_PATH = os.getenv(
    "DATABASE_PATH",
    os.path.join(BASE_DIR, "data", "aika.db")
)


def _read_json_file(file_path: str) -> Any:
    """Function pembantu buat ngebaca file JSON secara sinkronis di dalam thread eksekutor."""
    
    with open(file_path, "r", encoding="utf-8") as f:
        return json.load(f)


@asynccontextmanager
async def get_connection():
    os.makedirs(os.path.dirname(DATABASE_PATH), exist_ok=True)
    
    conn = await aiosqlite.connect(DATABASE_PATH)
    conn.row_factory = aiosqlite.Row
    
    try:
        await conn.execute("PRAGMA journal_mode=WAL;")
        await conn.execute("PRAGMA synchronous=NORMAL;")
        await conn.execute("PRAGMA busy_timeout=10000;")
        
        yield conn
        await conn.commit()
        
    except Exception:
        await conn.rollback()
        raise
        
    finally:
        await conn.close()


# -----------------------------------------------------------------------------
# inisialisasi & migrasi
# -----------------------------------------------------------------------------

async def init_db() -> None:
    """Nginisialisasi tabel sama indeks di database, skalian nge-run auto-migration kalo perlu."""
    
    async with get_connection() as conn:
        
        #tabel lore aika
        await conn.execute("""
            CREATE TABLE IF NOT EXISTS aika_lore (
                id INTEGER PRIMARY KEY CHECK (id = 1),
                original_illustrator TEXT,
                origin_story TEXT,
                contributors TEXT,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        #tabel chat para member
        await conn.execute("""
            CREATE TABLE IF NOT EXISTS user_chats (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                role TEXT NOT NULL,
                content TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        await conn.execute("""
            CREATE INDEX IF NOT EXISTS idx_user_chats_user_id 
            ON user_chats(user_id)
        """) 
        
        # 3. tabel para player gd
        await conn.execute("""
            CREATE TABLE IF NOT EXISTS gd_players (
                account_id_gd INTEGER PRIMARY KEY,
                nama_user_gd TEXT NOT NULL,
                player_id_gd INTEGER DEFAULT 0,
                id_user_discord INTEGER,
                stars INTEGER DEFAULT 0,
                moons INTEGER DEFAULT 0,
                diamonds INTEGER DEFAULT 0,
                secret_coins INTEGER DEFAULT 0,
                user_coins INTEGER DEFAULT 0,
                demons INTEGER DEFAULT 0,
                creator_points INTEGER DEFAULT 0,
                icon INTEGER DEFAULT 0,
                col1 INTEGER DEFAULT 0,
                col2 INTEGER DEFAULT 0,
                glow INTEGER DEFAULT 0,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        await conn.execute("""
            CREATE INDEX IF NOT EXISTS idx_gd_players_nama 
            ON gd_players(nama_user_gd COLLATE NOCASE)
        """)
        await conn.execute("""
            CREATE INDEX IF NOT EXISTS idx_gd_players_discord 
            ON gd_players(id_user_discord)
        """)

        # 4. tabel riwayat downtime
        await conn.execute("""
            CREATE TABLE IF NOT EXISTS downtime_history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                status TEXT NOT NULL,
                timestamp TEXT NOT NULL,
                alasan TEXT NOT NULL
            )
        """)

        # 5. tabel statistik harian
        cursor = await conn.execute("PRAGMA table_info(daily_stats)")
        cols = [r["name"] for r in await cursor.fetchall()]
        if cols and "key" not in cols:
            await conn.execute("DROP TABLE daily_stats")

        await conn.execute("""
            CREATE TABLE IF NOT EXISTS daily_stats (
                key TEXT PRIMARY KEY,
                value TEXT NOT NULL
            )
        """)

        # 6. tabel durasi voice channel
        await conn.execute("""
            CREATE TABLE IF NOT EXISTS vc_durations (
                category TEXT NOT NULL,
                target_id INTEGER NOT NULL,
                timestamp TEXT NOT NULL,
                PRIMARY KEY (category, target_id)
            )
        """)
        
        # 7. tabel memebrship binroom / fitur kartu member
        await conn.execute("""
            CREATE TABLE IF NOT EXISTS binroom_memberships (
                user_id INTEGER PRIMARY KEY,
                custom_name TEXT,
                join_number INTEGER,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        # 8. tabel streak harian member
        await conn.execute("""
            CREATE TABLE IF NOT EXISTS streak_member (
                user_id INTEGER PRIMARY KEY,
                streak_skrg INTEGER DEFAULT 0,
                streak_terlama INTEGER DEFAULT 0, 
                terakhir_aktif TEXT
            )
        """)
    
    #cek buat migrasi json
    await auto_migrate_from_json()


async def auto_migrate_from_json() -> None:
    """Migrasi dari file JSON ke tabel SQLite kalo kosong."""
    
    json_dir = os.path.join(BASE_DIR, "json")
    data_dir = os.path.join(BASE_DIR, "data")
    
    async with get_connection() as conn:
        if os.path.exists(json_dir):
            #migrasi role
            cursor = await conn.execute("SELECT COUNT(*) FROM aika_lore")
            row = await cursor.fetchone()
            if row and row[0] == 0:
                lore_file = os.path.join(json_dir, "aika_lore.json")
                if os.path.exists(lore_file):
                    data = await asyncio.to_thread(_read_json_file, lore_file)
                    await conn.execute("""
                        INSERT INTO aika_lore (id, original_illustrator, origin_story, contributors)
                        VALUES (1, ?, ?, ?)
                    """, (
                        data.get("original_illustrator", ""),
                        data.get("origin_story", ""),
                        json_dumps(data.get("contributors", []))
                    ))
            
            #migrasi isi chat
            cursor = await conn.execute("SELECT COUNT(*) FROM user_chats")
            row = await cursor.fetchone()
            if row and row[0] == 0:
                chats_file = os.path.join(json_dir, "user_chats_with_aika.json")
                
                if os.path.exists(chats_file):
                    data = await asyncio.to_thread(_read_json_file, chats_file)
                    chat_rows = []
                    
                    for user_id_str, messages in data.items():
                        uid = int(user_id_str)
                        
                        for msg in messages:
                            chat_rows.append((uid, msg.get("role", "user"), msg.get("content", "")))
                    
                    if chat_rows:
                        await conn.executemany("""
                            INSERT INTO user_chats (user_id, role, content)
                            VALUES (?, ?, ?)
                        """, chat_rows)
            
            #migrasi player2 gd
            cursor = await conn.execute("SELECT COUNT(*) FROM gd_players")
            row = await cursor.fetchone()
            if row and row[0] == 0:
                gd_file = os.path.join(json_dir, "binrum_gd_players.json")
                
                if os.path.exists(gd_file):
                    data = await asyncio.to_thread(_read_json_file, gd_file)
                    player_rows = []
                    
                    for p in data:
                        player_rows.append((
                            p.get("account_id_gd"),
                            p.get("nama_user_gd", ""),
                            p.get("player_id_gd", 0),
                            p.get("id_user_discord"),
                            p.get("stars", 0),
                            p.get("moons", 0),
                            p.get("diamonds", 0),
                            p.get("secret_coins", 0),
                            p.get("user_coins", 0),
                            p.get("demons", 0),
                            p.get("creator_points", 0),
                            p.get("icon", 0),
                            p.get("col1", 0),
                            p.get("col2", 0),
                            p.get("glow", 0)
                        ))
                    
                    if player_rows:
                        await conn.executemany("""
                            INSERT INTO gd_players (
                                account_id_gd, nama_user_gd, player_id_gd, id_user_discord,
                                stars, moons, diamonds, secret_coins, user_coins, demons,
                                creator_points, icon, col1, col2, glow
                            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                        """, player_rows)

        if os.path.exists(data_dir):
            # migrasi downtime history
            cursor = await conn.execute("SELECT COUNT(*) FROM downtime_history")
            row = await cursor.fetchone()
            if row and row[0] == 0:
                downtime_file = os.path.join(data_dir, "riwayat_downtime.json")
                if os.path.exists(downtime_file):
                    data = await asyncio.to_thread(_read_json_file, downtime_file)
                    batch = [
                        (
                            item.get("status", "ok"),
                            str(item.get("timestamp", "")),
                            item.get("alasan", "")
                        )
                        for item in data
                    ]
                    if batch:
                        await conn.executemany("""
                            INSERT INTO downtime_history (status, timestamp, alasan)
                            VALUES (?, ?, ?)
                        """, batch)

            # migrasi daily stats
            cursor = await conn.execute("SELECT COUNT(*) FROM daily_stats")
            row = await cursor.fetchone()
            if row and row[0] == 0:
                stats_file = os.path.join(data_dir, "stats_harian.json")
                if os.path.exists(stats_file):
                    data = await asyncio.to_thread(_read_json_file, stats_file)
                    batch = []
                    for k, v in data.items():
                        if isinstance(v, (dict, list)):
                            val_str = json_dumps(v)
                        else:
                            val_str = str(v)
                        batch.append((k, val_str))
                    if batch:
                        await conn.executemany("""
                            INSERT INTO daily_stats (key, value)
                            VALUES (?, ?)
                        """, batch)

            # migrasi vc durations
            cursor = await conn.execute("SELECT COUNT(*) FROM vc_durations")
            row = await cursor.fetchone()
            if row and row[0] == 0:
                vc_file = os.path.join(data_dir, "vc_duration.json")
                if os.path.exists(vc_file):
                    data = await asyncio.to_thread(_read_json_file, vc_file)
                    batch = []
                    status_vc = data.get("status_vc", data.get("voice_states", {}))
                    status_live = data.get("status_live", data.get("streaming_states", {}))
                    status_vc_kosong = data.get("status_vc_kosong", data.get("vc_empty_states", {}))
                    
                    for k, v in status_vc.items():
                        batch.append(("status_vc", int(k), str(v)))
                    for k, v in status_live.items():
                        batch.append(("status_live", int(k), str(v)))
                    for k, v in status_vc_kosong.items():
                        batch.append(("status_vc_kosong", int(k), str(v)))
                    
                    if batch:
                        await conn.executemany("""
                            INSERT INTO vc_durations (category, target_id, timestamp)
                            VALUES (?, ?, ?)
                        """, batch)


# -----------------------------------------------------------------------------
# Lore Aika
# -----------------------------------------------------------------------------

async def get_lore() -> dict[str, Any]:
    """Ngebaca pengaturan lore-nya Aika."""
    
    async with get_connection() as conn:
        cursor = await conn.execute("SELECT * FROM aika_lore WHERE id = 1")
        row = await cursor.fetchone()
        
        if not row:
            return {"original_illustrator": "", "origin_story": "", "contributors": []}
        
        return {
            "original_illustrator": row["original_illustrator"],
            "origin_story": row["origin_story"],
            "contributors": json_loads(row["contributors"]) if row["contributors"] else []
        }


async def save_lore(original_illustrator: str, origin_story: str, contributors: list[str]) -> None:
    """Nyimpan atau ngupdate info lore Aika."""
    
    contrib_json = json_dumps(contributors)
    async with get_connection() as conn:
        await conn.execute("""
            INSERT INTO aika_lore (id, original_illustrator, origin_story, contributors, updated_at)
            VALUES (1, ?, ?, ?, CURRENT_TIMESTAMP)
            ON CONFLICT(id) DO UPDATE SET
                original_illustrator = excluded.original_illustrator,
                origin_story = excluded.origin_story,
                contributors = excluded.contributors,
                updated_at = CURRENT_TIMESTAMP
        """, (original_illustrator, origin_story, contrib_json))


# -----------------------------------------------------------------------------
# Pengaturan Memori Chat Para Member
# -----------------------------------------------------------------------------

async def get_user_chat(user_id: int) -> list[dict[str, str]]:
    """Ngebaca semua pesan chat buat satu member di Discord."""
    
    async with get_connection() as conn:
        cursor = await conn.execute(
            """SELECT role, content FROM user_chats WHERE user_id = ? ORDER BY id ASC""",
            (user_id,)
        )
        rows = await cursor.fetchall()
        return [{"role": r["role"], "content": r["content"]} for r in rows]


async def save_user_chat(user_id: int, messages: list[dict[str, str]]) -> None:
    """Ngubah isi chat buat satu member di Discord."""
    
    async with get_connection() as conn:
        await conn.execute("DELETE FROM user_chats WHERE user_id = ?", (user_id,))
        batch = [(user_id, m["role"], m["content"]) for m in messages]
        if batch:
            await conn.executemany(
                """INSERT INTO user_chats (user_id, role, content) VALUES (?, ?, ?)""",
                batch
            )


async def add_chat_message(user_id: int, role: str, content: str) -> None:
    """Nambahin satu pesan ke histori chat user."""
    
    async with get_connection() as conn:
        await conn.execute(
            """INSERT INTO user_chats (user_id, role, content) VALUES (?, ?, ?)""",
            (user_id, role, content)
        )


async def load_all_user_chats() -> dict[int, list[dict[str, str]]]:
    """Nge-load semua histori chat nya user yang dikategoriin pake user ID."""
    
    async with get_connection() as conn:
        cursor = await conn.execute("SELECT user_id, role, content FROM user_chats ORDER BY id ASC")
        rows = await cursor.fetchall()
        
        result: dict[int, list[dict[str, str]]] = {}
        for r in rows:
            uid = r["user_id"]
            
            if uid not in result:
                result[uid] = []
            
            result[uid].append({"role": r["role"], "content": r["content"]})
        
        return result


# -----------------------------------------------------------------------------
# Profil Para Player GD
# -----------------------------------------------------------------------------

async def upsert_gd_player(player_data: dict[str, Any]) -> None:
    """Masukin atau ngupdate statistiknya satu player GD."""
    
    async with get_connection() as conn:
        await conn.execute("""
            INSERT INTO gd_players (
                account_id_gd, nama_user_gd, player_id_gd, id_user_discord,
                stars, moons, diamonds, secret_coins, user_coins, demons,
                creator_points, icon, col1, col2, glow, updated_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
            ON CONFLICT(account_id_gd) DO UPDATE SET
                nama_user_gd = excluded.nama_user_gd,
                player_id_gd = excluded.player_id_gd,
                id_user_discord = excluded.id_user_discord,
                stars = excluded.stars,
                moons = excluded.moons,
                diamonds = excluded.diamonds,
                secret_coins = excluded.secret_coins,
                user_coins = excluded.user_coins,
                demons = excluded.demons,
                creator_points = excluded.creator_points,
                icon = excluded.icon,
                col1 = excluded.col1,
                col2 = excluded.col2,
                glow = excluded.glow,
                updated_at = CURRENT_TIMESTAMP
        """, (
            player_data["account_id_gd"],
            player_data.get("nama_user_gd", ""),
            player_data.get("player_id_gd", 0),
            player_data.get("id_user_discord"),
            player_data.get("stars", 0),
            player_data.get("moons", 0),
            player_data.get("diamonds", 0),
            player_data.get("secret_coins", 0),
            player_data.get("user_coins", 0),
            player_data.get("demons", 0),
            player_data.get("creator_points", 0),
            player_data.get("icon", 0),
            player_data.get("col1", 0),
            player_data.get("col2", 0),
            player_data.get("glow", 0)
        ))


async def save_all_gd_players(players: list[dict[str, Any]]) -> None:
    """Nge-batch upsert profilnya para player dan ngapus entry lama."""
    
    if not players:
        async with get_connection() as conn:
            await conn.execute("DELETE FROM gd_players")
        return
    
    account_ids = [p["account_id_gd"] for p in players]
    
    async with get_connection() as conn:
        # Upsert all provided profiles in batch
        batch = [(
            p["account_id_gd"],
            p.get("nama_user_gd", ""),
            p.get("player_id_gd", 0),
            p.get("id_user_discord"),
            p.get("stars", 0),
            p.get("moons", 0),
            p.get("diamonds", 0),
            p.get("secret_coins", 0),
            p.get("user_coins", 0),
            p.get("demons", 0),
            p.get("creator_points", 0),
            p.get("icon", 0),
            p.get("col1", 0),
            p.get("col2", 0),
            p.get("glow", 0)
        ) for p in players]
        
        await conn.executemany("""
            INSERT INTO gd_players (
                account_id_gd, nama_user_gd, player_id_gd, id_user_discord,
                stars, moons, diamonds, secret_coins, user_coins, demons,
                creator_points, icon, col1, col2, glow, updated_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
            ON CONFLICT(account_id_gd) DO UPDATE SET
                nama_user_gd = excluded.nama_user_gd,
                player_id_gd = excluded.player_id_gd,
                id_user_discord = excluded.id_user_discord,
                stars = excluded.stars,
                moons = excluded.moons,
                diamonds = excluded.diamonds,
                secret_coins = excluded.secret_coins,
                user_coins = excluded.user_coins,
                demons = excluded.demons,
                creator_points = excluded.creator_points,
                icon = excluded.icon,
                col1 = excluded.col1,
                col2 = excluded.col2,
                glow = excluded.glow,
                updated_at = CURRENT_TIMESTAMP
        """, batch)
        
        #hapus profil yang udah gaada dari database
        placeholders = ",".join("?" for _ in account_ids)
        query = f"DELETE FROM gd_players WHERE account_id_gd NOT IN ({placeholders})"
        await conn.execute(query, account_ids)


async def get_all_gd_players() -> list[dict[str, Any]]:
    """Ngebaca semua statistik player GD jadi kumpulan dict."""
    
    async with get_connection() as conn:
        cursor = await conn.execute("SELECT * FROM gd_players ORDER BY nama_user_gd ASC")
        rows = await cursor.fetchall()
        return [dict(r) for r in rows]


# -----------------------------------------------------------------------------
# Riwayat Downtime
# -----------------------------------------------------------------------------

async def get_downtime_history() -> list[dict[str, Any]]:
    """Ngebaca riwayat downtime bot dari database."""
    async with get_connection() as conn:
        cursor = await conn.execute("SELECT status, timestamp, alasan FROM downtime_history ORDER BY id ASC")
        rows = await cursor.fetchall()
        return [{"status": r["status"], "timestamp": r["timestamp"], "alasan": r["alasan"]} for r in rows]


async def save_downtime_history(riwayat: list[dict[str, Any]]) -> None:
    """Nyimpan atau ngupdate daftar riwayat downtime bot."""
    async with get_connection() as conn:
        await conn.execute("DELETE FROM downtime_history")
        batch = [(item["status"], str(item["timestamp"]), item["alasan"]) for item in riwayat]
        if batch:
            await conn.executemany(
                "INSERT INTO downtime_history (status, timestamp, alasan) VALUES (?, ?, ?)",
                batch
            )


# -----------------------------------------------------------------------------
# Statistik Harian
# -----------------------------------------------------------------------------

async def get_daily_stats() -> dict[str, Any]:
    """Ngebaca data statistik harian dari database."""
    async with get_connection() as conn:
        cursor = await conn.execute("SELECT key, value FROM daily_stats")
        rows = await cursor.fetchall()
        result: dict[str, Any] = {}
        for r in rows:
            k, v = r["key"], r["value"]
            if k == "emoji_digunakan":
                try:
                    result[k] = json_loads(v)
                except Exception:  # noqa: BLE001
                    result[k] = {}
            else:
                try:
                    result[k] = int(v)
                except (ValueError, TypeError):
                    result[k] = v
        return result


async def save_daily_stats(data_stats: dict[str, Any]) -> None:
    """Nyimpan atau ngupdate statistik harian ke database."""
    batch = []
    for k, v in data_stats.items():
        if isinstance(v, (dict, list, collections.Counter)):
            val_str = json_dumps(dict(v) if isinstance(v, collections.Counter) else v)
        else:
            val_str = str(v)
        batch.append((k, val_str))
    
    if batch:
        async with get_connection() as conn:
            await conn.executemany("""
                INSERT INTO daily_stats (key, value) VALUES (?, ?)
                ON CONFLICT(key) DO UPDATE SET value = excluded.value
            """, batch)


async def reset_daily_stats() -> None:
    """Ngapus seluruh data statistik harian."""
    async with get_connection() as conn:
        await conn.execute("DELETE FROM daily_stats")


# -----------------------------------------------------------------------------
# Durasi VC (Voice Channel)
# -----------------------------------------------------------------------------

async def get_vc_durations() -> dict[str, dict[int, str]]:
    """Ngebaca status durasi VC, live streaming, dan VC kosong dari database."""
    async with get_connection() as conn:
        cursor = await conn.execute("SELECT category, target_id, timestamp FROM vc_durations")
        rows = await cursor.fetchall()
        result: dict[str, dict[int, str]] = {
            "status_vc": {},
            "status_live": {},
            "status_vc_kosong": {}
        }
        for r in rows:
            cat = r["category"]
            if cat not in result:
                result[cat] = {}
            result[cat][r["target_id"]] = r["timestamp"]
        return result


async def save_vc_durations(
    status_vc: dict[int, str],
    status_live: dict[int, str],
    status_vc_kosong: dict[int, str]
) -> None:
    """Nyimpan status durasi VC ke database."""
    categories = [
        ("status_vc", status_vc),
        ("status_live", status_live),
        ("status_vc_kosong", status_vc_kosong),
    ]
    batch = []
    for cat, d in categories:
        for tid, ts in d.items():
            batch.append((cat, int(tid), str(ts)))
    
    async with get_connection() as conn:
        await conn.execute("DELETE FROM vc_durations")
        if batch:
            await conn.executemany(
                "INSERT INTO vc_durations (category, target_id, timestamp) VALUES (?, ?, ?)",
                batch
            )


# -----------------------------------------------------------------------------
# Fitur Kartu Member BinRoom
# -----------------------------------------------------------------------------

async def get_binroom_member(user_id: int) -> dict[str, Any] | None:
    """Ngebaca data kartu member BinRoom berdasarkan User ID."""
    async with get_connection() as conn:
        cursor = await conn.execute(
            "SELECT custom_name, join_number FROM binroom_memberships WHERE user_id = ?",
            (user_id,)
        )
        row = await cursor.fetchone()
        if row:
            return {"custom_name": row["custom_name"], "join_number": row["join_number"]}
    return None


async def save_binroom_custom_name(user_id: int, custom_name: str, join_number: int) -> None:
    """Nyimpan atau ngupdate nama kustom kartu member."""
    async with get_connection() as conn:
        await conn.execute("""
            INSERT INTO binroom_memberships (user_id, custom_name, join_number)
            VALUES (?, ?, ?)
            ON CONFLICT(user_id) DO UPDATE SET custom_name = excluded.custom_name
        """, (user_id, custom_name, join_number))


async def save_binroom_join_number(user_id: int, join_number: int) -> None:
    """Nyimpan nomor urut gabung member jika belum ada."""
    async with get_connection() as conn:
        await conn.execute("""
            INSERT INTO binroom_memberships (user_id, join_number)
            VALUES (?, ?)
            ON CONFLICT(user_id) DO NOTHING
        """, (user_id, join_number))


async def reset_binroom_custom_name(user_id: int) -> None:
    """Ngereset nama kustom member (ngeset custom_name jadi NULL)."""
    async with get_connection() as conn:
        await conn.execute("""
            UPDATE binroom_memberships
            SET custom_name = NULL
            WHERE user_id = ?
        """, (user_id,))


async def delete_binroom_member(user_id: int) -> None:
    """Ngapus data kartu member BinRoom pas member keluar dari server."""
    async with get_connection() as conn:
        await conn.execute(
            "DELETE FROM binroom_memberships WHERE user_id = ?",
            (user_id,)
        )


# -----------------------------------------------------------------------------
# Fitur Streak Harian Member
# -----------------------------------------------------------------------------

WIB = timezone(timedelta(hours=7))

async def proses_streak_harian(user_id:int) -> dict[str, Any]:
    """Ngeproses streak harian member sesuai zona waktu WIB.
    
    Mengembalikan dictionary berisi status update
    (new_)"""
    
    wib_skrg = datetime.now(WIB)
    str_hari_ini = wib_skrg.strftime("%Y-%m-%d")
    str_kemarin = (wib_skrg - timedelta(days=1)).strftime("%Y-%m-%d")
    
    async with get_connection() as conn:
        cursor = await conn.execute(
            """
            SELECT streak_skrg, streak_terlama, terakhir_aktif
            FROM streak_member WHERE user_id = ?
            """,
            (user_id,),
        )
        row = await cursor.fetchone()
        
        if not row:
            #pertama kali
            await conn.execute("""
                INSERT INTO streak_member (user_id, streak_skrg, streak_terlama, terakhir_aktif)
                VALUES (?, 1, 1, ?)
                """,
                (user_id, str_hari_ini),
            )
            return {
                "status": "baru",
                "streak_skrg": 1,
                "streak_terlama": 1
            }
        
        terakhir_aktif = row["terakhir_aktif"]
        streak_skrg = row["streak_skrg"]
        streak_terlama = row["streak_terlama"]
        
        if terakhir_aktif == str_hari_ini:
            return {
                "status": "sudah_masuk",
                "streak_skrg": streak_skrg,
                "streak_terlama": streak_terlama
            }
        
        #nimbrung tiap hari -> naik streak
        if terakhir_aktif == str_kemarin:
            streak_skrg += 1
            streak_terlama = max(streak_terlama, streak_skrg)
            status = "streak_naik"
        #lewat 1 hari -> reset
        else:
            streak_skrg = 1
            status = "streak_reset"
        
        await conn.execute("""
            UPDATE streak_member
            SET streak_skrg = ?, streak_terlama = ?, terakhir_aktif = ?
            WHERE user_id = ?
        """, (streak_skrg, streak_terlama, str_hari_ini, user_id))
        
        return {
            "status": status,
            "streak_skrg": streak_skrg,
            "streak_terlama": streak_terlama
        }

async def baca_streak_member(user_id:int) -> dict[str, Any]:
    """Ngebaca data streak member.
    Kalo kemarin gk aktif, streak-nya otomatis dianggap reset ke 0."""
    
    wib_skrg = datetime.now(WIB)
    str_hari_ini = wib_skrg.strftime("%Y-%m-%d")
    str_kemarin = (wib_skrg - timedelta(days=1)).strftime("%Y-%m-%d")
    
    async with get_connection() as conn:
        cursor = await conn.execute("""
            SELECT streak_skrg, streak_terlama, terakhir_aktif
            FROM streak_member WHERE user_id = ?
        """, (user_id,))
        row = await cursor.fetchone()
        
        if not row:
            return {
                "streak_skrg": 0,
                "streak_terlama": 0,
                "terakhir_aktif": None
            }
        
        terakhir_aktif = row["terakhir_aktif"]
        streak_skrg = row["streak_skrg"]
        
        #klo gk aktif di hari ini atw kmarin, hangus
        if terakhir_aktif not in (str_hari_ini, str_kemarin):
            streak_skrg = 0
        
        return {
            "streak_skrg": streak_skrg,
            "streak_terlama": row["streak_terlama"],
            "terakhir_aktif": terakhir_aktif
        }