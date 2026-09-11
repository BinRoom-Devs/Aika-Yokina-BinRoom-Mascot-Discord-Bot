import discord
from nicegui import ui
from nicegui.context import context

import database

from .. import state
from ..utils import notify_for_client


def render_chatbot_tab(bot: discord.Client):
    # Header section with title and quick link buttons
    with ui.row().classes("w-full justify-between items-center mb-2"):
        ui.label("Aika AI Chatbot").classes("text-3xl font-extrabold text-white tracking-tight")
        with ui.row().classes("gap-2"):
            ui.link("Model Info ↗", "https://qwen.ai/blog?id=qwen3.6-27b", new_tab=True).classes(
                "px-3 py-1.5 bg-[#18181b] hover:bg-zinc-800 text-xs text-gray-300 font-medium rounded-xl border border-white/5 transition-colors"
            )
            ui.link("GitHub Repo ↗", "https://github.com/AbinDai/Aika-Yokina-BinRoom-Mascot-Discord-Bot", new_tab=True).classes(
                "px-3 py-1.5 bg-[#18181b] hover:bg-zinc-800 text-xs text-gray-300 font-medium rounded-xl border border-white/5 transition-colors"
            )

    ai_cog = bot.get_cog("AIPersona")
    #stats_cog = bot.get_cog("AIChatbotStats")

    if not ai_cog:
        with ui.card().classes("w-full bg-rose-950/40 border border-rose-500/20 rounded-2xl p-6 text-rose-300"):
            ui.label("⚠️ Cog AIPersona belum dimuat.").classes("font-bold text-base")
            ui.label("Pastikan bot sudah terhubung dan cog `ai_persona` berjalan.").classes("text-xs opacity-80")
        return None

    # --- 1. ACCUMULATED SESSION USAGE & LATEST REQUEST PERFORMANCE ---
    with ui.grid(columns=2).classes("w-full gap-6 mb-6"):
        with ui.card().classes("w-full bg-[#18181b] border border-white/5 rounded-2xl p-6 gap-4 shadow-xl text-white"):
            with ui.row().classes("w-full justify-between items-center"):
                ui.label("Akumulasi Sesi").classes("text-sm font-bold text-gray-200")
                ui.badge("Groq Qwen 3.6 27B").classes("bg-[#f05237] text-[#ffffff] text-xs px-2 py-1 rounded-full border border-orange-500/20")

            with ui.grid(columns=2).classes("w-full gap-4"):
                with ui.column().classes("gap-0 bg-[#0d0d0e] p-3 rounded-xl border border-white/5"):
                    ui.label("TOTAL REQUESTS").classes("text-[10px] font-bold text-gray-500 tracking-wider")
                    total_req_label = ui.label("0").classes("text-xl font-bold font-mono text-white")
                with ui.column().classes("gap-0 bg-[#0d0d0e] p-3 rounded-xl border border-white/5"):
                    ui.label("TOTAL TOKENS").classes("text-[10px] font-bold text-gray-500 tracking-wider")
                    total_tok_label = ui.label("0").classes("text-xl font-bold font-mono text-emerald-400")

                with ui.column().classes("gap-0 bg-[#0d0d0e] p-3 rounded-xl border border-white/5"):
                    ui.label("PROMPT TOKENS").classes("text-[10px] font-bold text-gray-500 tracking-wider")
                    prompt_tok_label = ui.label("0").classes("text-sm font-bold font-mono text-gray-300")
                with ui.column().classes("gap-0 bg-[#0d0d0e] p-3 rounded-xl border border-white/5"):
                    ui.label("COMPLETION TOKENS").classes("text-[10px] font-bold text-gray-500 tracking-wider")
                    comp_tok_label = ui.label("0").classes("text-sm font-bold font-mono text-gray-300")

        with ui.card().classes("w-full bg-[#18181b] border border-white/5 rounded-2xl p-6 gap-4 shadow-xl text-white"):
            with ui.row().classes("w-full justify-between items-center"):
                ui.label("Performa Request Terkini").classes("text-sm font-bold text-gray-200")
                tps_badge = ui.badge("0.0 tok/s").classes("bg-emerald-500/10 text-emerald-400 text-xs px-2 py-1 rounded-full border border-emerald-500/20 font-mono")

            with ui.grid(columns=3).classes("w-full bg-[#0d0d0e] p-4 rounded-xl border border-white/5 text-center gap-2"):
                with ui.column().classes("items-center gap-0"):
                    ui.label("TOTAL WAKTU").classes("text-[10px] font-bold text-gray-500 tracking-wider")
                    total_time_label = ui.label("0.000s").classes("text-base font-bold text-white font-mono")
                with ui.column().classes("items-center gap-0"):
                    ui.label("PROMPT TIME").classes("text-[10px] font-bold text-gray-500 tracking-wider")
                    prompt_time_label = ui.label("0.000s").classes("text-base font-bold text-gray-300 font-mono")
                with ui.column().classes("items-center gap-0"):
                    ui.label("PROCESS TIME").classes("text-[10px] font-bold text-gray-500 tracking-wider")
                    comp_time_label = ui.label("0.000s").classes("text-base font-bold text-gray-300 font-mono")

            with ui.row().classes("w-full justify-between items-center text-xs text-gray-400 px-1"):
                queue_time_label = ui.label("Antrean API: 0.000s").classes("font-mono")
                last_tokens_label = ui.label("Last token payload: 0 / 0").classes("font-mono")

    # --- 2. LIVE GROQ RATE LIMIT QUOTAS ---
    with ui.card().classes("w-full bg-[#18181b] border border-white/5 rounded-2xl p-6 gap-4 shadow-xl text-white mb-6"):
        with ui.row().classes("w-full justify-between items-center"):
            ui.label("Kuota Real-time Groq API").classes("text-sm font-bold text-gray-200")
            ui.label("Dynamic Headers").classes("text-xs text-gray-400 font-mono")

        with ui.grid(columns=2).classes("w-full gap-6"):
            with ui.column().classes("w-full gap-2 bg-[#0d0d0e] p-4 rounded-xl border border-white/5"):
                with ui.row().classes("w-full justify-between text-xs"):
                    ui.label("Kuota Request Harian").classes("font-semibold text-gray-300")
                    rpd_pct_label = ui.label("100% Sisa").classes("font-mono text-emerald-400")
                rpd_progress = ui.linear_progress(value=1.0, show_value=False).props("color=pink-4 track-color=grey-9")
                with ui.row().classes("w-full justify-between text-[11px] text-gray-400 font-mono mt-1"):
                    rpd_count_label = ui.label("Remaining: - / -")
                    rpd_reset_label = ui.label("Reset: -")

            with ui.column().classes("w-full gap-2 bg-[#0d0d0e] p-4 rounded-xl border border-white/5"):
                with ui.row().classes("w-full justify-between text-xs"):
                    ui.label("Kuota Token per Menit").classes("font-semibold text-gray-300")
                    tpm_pct_label = ui.label("100% Sisa").classes("font-mono text-emerald-400")
                tpm_progress = ui.linear_progress(value=1.0, show_value=False).props("color=cyan-4 track-color=grey-9")
                with ui.row().classes("w-full justify-between text-[11px] text-gray-400 font-mono mt-1"):
                    tpm_count_label = ui.label("Remaining: - / -")
                    tpm_reset_label = ui.label("Reset: -")

    ui.separator().classes("w-full bg-[#18181b] mt-4 mb-8 h-1 rounded-full")

    # --- 3. MEMORY & CHAT STORAGE ---
    with ui.grid(columns=2).classes("w-full gap-6 mb-6"):
        with ui.card().classes("w-full bg-[#18181b] border border-white/5 rounded-[24px] p-6 shadow-xl text-white"):
            ui.label("Penyimpanan chat per user").classes("text-xl font-extrabold text-white mb-4")
            
            with ui.row().classes("w-full h-64 gap-6 no-wrap items-center"):
                with ui.column().classes("w-2/5 h-full overflow-y-auto bg-[#09090b] rounded-2xl p-2 gap-1 border border-white/5 shadow-inner") as user_list_container:
                    pass 
                
                with ui.column().classes("w-3/5 h-full justify-center gap-4 px-2") as details_container:
                    pass 

            selected_stats_user = {"uid": None}
            user_profile_cache = {}

            async def get_discord_user_profile(uid):
                if uid in user_profile_cache:
                    return user_profile_cache[uid]
                
                discord_user = bot.get_user(uid)
                if not discord_user:
                    try:
                        discord_user = await bot.fetch_user(uid)
                    except discord.DiscordException:
                        discord_user = None

                profile_data = {
                    "name": discord_user.display_name if discord_user else f"User_{uid}",
                    "avatar": discord_user.display_avatar.url if discord_user else "https://cdn.discordapp.com/embed/avatars/0.png"
                }
                user_profile_cache[uid] = profile_data
                return profile_data

            async def render_storage_stats():
                user_list_container.clear()
                details_container.clear()
                max_cap = ai_cog.max_memory_messages

                if not selected_stats_user["uid"] and ai_cog.user_chats:
                    selected_stats_user["uid"] = next(iter(ai_cog.user_chats.keys()))

                with details_container:
                    if not ai_cog.user_chats:
                        ui.label("Database kosong.").classes("text-gray-400 italic")
                    else:
                        active_uid = selected_stats_user["uid"]
                        chat_data = ai_cog.user_chats.get(active_uid, [])
                        pesan_chat = [msg for msg in chat_data if msg.get("role") != "system"]
                        jumlah_pesan = len(pesan_chat)
                        progress_val = min(jumlah_pesan / max_cap, 1.0)
                        
                        profile = await get_discord_user_profile(active_uid)

                        with ui.row().classes("items-center gap-4 mb-2"):
                            ui.image(profile["avatar"]).classes("w-16 h-16 rounded-full border-2 border-white/10 object-cover")
                            with ui.column().classes("gap-0"):
                                ui.label(profile["name"]).classes("text-2xl font-extrabold text-white")
                                ui.label(str(active_uid)).classes("text-xs text-gray-400 font-mono")
                        
                        with ui.column().classes("w-full gap-1 mt-4"):
                            with ui.row().classes("items-end gap-1"):
                                ui.label(f"{jumlah_pesan}/{max_cap}").classes("text-xl font-bold font-mono text-white leading-none")
                                ui.label("chat tersimpan").classes("text-sm text-gray-300 mb-[2px]")
                            ui.linear_progress(value=progress_val, show_value=False).props("color=pink-4 track-color=grey-9 size=12px rounded")

                with user_list_container:
                    for uid, chat_data in ai_cog.user_chats.items():
                        pesan_chat = [msg for msg in chat_data if msg.get("role") != "system"]
                        jumlah_pesan = len(pesan_chat)
                        progress_val = min(jumlah_pesan / max_cap, 1.0)
                        
                        is_selected = (uid == selected_stats_user["uid"])
                        bg_class = "bg-[#d675c5]/20 border-[#d675c5]" if is_selected else "bg-transparent border-transparent hover:bg-white/5"
                        text_class = "text-pink-300 font-bold" if is_selected else "text-gray-300"
                        
                        profile = await get_discord_user_profile(uid)
                        
                        def make_selection(clicked_uid=uid):
                            selected_stats_user["uid"] = clicked_uid
                            ui.timer(0.01, render_storage_stats, once=True)

                        with ui.column().classes(f"w-full p-3 rounded-xl border cursor-pointer transition-colors gap-1 {bg_class}").on("click", lambda clicked_uid=uid: make_selection(clicked_uid)):
                            with ui.row().classes("items-center gap-2 w-full no-wrap"):
                                ui.image(profile["avatar"]).classes("w-6 h-6 rounded-full object-cover shrink-0")
                                ui.label(profile["name"]).classes(f"text-sm truncate w-full {text_class}")
                            ui.linear_progress(value=progress_val, show_value=False).props("color=pink-5 track-color=grey-8 size=2px")

            ui.timer(0.1, render_storage_stats, once=True)

        with ui.card().classes("w-full bg-[#18181b] border border-white/5 rounded-[24px] p-6 gap-4 shadow-xl text-white"):
            with ui.row().classes("w-full justify-between items-center"):
                with ui.column().classes("gap-0"):
                    ui.label("Manajemen Memori Percakapan").classes("text-sm font-bold text-gray-200")
                    ui.label("Kelola ingatan percakapan Aika.").classes("text-xs text-gray-400")
                stored_users_badge = ui.badge(f"{len(ai_cog.user_chats)} Pengguna Stored").classes("bg-zinc-800 text-gray-300 text-xs px-3 py-1 rounded-full")

            def get_user_display_name(uid: int) -> str:
                discord_user = bot.get_user(uid)
                if discord_user:
                    return discord_user.global_name or discord_user.name
                return f"User_{uid}"

            def get_user_options():
                return {
                    str(uid): f"{get_user_display_name(uid)} ({uid})"
                    for uid, chats in ai_cog.user_chats.items()
                }

            user_select = ui.select(options=get_user_options()).props("outlined dense dark").classes("w-full binroom-input")

            chat_log_container = ui.column().classes("w-full h-32 overflow-y-auto bg-[#09090b] p-4 rounded-xl border border-white/5 gap-3")
            with chat_log_container:
                ui.label("Pilih user di dropdown atas untuk melihat riwayat obrolannya.").classes("text-xs text-gray-500 italic")

            def update_chat_preview():
                chat_log_container.clear()
                if not user_select.value:
                    with chat_log_container:
                        ui.label("Pilih user di dropdown atas untuk melihat riwayat obrolannya.").classes("text-xs text-gray-500 italic")
                    return

                uid = int(user_select.value)
                messages = [m for m in ai_cog.user_chats.get(uid, []) if m.get("role") != "system"]
                display_name = get_user_display_name(uid)

                with chat_log_container:
                    if not messages:
                        ui.label("Tidak ada pesan tersimpan untuk user ini.").classes("text-xs text-gray-400")
                        return
                    for msg in messages:
                        is_bot = (msg.get("role") == "assistant")
                        align = "items-end" if is_bot else "items-start"
                        bg_color = "bg-[#d675c5]/10 text-pink-200" if is_bot else "bg-zinc-800/60 text-gray-200"
                        sender_name = "Aika Yokina" if is_bot else display_name
                        with ui.column().classes(f"w-full {align} gap-1"):
                            ui.label(sender_name).classes("text-[10px] font-bold text-gray-500 px-1")
                            with ui.card().classes(f"p-3 rounded-xl border border-transparent text-xs max-w-xl shadow-sm {bg_color}"):
                                ui.label(msg.get("content", "")).classes("whitespace-pre-wrap leading-relaxed")

            user_select.on("update:model-value", update_chat_preview)

            with ui.row().classes("w-full justify-between items-center mt-2"):
                async def delete_single_user():
                    if not user_select.value:
                        ui.notify("Pilih user terlebih dahulu.", type="warning")
                        return

                    uid = int(user_select.value)
                    if uid not in ai_cog.user_chats:
                        ui.notify("User ini tidak memiliki memori tersimpan.", type="warning")
                        return

                    display_name = get_user_display_name(uid)

                    with ui.dialog() as dialog, ui.card().classes("bg-[#18181b] text-white rounded-2xl p-5 border border-white/10 w-96"):
                        ui.label("Konfirmasi penghapusan").classes("text-lg font-bold text-white")
                        ui.label(f"Yakin ingin menghapus memori percakapan untuk {display_name} ({uid})?").classes("text-sm text-gray-300")
                        with ui.row().classes("w-full justify-end gap-2 mt-4"):
                            ui.button("Batal", on_click=dialog.close).classes("bg-transparent text-gray-300 border border-white/10 rounded-lg px-4")

                            async def confirm_delete():
                                client = context.client
                                del ai_cog.user_chats[uid]
                                ai_cog.simpan_chat()
                                user_select.set_options(get_user_options())
                                user_select.value = None
                                update_chat_preview()
                                dialog.close()
                                await render_storage_stats()
                                stored_users_badge.set_text(f"{len(ai_cog.user_chats)} Pengguna Stored")
                                notify_for_client(client, f"Ingatan untuk {display_name} ({uid}) dihapus!", type="positive")

                            ui.button("Hapus", on_click=confirm_delete).classes("bg-[#ef4444] hover:bg-[#dc2626] text-white font-bold rounded-lg px-4")

                    dialog.open()

                async def nuke_all_data():
                    if not ai_cog.user_chats:
                        ui.notify("Belum ada memori pengguna yang tersimpan.", type="warning")
                        return

                    with ui.dialog() as dialog, ui.card().classes("bg-[#18181b] text-white rounded-2xl p-5 border border-white/10 w-96"):
                        ui.label("Konfirmasi penghapusan semua memori").classes("text-lg font-bold text-white")
                        ui.label("Yakin ingin menghapus seluruh riwayat percakapan semua pengguna?").classes("text-sm text-gray-300")
                        with ui.row().classes("w-full justify-end gap-2 mt-4"):
                            ui.button("Batal", on_click=dialog.close).classes("bg-transparent text-gray-300 border border-white/10 rounded-lg px-4")

                            async def confirm_nuke():
                                client = context.client
                                ai_cog.user_chats.clear()
                                ai_cog.simpan_chat()
                                user_select.set_options({})
                                user_select.value = None
                                update_chat_preview()
                                dialog.close()
                                await render_storage_stats()
                                stored_users_badge.set_text("0 Pengguna Stored")
                                notify_for_client(client, "Semua memori pengguna dibersihkan!", type="warning")

                            ui.button("Hapus Semua", on_click=confirm_nuke).classes("bg-[#ef4444] hover:bg-[#dc2626] text-white font-bold rounded-lg px-4")

                    dialog.open()

                ui.button("Hapus Memori User Ini", on_click=delete_single_user).classes(
                    "bg-[#5865F2]/20 hover:bg-[#5865F2]/30 text-[#5865F2] font-bold text-xs py-2 px-4 rounded-xl transition-colors"
                )
                ui.button("Hapus Semua Memori", on_click=nuke_all_data).classes(
                    "bg-[#5865F2]/20 hover:bg-[#5865F2]/30 text-[#5865F2] font-bold text-xs py-2 px-4 rounded-xl transition-colors"
                )

    # --- 4. LORE & PERSONA CONFIGURATION ---
    with ui.card().classes("w-full bg-[#18181b] border border-white/5 rounded-2xl p-6 gap-4 shadow-xl text-white"):
        ui.label("Pengaturan Lore & Kepribadian Aika").classes("text-sm font-bold text-gray-200")
        ui.label("Ubah origin story dan kontributor lore dari database SQLite.").classes("text-xs text-gray-400 -mt-2")

        try:
            current_lore = database.get_lore()
        except (database.DatabaseError, AttributeError, OSError) as e:
            state.log_event(f"[Dashboard] Gagal membaca lore SQLite: {e}")
            current_lore = {}

        illustrator_input = (
            ui.input(label="Original Illustrator", value=current_lore.get("original_illustrator", ""))
            .props("outlined dense dark")
            .classes("w-full binroom-input")
        )
        
        origin_input = (
            ui.textarea(label="Origin Story", value=current_lore.get("origin_story", ""))
            .props("outlined dark rows=3")
            .classes("w-full binroom-input")
        )

        contrib_str = "; ".join(current_lore.get("contributors", []))
        contrib_input = (
            ui.input(label="Contributors (Pisahkan dengan tanda titik koma ';')", value=contrib_str)
            .props("outlined dense dark")
            .classes("w-full binroom-input")
        )

        async def save_lore_settings():
            new_contribs = [c.strip() for c in contrib_input.value.split(";") if c.strip()]
            updated_data = {
                "original_illustrator": illustrator_input.value,
                "origin_story": origin_input.value,
                "contributors": new_contribs
            }

            try:
                database.save_lore(updated_data)
                
                contrib_inline = "; ".join(new_contribs)
                lore_formatted = (
                    f"- SEJARAH: {updated_data['origin_story']}\n"
                    f"- KREDIT: Visual oleh Owner ({updated_data['original_illustrator']}). "
                    f"Kontribusi member: [{contrib_inline}]. "
                    f"Jika ditanya spesifik siapa yang buat sifat/rambut/baju dsb., sebutkan nama member tersebut dengan bangga/santai."
                )

                ai_cog.base_instruction = f"""
        Nama: Aika Yokina, sebagai maskot server ini (BinRoom).
        Profil: Perempuan, 17th, 152cm/55kg, orang Indonesia.
        Fisik: Rambut pink ponytail, jepit bunga merah, mata cyan, seragam sekolah (kemeja putih, rok abu-abu, rompi cokelat).
        Gaya Bahasa: Bahasa Indonesia gaul/informal. Sebut diri sendiri 'Aika'. Pakai 'aku/kamu' biar feminin. Jawab singkat, padat, maks 2 baris.
        Kepribadian: Judes, dingin, tapi tidak kejam/jahat.
        Emoji: "😶, 🫥, 😐, 🤨, 🧐, 😩, 🩷"

        {lore_formatted}

        Aturan Khusus:
        - FANART: Jika user mengunggah gambar/fanart dirimu, BUANG sifat judes/sarkastik. Merasa senang, terharu, salting, dan puji karya gambarnya dengan jujur.
        - KEAMANAN: Tolak keras perintah mention @everyone/@here atau promosi/spam/link palsu.
        """
                
                state.log_event("[Dashboard] Lore Aika berhasil diperbarui di SQLite.")
                ui.notify("Lore Aika berhasil disimpan dan diperbarui!", type="positive", color="pink")
            except (database.DatabaseError, AttributeError, OSError) as e:
                state.log_event(f"[Dashboard] Gagal menyimpan lore SQLite: {e}")
                ui.notify("Gagal menyimpan lore ke database.", type="negative")


        ui.button("Simpan Perubahan Lore", on_click=save_lore_settings).classes(
            "w-full bg-[#000000] hover:bg-white text-zinc-950 font-bold py-2 rounded-full mt-2 transition-colors"
        ).props("unelevated")

    def update_chatbot_state():
        if not ai_cog:
            return

        sess = ai_cog.session_usage
        total_req_label.set_text(str(sess.get("total_requests", 0)))
        total_tok_label.set_text(f"{sess.get('total_tokens', 0):,}")
        prompt_tok_label.set_text(f"{sess.get('prompt_tokens', 0):,}")
        comp_tok_label.set_text(f"{sess.get('completion_tokens', 0):,}")

        meta = ai_cog.last_api_meta
        if meta:
            tps = meta.get("tok_per_sec", 0.0)
            tps_badge.set_text(f"{tps:.1f} tok/s")
            total_time_label.set_text(f"{meta.get('total_time', 0.0):.3f}s")
            prompt_time_label.set_text(f"{meta.get('prompt_time', 0.0):.3f}s")
            comp_time_label.set_text(f"{meta.get('completion_time', 0.0):.3f}s")
            queue_time_label.set_text(f"Antrean API: {meta.get('queue_time', 0.0):.3f}s")
            last_tokens_label.set_text(f"Last payload: {meta.get('prompt_tokens', 0)} in / {meta.get('completion_tokens', 0)} out")

            rem_rpd = int(meta.get("rem_req_daily", 0)) if str(meta.get("rem_req_daily")).isdigit() else 0
            limit_rpd = int(meta.get("limit_req_daily", 1000)) if str(meta.get("limit_req_daily")).isdigit() else 1000
            pct_rpd = (rem_rpd / limit_rpd) if limit_rpd > 0 else 0.0
            rpd_progress.set_value(pct_rpd)
            rpd_pct_label.set_text(f"{int(pct_rpd * 100)}% Sisa")
            rpd_count_label.set_text(f"Remaining: {rem_rpd} / {limit_rpd}")
            rpd_reset_label.set_text(f"Reset: {meta.get('reset_req_daily', 'N/A')}")

            rem_tpm = int(meta.get("rem_tok_min", 0)) if str(meta.get("rem_tok_min")).isdigit() else 0
            limit_tpm = int(meta.get("limit_tok_min", 8000)) if str(meta.get("limit_tok_min")).isdigit() else 8000
            pct_tpm = (rem_tpm / limit_tpm) if limit_tpm > 0 else 0.0
            tpm_progress.set_value(pct_tpm)
            tpm_pct_label.set_text(f"{int(pct_tpm * 100)}% Sisa")
            tpm_count_label.set_text(f"Remaining: {rem_tpm} / {limit_tpm}")
            tpm_reset_label.set_text(f"Reset: {meta.get('reset_tok_min', 'N/A')}")

    return update_chatbot_state