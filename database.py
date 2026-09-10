import sqlite3, os, json, threading
from contextlib import contextmanager
from dotenv import load_dotenv

load_dotenv()

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_ENV_PATH = os.getenv("DATABASE_PATH", "data/aika.db")
if os.path.isabs(DB_ENV_PATH):
    DATABASE_PATH = DB_ENV_PATH
else:
    DATABASE_PATH = os.path.normpath(os.path.join(BASE_DIR, DB_ENV_PATH))

_db_lock = threading.RLock()


def get_db_path() -> str:
    return DATABASE_PATH


@contextmanager
def get_connection():
    os.makedirs(os.path.dirname(DATABASE_PATH), exist_ok=True)
    with _db_lock:
        conn = sqlite3.connect(DATABASE_PATH, timeout=10.0, check_same_thread=False)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA journal_mode=WAL;")
        conn.execute("PRAGMA synchronous=NORMAL;")
        conn.execute("PRAGMA busy_timeout=10000;")
        try:
            yield conn
            conn.commit()
        except Exception:
            conn.rollback()
            raise
        finally:
            conn.close()


def init_db():
    with get_connection() as conn:
        cursor = conn.cursor()

        #table lore & persona
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS aika_lore (
                id INTEGER PRIMARY KEY CHECK (id = 1),
                original_illustrator TEXT NOT NULL DEFAULT '',
                origin_story TEXT NOT NULL DEFAULT '',
                contributors TEXT NOT NULL DEFAULT '[]',
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
        """)

        #table memori chat sama para user
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS user_chats (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                role TEXT NOT NULL,
                content TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
        """)
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_user_chats_user_id ON user_chats(user_id);
        """)

        #table para player GD
        cursor.execute("""
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
                icon INTEGER DEFAULT 1,
                col1 INTEGER DEFAULT 0,
                col2 INTEGER DEFAULT 0,
                glow INTEGER DEFAULT 0,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
        """)
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_gd_players_nama ON gd_players(nama_user_gd COLLATE NOCASE);
        """)
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_gd_players_discord ON gd_players(id_user_discord);
        """)

    #migrasi otomatis dari json kalo misal kosong
    auto_migrate_from_json()


# ==============================================================================
# OPERASI LORE AIKA
# ==============================================================================

def get_lore() -> dict:
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT original_illustrator, origin_story, contributors FROM aika_lore WHERE id = 1;")
        row = cursor.fetchone()
        if row:
            try:
                contribs = json.loads(row["contributors"])
            except Exception:
                contribs = []
            return {
                "original_illustrator": row["original_illustrator"],
                "origin_story": row["origin_story"],
                "contributors": contribs
            }
        return {
            "original_illustrator": "",
            "origin_story": "",
            "contributors": []
        }


def save_lore(lore_data:dict) -> None:
    illustrator = lore_data.get("original_illustrator", "")
    origin = lore_data.get("origin_story", "")
    contribs = lore_data.get("contributors", [])
    contribs_json = json.dumps(contribs, ensure_ascii=False)

    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO aika_lore (id, original_illustrator, origin_story, contributors, updated_at)
            VALUES (1, ?, ?, ?, CURRENT_TIMESTAMP)
            ON CONFLICT(id) DO UPDATE SET
                original_illustrator = excluded.original_illustrator,
                origin_story = excluded.origin_story,
                contributors = excluded.contributors,
                updated_at = CURRENT_TIMESTAMP;
        """, (illustrator, origin, contribs_json))


# ==============================================================================
# OPERASI MEMORI PERCAKAPAN (USER CHATS)
# ==============================================================================

def load_all_user_chats() -> dict[int,list[dict]]:
    user_chats: dict[int, list[dict]] = {}
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT user_id, role, content FROM user_chats ORDER BY user_id, id ASC;")
        for row in cursor.fetchall():
            uid = int(row["user_id"])
            if uid not in user_chats:
                user_chats[uid] = []
            user_chats[uid].append({
                "role": row["role"],
                "content": row["content"]
            })
    return user_chats


def get_user_chat(user_id:int) -> list[dict]:
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT role, content FROM user_chats WHERE user_id = ? ORDER BY id ASC;", (user_id,))
        return [{"role": row["role"], "content": row["content"]} for row in cursor.fetchall()]


def save_user_chat(user_id:int, messages:list[dict]) -> None:
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("DELETE FROM user_chats WHERE user_id = ?;", (user_id,))
        for msg in messages:
            role = msg.get("role", "")
            content = msg.get("content", "")
            if role and content:
                cursor.execute(
                    "INSERT INTO user_chats (user_id, role, content) VALUES (?, ?, ?);",
                    (user_id, role, content)
                )


def save_all_user_chats(user_chats:dict[int,list[dict]]) -> None:
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("DELETE FROM user_chats;")
        for uid, messages in user_chats.items():
            for msg in messages:
                role = msg.get("role", "")
                content = msg.get("content", "")
                if role and content:
                    cursor.execute(
                        "INSERT INTO user_chats (user_id, role, content) VALUES (?, ?, ?);",
                        (int(uid), role, content)
                    )


def add_chat_message(user_id:int, role:str, content:str) -> None:
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(
            "INSERT INTO user_chats (user_id, role, content) VALUES (?, ?, ?);",
            (user_id, role, content)
        )


def delete_user_chat(user_id:int) -> None:
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("DELETE FROM user_chats WHERE user_id = ?;", (user_id,))


def clear_all_user_chats() -> None:
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("DELETE FROM user_chats;")


# ==============================================================================
# OPERASI PEMAIN GEOMETRY DASH (GD PLAYERS)
# ==============================================================================

def load_all_gd_players() -> list[dict]:
    players = []
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT account_id_gd, nama_user_gd, player_id_gd, id_user_discord,
                   stars, moons, diamonds, secret_coins, user_coins, demons, creator_points,
                   icon, col1, col2, glow
            FROM gd_players
            ORDER BY stars DESC;
        """)
        for row in cursor.fetchall():
            players.append({
                "nama_user_gd": row["nama_user_gd"],
                "account_id_gd": row["account_id_gd"],
                "player_id_gd": row["player_id_gd"],
                "id_user_discord": row["id_user_discord"],
                "statistik": {
                    "stars": row["stars"],
                    "moons": row["moons"],
                    "diamonds": row["diamonds"],
                    "secret_coins": row["secret_coins"],
                    "user_coins": row["user_coins"],
                    "demons": row["demons"],
                    "creator_points": row["creator_points"],
                },
                "icon": row["icon"],
                "col1": row["col1"],
                "col2": row["col2"],
                "glow": row["glow"],
            })
    return players


def upsert_gd_player(p:dict) -> None:
    stats = p.get("statistik", {})
    account_id = int(p.get("account_id_gd", 0))
    nama = p.get("nama_user_gd", "")
    player_id = int(p.get("player_id_gd", 0))
    id_discord = p.get("id_user_discord")
    if id_discord is not None:
        try:
            id_discord = int(id_discord)
        except (ValueError, TypeError):
            id_discord = None

    stars = int(stats.get("stars", 0))
    moons = int(stats.get("moons", 0))
    diamonds = int(stats.get("diamonds", 0))
    secret_coins = int(stats.get("secret_coins", 0))
    user_coins = int(stats.get("user_coins", 0))
    demons = int(stats.get("demons", 0))
    creator_points = int(stats.get("creator_points", 0))

    icon = int(p.get("icon", 1))
    col1 = int(p.get("col1", 0))
    col2 = int(p.get("col2", 0))
    glow = 1 if p.get("glow") else 0

    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO gd_players (
                account_id_gd, nama_user_gd, player_id_gd, id_user_discord,
                stars, moons, diamonds, secret_coins, user_coins, demons, creator_points,
                icon, col1, col2, glow, updated_at
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
                updated_at = CURRENT_TIMESTAMP;
        """, (
            account_id, nama, player_id, id_discord,
            stars, moons, diamonds, secret_coins, user_coins, demons, creator_points,
            icon, col1, col2, glow
        ))


def save_all_gd_players(players:list[dict]) -> None:
    with get_connection() as conn:
        cursor = conn.cursor()
        
        valid_account_ids = []
        for p in players:
            account_id = int(p.get("account_id_gd", 0))
            if account_id:
                valid_account_ids.append(account_id)

        #hapus player yang udah gaada di list
        if valid_account_ids:
            placeholders = ",".join("?" for _ in valid_account_ids)
            cursor.execute(f"DELETE FROM gd_players WHERE account_id_gd NOT IN ({placeholders});", valid_account_ids)
        else:
            cursor.execute("DELETE FROM gd_players;")

        #upsert tiap player
        for p in players:
            stats = p.get("statistik", {})
            account_id = int(p.get("account_id_gd", 0))
            nama = p.get("nama_user_gd", "")
            player_id = int(p.get("player_id_gd", 0))
            id_discord = p.get("id_user_discord")
            if id_discord is not None:
                try:
                    id_discord = int(id_discord)
                except (ValueError, TypeError):
                    id_discord = None

            stars = int(stats.get("stars", 0))
            moons = int(stats.get("moons", 0))
            diamonds = int(stats.get("diamonds", 0))
            secret_coins = int(stats.get("secret_coins", 0))
            user_coins = int(stats.get("user_coins", 0))
            demons = int(stats.get("demons", 0))
            creator_points = int(stats.get("creator_points", 0))

            icon = int(p.get("icon", 1))
            col1 = int(p.get("col1", 0))
            col2 = int(p.get("col2", 0))
            glow = 1 if p.get("glow") else 0

            cursor.execute("""
                INSERT INTO gd_players (
                    account_id_gd, nama_user_gd, player_id_gd, id_user_discord,
                    stars, moons, diamonds, secret_coins, user_coins, demons, creator_points,
                    icon, col1, col2, glow, updated_at
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
                    updated_at = CURRENT_TIMESTAMP;
            """, (
                account_id, nama, player_id, id_discord,
                stars, moons, diamonds, secret_coins, user_coins, demons, creator_points,
                icon, col1, col2, glow
            ))


def delete_gd_player(account_id_gd:int=None, nama_user_gd:str=None) -> bool:
    with get_connection() as conn:
        cursor = conn.cursor()
        if account_id_gd:
            cursor.execute("DELETE FROM gd_players WHERE account_id_gd = ?;", (int(account_id_gd),))
        elif nama_user_gd:
            cursor.execute("DELETE FROM gd_players WHERE nama_user_gd = ? COLLATE NOCASE;", (nama_user_gd,))
        else:
            return False
        return cursor.rowcount > 0


# ==============================================================================
# MIGRASI OTOMATIS DARI JSON
# ==============================================================================

def auto_migrate_from_json():
    json_dir = os.path.join(BASE_DIR, "json")

    with get_connection() as conn:
        cursor = conn.cursor()

        #migrasi lore
        cursor.execute("SELECT COUNT(*) AS cnt FROM aika_lore;")
        if cursor.fetchone()["cnt"] == 0:
            lore_file = os.path.join(json_dir, "json/aika_lore.json")
            if os.path.exists(lore_file):
                try:
                    with open(lore_file, "r", encoding="utf-8") as f:
                        lore_data = json.load(f)
                    save_lore(lore_data)
                    print("[SQLite] Migrasi otomatis: aika_lore.json berhasil diimpor ke database.")
                except Exception as e:
                    print(f"[SQLite] Gagal migrasi aika_lore.json: {e}")

        #migrasi user chats
        cursor.execute("SELECT COUNT(*) AS cnt FROM user_chats;")
        if cursor.fetchone()["cnt"] == 0:
            chat_file = os.path.join(json_dir, "json/user_chats_with_aika.json")
            if os.path.exists(chat_file):
                try:
                    with open(chat_file, "r", encoding="utf-8") as f:
                        chat_data = json.load(f)
                    chats = {int(k): v for k, v in chat_data.items()}
                    save_all_user_chats(chats)
                    total_msgs = sum(len(v) for v in chats.values())
                    print(f"[SQLite] Migrasi otomatis: {len(chats)} pengguna ({total_msgs} pesan) berhasil diimpor ke database.")
                except Exception as e:
                    print(f"[SQLite] Gagal migrasi user_chats_with_aika.json: {e}")

        #migrasi para player GD
        cursor.execute("SELECT COUNT(*) AS cnt FROM gd_players;")
        if cursor.fetchone()["cnt"] == 0:
            gd_file = os.path.join(json_dir, "json/binrum_gd_players.json")
            if os.path.exists(gd_file):
                try:
                    with open(gd_file, "r", encoding="utf-8") as f:
                        players_data = json.load(f)
                    save_all_gd_players(players_data)
                    print(f"[SQLite] Migrasi otomatis: {len(players_data)} pemain GD berhasil diimpor ke database.")
                except Exception as e:
                    print(f"[SQLite] Gagal migrasi binrum_gd_players.json: {e}")
