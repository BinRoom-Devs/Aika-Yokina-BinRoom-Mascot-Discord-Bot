"""Berisi semua konfigurasi chatbot Aika."""

import re

import config

GROQ_API_KEY = config.pengaturan.api_key_groq

WAKTU_TUNGGU_SALURAN_TARGET = config.pengaturan.cooldown_channel_target
WAKTU_TUNGGU_MENTION = config.pengaturan.cooldown_mention
MAKS_GAMBAR_PER_CHAT = config.pengaturan.maksimal_gambar_per_chat
UKURAN_FILE_MAKS_BYTES = config.pengaturan.ukuran_file_maksimal_bytes
MENIT_RATE_LIMIT_REQ = config.pengaturan.menit_limit_permintaan
RATE_LIMIT_HARIAN = config.pengaturan.limit_harian
RATE_LIMIT_TOKEN_PERMENIT = config.pengaturan.limit_token_per_menit
RATE_LIMIT_TOKEN_PERHARI = config.pengaturan.limit_token_per_hari
MAKS_TOKEN_RESPON = config.pengaturan.maksimal_token_respon
PERKIRAAN_TOKEN_DEFAULT = config.pengaturan.perkiraan_token_default
ID_ROLE_REASONING = config.pengaturan.id_role_reasoning
MAKS_KONTEKS_CHANNEL = getattr(config.pengaturan, 'maksimal_konteks_channel', 30)

RE_PROSES_MIKIR = re.compile(r'<think>.*?(?:</think>|$)', re.DOTALL)
RE_TAG_KONTEN = re.compile(r'\[CONTENT\](.*?)\[/CONTENT\]', re.DOTALL)
RE_HAPUS_TAG_KONTEN = re.compile(r'\[/?CONTENT\]')
RE_BARIS_BARU_GANDA = re.compile(r'\n{3,}')
RE_PEMISAH_BAGIAN = re.compile(r'\n\s*---\s*\n')
RE_WAKTU_RATE_LIMIT = re.compile(r"Please try again in (?:(\d+)h)?(?:(\d+)m)?(?:([\d\.]+)s)?")

WARNA_AIKA = config.pengaturan.warna_aika