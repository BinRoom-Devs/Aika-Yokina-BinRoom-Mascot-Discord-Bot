import json
import os
import sqlite3
from pathlib import Path

DB_PATH = Path(__file__).parent / "data" / "aika.db"

def init_db():
    """Buat database dan bikin table kalo awalnya gaada."""
    os.makedirs(DB_PATH.parent, exist_ok=True)
    
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    #table user_chats
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS user_chats (
            user_id INTEGER PRIMARY KEY,
            chat_history TEXT
        )
    """)
    
    #table gd_players 
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS gd_players (
            player_id INTEGER PRIMARY KEY,
            player_name TEXT,
            stars INTEGER,
            coins INTEGER,
            user_demons INTEGER,
            creator_points INTEGER
        )
    """)
    
    #table lore
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS lore (
            id INTEGER PRIMARY KEY CHECK (id = 1),
            origin_story TEXT,
            original_illustrator TEXT,
            contributors TEXT
        )
    """)
    
    #masukin lore default
    cursor.execute("SELECT * FROM lore WHERE id = 1")
    if not cursor.fetchone():
        cursor.execute("""
            INSERT INTO lore (id, origin_story, original_illustrator, contributors)
            VALUES (1, '', '', '')
        """)
    
    conn.commit()
    conn.close()

def save_user_chat(user_id:int, chat_history:list):
    """Nyimpan histori chat buat user."""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    cursor.execute("""
        INSERT OR REPLACE INTO user_chats (user_id, chat_history)
        VALUES (?, ?)
    """, (user_id, json.dumps(chat_history)))
    
    conn.commit()
    conn.close()

def load_user_chat(user_id:int) -> list:
    """Load histori chat buat user."""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    cursor.execute("SELECT chat_history FROM user_chats WHERE user_id = ?", (user_id,))
    result = cursor.fetchone()
    conn.close()
    
    if result:
        return json.loads(result[0])
    return []

def load_all_user_chats() -> dict:
    """Load semua chat user."""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    cursor.execute("SELECT user_id, chat_history FROM user_chats")
    results = cursor.fetchall()
    conn.close()
    
    return {user_id: json.loads(chat_history) for user_id, chat_history in results}

def save_all_user_chats(user_chats:dict):
    """Nyimpan semua chat user."""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    for user_id, chat_history in user_chats.items():
        cursor.execute("""
            INSERT OR REPLACE INTO user_chats (user_id, chat_history)
            VALUES (?, ?)
        """, (user_id, json.dumps(chat_history)))
    
    conn.commit()
    conn.close()

def delete_user_chat(user_id:int):
    """Ngehapus histori chat buat user."""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    cursor.execute("DELETE FROM user_chats WHERE user_id = ?", (user_id,))
    
    conn.commit()
    conn.close()

def save_all_gd_players(players: list):
    """Nyimpan semua data player GD dalam server."""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    cursor.execute("DELETE FROM gd_players")
    
    for player in players:
        cursor.execute("""
            INSERT INTO gd_players (player_id, player_name, stars, coins, user_demons, creator_points)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (
            player.get('player_id'),
            player.get('player_name'),
            player.get('stars', 0),
            player.get('coins', 0),
            player.get('user_demons', 0),
            player.get('creator_points', 0)
        ))
    
    conn.commit()
    conn.close()

def load_all_gd_players() -> list:
    """Load semua data player GD server."""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    cursor.execute("SELECT player_id, player_name, stars, coins, user_demons, creator_points FROM gd_players")
    results = cursor.fetchall()
    conn.close()
    
    return [
        {
            'player_id': row[0],
            'player_name': row[1],
            'stars': row[2],
            'coins': row[3],
            'user_demons': row[4],
            'creator_points': row[5]
        }
        for row in results
    ]

def get_lore() -> dict:
    """Baca data lore Aika."""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    cursor.execute("SELECT origin_story, original_illustrator, contributors FROM lore WHERE id = 1")
    result = cursor.fetchone()
    conn.close()
    
    if result:
        return {
            'origin_story': result[0],
            'original_illustrator': result[1],
            'contributors': json.loads(result[2]) if result[2] else []
        }
    return {
        'origin_story': '',
        'original_illustrator': '',
        'contributors': []
    }

def save_lore(lore_data:dict):
    """Nyimpan data lore Aika."""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    cursor.execute("""
        UPDATE lore
        SET origin_story = ?, original_illustrator = ?, contributors = ?
        WHERE id = 1
    """, (
        lore_data.get('origin_story', ''),
        lore_data.get('original_illustrator', ''),
        json.dumps(lore_data.get('contributors', []))
    ))
    
    conn.commit()
    conn.close()