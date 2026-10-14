from pathlib import Path

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Pengaturan(BaseSettings):
    """
    Konfigurasi terpusat untuk bot Aika Yokina.
    
    Menggunakan Pydantic Settings untuk validasi otomatis dan type safety.
    Semua konfigurasi dimuat dari file .env atau environment variables.
    """
    
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
        case_sensitive=False
    )
    
    
    # kredensial Aika
    token_bot: str = Field(
        ...,
        alias="TOKEN_BOT",
        description="Token bot Discord dari Discord Developer Portal"
    )
    id_pemilik: int = Field(
        default=1524951093560213638,
        alias="OWNER_ID",
        description="ID pemilik bot (@arumugi_4405)"
    )
    id_server_binroom: int = Field(
        default=904972136328888340,
        alias="BINROOM",
        description="ID server BinRoom utama"
    )
    warna_aika: int = Field(
        default=0xD675C1,
        description="Warna hex Aika untuk embed (pink)"
    )
    warna_merah: int = Field(
        default=0xDD2E44,
        description="Warna hex merah untuk embed dan container"
    )
    warna_kuning: int = Field(
        default=0xFCCA58,
        description="Warna hex kuning untuk embed dan container"
    )
    warna_hijau: int = Field(
        default=0x77B256,
        description="Warna hex hijau untuk embed dan container"
    )
    
    
    # channel
    id_channel_aika: int | None = Field(
        default=1540785170335006833,
        alias="AIKA_CHANNEL_ID",
        description="ID channel khusus untuk chat Aika"
    )
    id_channel_logging: int = Field(
        default=932191307789656064,
        alias="CHANNEL_LOGGING",
        description="ID channel untuk log aktivitas bot"
    )
    id_channel_sambutan: int = Field(
        default=904973494813614141,
        alias="CHANNEL_SAMBUTAN",
        description="ID channel sambutan member baru"
    )
    id_channel_ranjau: int = Field(
        default=904973494813614141,
        alias="CHANNEL_RANJAU",
        description="ID channel untuk honeypot/ranjau"
    )
    
    
    # leaderboard GD
    hash_gjp2_bot: str = Field(
        ...,
        alias="HASH_GJP2_BOT",
        description="Hash GJP2 untuk komunikasi dengan Geometry Dash API"
    )
    rahasia_boomlings: str = Field(
        ...,
        alias="BOOMLINGS_SECRET",
        description="Secret API Boomlings untuk Geometry Dash"
    )
    id_channel_leaderboard: int = Field(
        default=1545795446214098975,
        description="ID channel untuk leaderboard GD"
    )
    nama_akun_gd_bot: str = Field(
        default="AikaBot",
        description="Nama akun Geometry Dash bot"
    )
    id_akun_gd_bot: int = Field(
        default=43800101,
        description="Account ID Geometry Dash bot"
    )
    
    
    # database
    jalur_database: str | None = Field(
        default=None,
        alias="DATABASE_PATH",
        description="Jalur kustom untuk file database SQLite"
    )
    
    
    # Pengaturan Chatbot AI Aika
    api_key_groq: str = Field(
        ...,
        alias="GROQ_API_KEY",
        description="Kunci API Groq untuk model AI Qwen"
    )
    cooldown_channel_target: float = Field(
        default=3.0,
        description="Waktu tunggu respons di channel target (detik)"
    )
    cooldown_mention: float = Field(
        default=10.0,
        description="Waktu tunggu respons saat bot di-mention (detik)"
    )
    maksimal_gambar_per_chat: int = Field(
        default=3,
        description="Maksimal gambar yang bisa diproses per chat"
    )
    ukuran_file_maksimal_bytes: int = Field(
        default=20 * 1024 * 1024,
        description="Ukuran maksimal file yang diterima (default: 20 MB)"
    )
    menit_limit_permintaan: int = Field(
        default=28,
        description="Limit permintaan API per menit"
    )
    limit_harian: int = Field(
        default=950,
        description="Limit permintaan API harian"
    )
    limit_token_per_menit: int = Field(
        default=7500,
        description="Limit token per menit"
    )
    limit_token_per_hari: int = Field(
        default=190000,
        description="Limit token per hari"
    )
    maksimal_token_respon: int = Field(
        default=75,
        description="Maksimal token per respons AI"
    )
    perkiraan_token_default: int = Field(
        default=1500,
        description="Perkiraan token default untuk setiap pesan"
    )
    id_role_reasoning: int = Field(
        default=1556752402550489152,
        description="ID role Discord untuk mode reasoning"
    )
    maksimal_konteks_channel: int = Field(
        default=30,
        description="Maksimal pesan konteks channel yang disimpan untuk referensi"
    )
    
    
    # link eksternal
    gambar_header_leaderboard: str = Field(
        default="https://cdn.discordapp.com/attachments/863959650448703538/1543244407145373829/Untitled-1.png",
        description="URL gambar header untuk leaderboard"
    )
    ikon_penulis_leaderboard: str = Field(
        default="https://cdn.discordapp.com/attachments/863959650448703538/1543780342379319337/rankIcon_1_001.png?ex=6a961cfb&is=6a94cb7b&hm=33bf6524a61776ae3bf21ccd07a9aab07260085a9c0dddf098ad73ea4bd19f59&",
        description="URL ikon penulis untuk leaderboard"
    )
    nama_penulis_leaderboard: str = Field(
        default="BinRoom Geometry Dash Players Leaderboard",
        description="Nama penulis untuk embed leaderboard"
    )
    
    
    # property helper
    @property
    def jalur_database_terselesaikan(self) -> Path:
        if self.jalur_database:
            return Path(self.jalur_database)
        return self.direktori_utama / "data" / "aika.db"
    
    @property
    def direktori_utama(self) -> Path:
        return Path(__file__).parent
    
    @property
    def jalur_env(self) -> Path:
        return self.direktori_utama / ".env"


pengaturan = Pengaturan()