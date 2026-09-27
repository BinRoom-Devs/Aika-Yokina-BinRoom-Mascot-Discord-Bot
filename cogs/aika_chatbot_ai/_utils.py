"""Berisi utilitas statis buat ngeproses gambar, bersihin regex, layout teks, dll."""

import discord

from ._config import (
    RE_PEMISAH_BAGIAN,
    RE_PROSES_MIKIR,
    RE_TAG_KONTEN,
    UKURAN_FILE_MAKS_BYTES,
)


def proses_gambar(attachment:discord.Attachment) -> dict | None:
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

def masukin_ke_component_v2(raw_text:str) -> tuple[str, list[discord.ui.TextDisplay|discord.ui.Separator] | None, str]:
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