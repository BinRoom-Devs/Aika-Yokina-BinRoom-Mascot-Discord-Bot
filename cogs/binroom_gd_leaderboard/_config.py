import os

import discord
from dotenv import load_dotenv

load_dotenv()

ID_CHANNEL_LEADERBOARD = 1545795446214098975 

NAMA_AKUN_GD_BOT = "AikaBot"
ACCOUNT_ID_GD_BOT = 43800101
HASH_GJP2_BOT = os.getenv("HASH_GJP2_BOT")
BOOMLINGS_SECRET = os.getenv("BOOMLINGS_SECRET")

GAMBAR_HEADER = "https://cdn.discordapp.com/attachments/863959650448703538/1543244407145373829/Untitled-1.png"
AUTHOR_ICON_LEADERBOARD = "https://cdn.discordapp.com/attachments/863959650448703538/1543780342379319337/rankIcon_1_001.png?ex=6a961cfb&is=6a94cb7b&hm=33bf6524a61776ae3bf21ccd07c9aab07260085a9c0dddf098ad73ea4bd19f59&"
AUTHOR_NAME_LEADERBOARD = "BinRoom Geometry Dash Players Leaderboard"

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