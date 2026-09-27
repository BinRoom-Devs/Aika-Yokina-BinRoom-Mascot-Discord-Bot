"""Berisi semua konfigurasi chatbot Aika."""

import os
import re
from pathlib import Path

from dotenv import load_dotenv

DIREKTORI_UTAMA = Path(__file__).resolve().parent.parent.parent
JALUR_ENV = DIREKTORI_UTAMA / ".env"
load_dotenv(dotenv_path=JALUR_ENV, override=True)

GROQ_API_KEY = os.getenv("GROQ_API_KEY")

WAKTU_TUNGGU_SALURAN_TARGET = 3.0
WAKTU_TUNGGU_MENTION = 10.0
MAKS_GAMBAR_PER_CHAT = 3
UKURAN_FILE_MAKS_BYTES = 20 * 1024 * 1024  
MENIT_RATE_LIMIT_REQ = 28
RATE_LIMIT_HARIAN = 950
RATE_LIMIT_TOKEN_PERMENIT = 7500
RATE_LIMIT_TOKEN_PERHARI = 190000
MAKS_TOKEN_RESPON = 75
PERKIRAAN_TOKEN_DEFAULT = 1500
ID_ROLE_REASONING = 1548693945729556560

RE_PROSES_MIKIR = re.compile(r'<think>.*?(?:</think>|$)', re.DOTALL)
RE_TAG_KONTEN = re.compile(r'\[CONTENT\](.*?)\[/CONTENT\]', re.DOTALL)
RE_HAPUS_TAG_KONTEN = re.compile(r'\[/?CONTENT\]')
RE_BARIS_BARU_GANDA = re.compile(r'\n{3,}')
RE_PEMISAH_BAGIAN = re.compile(r'\n\s*---\s*\n')
RE_WAKTU_RATE_LIMIT = re.compile(r"Please try again in (?:(\d+)h)?(?:(\d+)m)?(?:([\d\.]+)s)?")

WARNA_AIKA = 0xD675C1