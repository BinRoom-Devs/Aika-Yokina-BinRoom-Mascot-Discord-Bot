"""Berisi utilitas statis buat ngeproses gambar, bersihin regex, layout teks, dll."""

import re

import discord

from ._config import (
    RE_PEMISAH_BAGIAN,
    RE_PROSES_MIKIR,
    RE_TAG_KONTEN,
    UKURAN_FILE_MAKS_BYTES,
)

_LATEX_CONVERTER = None

def _get_latex_converter():
    global _LATEX_CONVERTER
    if _LATEX_CONVERTER is None:
        from pylatexenc.latex2text import LatexNodes2Text
        _LATEX_CONVERTER = LatexNodes2Text(
            #keep_braces_around_math=False,
            keep_inline_math=False,
            keep_comments=False
        )
    return _LATEX_CONVERTER

def proses_gambar(attachment: discord.Attachment) -> dict | None:
    if attachment.size > UKURAN_FILE_MAKS_BYTES:
        return None
    return {
        "type": "image_url",
        "image_url": {"url": attachment.url}
    }

def ilangin_mention(teks: str) -> str:
    return teks.replace("@everyone", "`@everyone`").replace("@here", "`@here`")

def hapus_alur_berpikir(teks: str) -> str:
    if not teks:
        return ""
    return RE_PROSES_MIKIR.sub("", teks).strip()

def ekstrak_teksnya_doang(daftar_konten: list) -> str:
    kumpulan_teks = []
    for item in daftar_konten:
        if item.get("type") == "text":
            kumpulan_teks.append(item.get("text", ""))
        elif item.get("type") == "image_url":
            kumpulan_teks.append("[User uploaded an image]")
    return " ".join(kumpulan_teks).strip()

def sanitasi_matematika(teks: str) -> str:
    if not teks:
        return ""
    
    try:
        converter = _get_latex_converter()
        teks_konversi = converter.latex_to_text(teks)
    except Exception as e:  # noqa: BLE001
        print(f"[pylatexenc] Sanitasi rumus matematika gagal: {e}")
        teks_konversi = teks
    
    teks_konversi = re.sub(r'\$\$(.*?)\$\$', r'\1', teks_konversi, flags=re.DOTALL)
    teks_konversi = re.sub(r'\$(.*?)\$', r'\1', teks_konversi)
    
    sub_map = str.maketrans("0123456789", "₀₁₂₃₄₅₆₇₈₉")
    teks_konversi = re.sub(r'_([0-9])', lambda m: m.group(1).translate(sub_map), teks_konversi)
    
    teks_konversi = re.sub(r'(\|[^\n]+\|)', r'\1\n', teks_konversi)
    teks_konversi = re.sub(r'\n{3,}', '\n\n', teks_konversi)
    
    return teks_konversi.strip()

def masukin_ke_component_v2(raw_text: str) -> tuple[str, list[discord.ui.TextDisplay | discord.ui.Separator] | None, str]:
    kecocokan = RE_TAG_KONTEN.search(raw_text)
    if not kecocokan:
        return raw_text.strip(), None, ""
    
    teks_sebelum = raw_text[:kecocokan.start()].strip()
    teks_sesudah = raw_text[kecocokan.end():].strip()
    
    pesan_inti = kecocokan.group(1).strip()
    bagian_mentahan = RE_PEMISAH_BAGIAN.split(pesan_inti)
    
    components = []
    total_bagian = len(bagian_mentahan)
    for idx, bagian in enumerate(bagian_mentahan):
        teks_bagian = bagian.strip()
        if not teks_bagian:
            continue
        components.append(discord.ui.TextDisplay(content=teks_bagian))
        if idx < total_bagian - 1:
            components.append(discord.ui.Separator(spacing=discord.SeparatorSpacing.small))
    
    return teks_sebelum, components, teks_sesudah