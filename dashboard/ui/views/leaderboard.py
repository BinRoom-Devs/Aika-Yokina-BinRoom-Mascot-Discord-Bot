import asyncio

import aiohttp
import discord
from nicegui import ui
from nicegui.context import context

from ..utils import notify_for_client


def render_leaderboard_tab(bot: discord.Client):
    try:
        from cogs.gd_leaderboard import (
            GDPlayer,
            cari_profil_gd,
            load_daftar_player,
            normalize_gd_category_name,
            prepare_gd_leaderboard_rows,
            simpan_daftar_player,
        )
    except ImportError as exc:
        ui.label("Leaderboard GD").classes("text-3xl font-extrabold text-white tracking-tight")
        with ui.card().classes("w-full bg-[#18181b] border border-white/5 rounded-2xl p-6 text-rose-300"):
            ui.label(f"Gagal memuat leaderboard GD: {exc}").classes("text-sm")
        return

    leaderboard_cog = bot.get_cog("BinrumLeaderboard")

    category_icons = {
        "stars": "https://cdn.discordapp.com/attachments/863959650448703538/1544331594301710356/GJ_bigStar_noShadow_001.png?ex=6a98c720&is=6a9775a0&hm=204cc1166e6f331185424efffcca4b485d5a1bad4d14c80299f6ed78d3dbe310&",
        "moons": "https://cdn.discordapp.com/attachments/863959650448703538/1544331593949118525/GJ_bigMoon_noShadow_001.png?ex=6a98c720&is=6a9775a0&hm=84afa398bd85bf216c6d4c0ec3103195bfe1eebefcfc07a2483df78fd7a2d563&",
        "demons": "https://cdn.discordapp.com/attachments/863959650448703538/1544331593529954425/diffIcon_06_btn_001.png?ex=6a98c720&is=6a9775a0&hm=61f3ab0481ddbcbbcbd74185109c7d8871bb553abad278dd4440b996e2c13460&",
        "secret coins": "https://cdn.discordapp.com/attachments/863959650448703538/1544331595002150912/secretCoinUI_001.png?ex=6a98c720&is=6a9775a0&hm=af6d5e31cc0f74b7057df7af4791045e2f8861e1ad5767decd38e594e1c5aae6&",
        "user coins": "https://cdn.discordapp.com/attachments/863959650448703538/1544331595366797482/secretCoinUI2_001.png?ex=6a98c720&is=6a9775a0&hm=a62008640808f5e665a616278e2408731ced53328591c89dc0bdc0c0b5ce61fb&",
        "diamonds": "https://cdn.discordapp.com/attachments/863959650448703538/1544343625008291910/GJ_bigDiamond_noShadow_001.png?ex=6a982994&is=6a96d814&hm=1292275544f326d2aa3ff4c2d75be1ae7b63d61d3823aeeed86de47a3d4b6d23&",
        "creator points": "https://cdn.discordapp.com/attachments/863959650448703538/1544331594645504121/GJ_hammerIcon_001.png?ex=6a98c720&is=6a9775a0&hm=830cdc28a372776465a6573fb307343afb17300debac4816f51bd8a63d7928b6&",
    }

    category_colors = {
        "stars": "#f8e062",
        "moons": "#70d8ff",
        "demons": "#ff4d6d",
        "secret coins": "#f7b500",
        "user coins": "#d5d5d5",
        "diamonds": "#4ad7ff",
        "creator points": "#f0f0f0",
    }

    page_size = 20
    page_index = {"value": 0}
    selected_category = {"value": "stars"}
    avatar_url_cache = {}

    def format_stat(value):
        try:
            return f"{int(value):,}"
        except (TypeError, ValueError):
            return str(value or 0)

    async def get_discord_avatar_url(discord_id):
        if not discord_id:
            return "https://cdn.discordapp.com/embed/avatars/0.png"
        try:
            user_id = int(discord_id)
        except (TypeError, ValueError):
            return "https://cdn.discordapp.com/embed/avatars/0.png"

        if user_id in avatar_url_cache:
            return avatar_url_cache[user_id]

        user = bot.get_user(user_id)
        if user:
            avatar_url = user.display_avatar.url if user.display_avatar else "https://cdn.discordapp.com/embed/avatars/0.png"
            avatar_url_cache[user_id] = avatar_url
            return avatar_url

        try:
            user = await asyncio.wait_for(bot.fetch_user(user_id), timeout=4)
            avatar_url = user.display_avatar.url if user.display_avatar else "https://cdn.discordapp.com/embed/avatars/0.png"
        except (discord.DiscordException, asyncio.TimeoutError):
            avatar_url = "https://cdn.discordapp.com/embed/avatars/0.png"

        avatar_url_cache[user_id] = avatar_url
        return avatar_url

    async def open_delete_player_dialog(player_data):
        name = player_data.get("nama_user_gd", "Player")
        account_id = player_data.get("account_id_gd", 0)
        with ui.dialog() as dialog, ui.card().classes("w-full max-w-md bg-[#18181b] border border-red-500/20 rounded-2xl p-5 text-white"):
            ui.label("Konfirmasi penghapusan").classes("text-lg font-bold text-white")
            with ui.row().classes("items-center gap-3 mt-2"):
                ui.image(f"https://gdicon.oat.zone/icon.png?type=cube&value={player_data.get('icon', 1)}&color1={player_data.get('col1', 0)}&color2={player_data.get('col2', 0)}{('&glow=1' if player_data.get('glow') else '')}").classes("w-12 h-12 rounded-lg object-cover")
                ui.label(f"Yakin ingin menghapus {name} dari leaderboard?").classes("text-sm text-gray-200")

            with ui.row().classes("w-full justify-end gap-2 mt-4"):
                ui.button("Batal", on_click=dialog.close).classes("bg-transparent text-gray-300 border border-white/10 rounded-lg px-4")

                async def confirm_delete():
                    client = context.client
                    daftar_player = load_daftar_player()
                    filtered = [
                        p for p in daftar_player
                        if not (
                            p.get("account_id_gd") == account_id
                            or p.get("nama_user_gd", "").lower() == name.lower()
                        )
                    ]
                    simpan_daftar_player(filtered)
                    dialog.close()
                    await render_leaderboard_rows()
                    notify_for_client(client, f"{name} berhasil dihapus dari leaderboard.", type="positive")

                ui.button("Hapus", on_click=confirm_delete).classes("bg-red-600 hover:bg-red-500 text-white font-bold rounded-lg px-4")

        dialog.open()

    async def open_add_player_dialog():
        with ui.dialog() as dialog, ui.card().classes("w-full max-w-lg bg-[#18181b] border border-white/10 rounded-2xl p-5 text-white"):
            ui.label("Tambah player ke leaderboard").classes("text-lg font-bold text-white")
            username_input = ui.input(label="Username GD", placeholder="Contoh: TheHx").props("outlined dense dark").classes("w-full binroom-input")
            status_label = ui.label("Masukkan username GD untuk mengecek validitas akun.").classes("text-xs text-gray-400")
            preview_container = ui.column().classes("w-full gap-3")

            async def validate_and_preview():
                username = (username_input.value or "").strip()
                if not username:
                    status_label.set_text("Username GD tidak boleh kosong.")
                    preview_container.clear()
                    return

                async with aiohttp.ClientSession() as session:
                    result = await cari_profil_gd(session, username)

                if not result:
                    status_label.set_text(f"Username GD '{username}' tidak ditemukan.")
                    preview_container.clear()
                    return

                account_id, player_id, real_name = result
                profile_data = {}
                try:
                    timeout = aiohttp.ClientTimeout(total=8)
                    async with aiohttp.ClientSession() as session, session.get(
                        f"https://gdbrowser.com/api/profile/{account_id}",
                        ssl=False,
                        timeout=timeout,
                    ) as response:
                        if response.status == 200:
                            data = await response.json()
                            if isinstance(data, dict):
                                profile_data = data
                except (aiohttp.ClientError, asyncio.TimeoutError, ValueError):
                    profile_data = {}

                preview_data = {
                    "username": real_name,
                    "accountID": account_id,
                    "playerID": player_id,
                    "stars": 0, "moons": 0, "diamonds": 0,
                    "coins": 0, "userCoins": 0, "demons": 0, "cp": 0,
                    "icon": profile_data.get("icon", 1),
                    "col1": profile_data.get("col1", 0),
                    "col2": profile_data.get("col2", 0),
                    "glow": profile_data.get("glow", 0),
                }
                preview_player = GDPlayer(preview_data)
                icon_url = preview_player.get_icon_url()
                preview_container.clear()
                with preview_container, ui.row().classes("w-full items-center gap-4 no-wrap"):
                    ui.image(icon_url).classes("w-20 h-20 object-contain shrink-0 rounded-xl border border-white/10 bg-[#0d0d0e] p-1")
                    with ui.column().classes("min-w-0 gap-1"):
                        ui.label(real_name).classes("text-xl font-bold text-white truncate")
                        ui.label(f"Account ID: {account_id}").classes("text-xs text-gray-400 font-mono")
                        ui.label(f"Player ID: {player_id}").classes("text-xs text-gray-400 font-mono")

                status_label.set_text("Akun valid. Konfirmasi untuk menambahkan ke leaderboard.")

                with preview_container:
                    async def confirm_add_player():
                        client = context.client
                        daftar_player = load_daftar_player()
                        if any(
                            p.get("account_id_gd") == account_id or p.get("nama_user_gd", "").lower() == real_name.lower()
                            for p in daftar_player
                        ):
                            status_label.set_text("Player ini sudah ada di leaderboard.")
                            ui.notify("Player sudah terdaftar di leaderboard.", type="warning")
                            return

                        data_baru = {
                            "nama_user_gd": real_name,
                            "account_id_gd": account_id,
                            "player_id_gd": player_id,
                            "id_user_discord": None,
                            "statistik": {
                                "stars": 0, "moons": 0, "diamonds": 0,
                                "secret_coins": 0, "user_coins": 0, "demons": 0, "creator_points": 0,
                            },
                            "icon": preview_player.icon,
                            "col1": preview_player.color1,
                            "col2": preview_player.color2,
                            "glow": preview_player.glow,
                        }
                        daftar_player.append(data_baru)
                        simpan_daftar_player(daftar_player)
                        dialog.close()
                        await render_leaderboard_rows()
                        notify_for_client(client, f"{real_name} berhasil ditambahkan ke leaderboard.", type="positive")

                    ui.button("Tambahkan ke leaderboard", on_click=confirm_add_player).classes("w-full bg-pink-500 hover:bg-pink-400 text-zinc-950 font-bold py-2 rounded-xl")

            with ui.row().classes("w-full justify-end gap-2 mt-4"):
                ui.button("Batal", on_click=dialog.close).classes("bg-transparent text-gray-300 border border-white/10 rounded-lg px-4")
                ui.button("Cek Username", on_click=validate_and_preview).classes("bg-[#000000] hover:bg-white text-zinc-950 font-bold rounded-lg px-4")

        dialog.open()

    ui.label("BinRoom Geometry Dash Leaderboard Management Dashboard").classes("text-[2rem] font-extrabold text-white tracking-tight")

    with ui.card().classes("w-full bg-[#18181b] border border-white/5 rounded-[24px] p-6 gap-4 shadow-xl text-white"):
        with ui.row().classes("w-full justify-between items-center"):
            with ui.row().classes("items-center gap-3"):
                ui.button("Tambah player", icon="person_add", on_click=open_add_player_dialog).classes("bg-cyan-600 hover:bg-cyan-500 text-white font-bold text-sm px-4 py-2 rounded-xl")

                async def refresh_leaderboard_data():
                    if not leaderboard_cog:
                        ui.notify("Cog leaderboard belum dimuat.", type="negative")
                        return

                    refresh_button.disable()
                    refresh_button.set_text("Memuat...")
                    try:
                        updated_count, failed_count = await leaderboard_cog.refresh_data_only()
                        await render_leaderboard_rows()
                        ui.notify(
                            f"Data diperbarui: {updated_count} berhasil, {failed_count} gagal.",
                            type="positive" if failed_count == 0 else "warning",
                        )
                    except (discord.DiscordException, aiohttp.ClientError, asyncio.TimeoutError, OSError) as exc:
                        ui.notify(f"Gagal memperbarui data: {exc}", type="negative")
                    finally:
                        refresh_button.enable()
                        refresh_button.set_text("Refresh data")

                refresh_button = ui.button("Refresh data", on_click=refresh_leaderboard_data).props("icon=sync").classes("bg-cyan-600 hover:bg-cyan-500 text-white font-bold text-sm px-4 py-2 rounded-xl")

            with ui.row().classes("items-center gap-2"):
                search_input = ui.input(placeholder="Cari player...").props("outlined dense dark").classes("w-72 binroom-input")

                async def trigger_search():
                    page_index["value"] = 0
                    await render_leaderboard_rows()

                ui.button(icon="search", on_click=trigger_search).props("flat").classes("bg-zinc-800 hover:bg-zinc-700 text-white rounded-xl w-12 h-10 min-w-[44px] p-0")

        leaderboard_body = ui.column().classes("w-full gap-3 mt-3 overflow-x-auto")
        leaderboard_grid_columns = "56px minmax(200px, 2fr) repeat(7, minmax(78px, 1fr)) 48px"

        async def render_leaderboard_rows():
            leaderboard_body.clear()
            with leaderboard_body, ui.card().classes("w-full bg-[#18181b] border border-white/5 rounded-2xl p-8 gap-3 items-center text-white"):
                ui.spinner(size="2em", color="pink")
                ui.label("Memuat leaderboard...").classes("text-sm text-gray-300")

            category = normalize_gd_category_name(selected_category["value"] or "stars")
            rows = prepare_gd_leaderboard_rows(category)
            query = (search_input.value or "").strip().lower()
            if query:
                rows = [r for r in rows if query in r[0].username.lower()]
            page_count = max(1, (len(rows) + page_size - 1) // page_size)
            if page_index["value"] >= page_count:
                page_index["value"] = page_count - 1

            start_index = page_index["value"] * page_size
            end_index = start_index + page_size
            page_rows = rows[start_index:end_index]

            avatar_ids = [player_data.get("id_user_discord") for _, player_data in page_rows]
            unique_avatar_ids = list(dict.fromkeys(discord_id for discord_id in avatar_ids if discord_id))
            avatar_values = await asyncio.gather(*(get_discord_avatar_url(discord_id) for discord_id in unique_avatar_ids))
            avatar_urls = dict(zip(unique_avatar_ids, avatar_values))
            leaderboard_body.clear()

            async def go_to_page(target_page):
                page_index["value"] = target_page
                await render_leaderboard_rows()

            async def select_category(cat_key):
                selected_category["value"] = cat_key
                page_index["value"] = 0
                await render_leaderboard_rows()

            with leaderboard_body:
                header_items = [
                    ("RANK", None, None),
                    ("PLAYER", None, None),
                    ("STAR", category_icons["stars"], "stars"),
                    ("MOON", category_icons["moons"], "moons"),
                    ("DEMON", category_icons["demons"], "demons"),
                    ("SECRET", category_icons["secret coins"], "secret coins"),
                    ("USER", category_icons["user coins"], "user coins"),
                    ("DIAMOND", category_icons["diamonds"], "diamonds"),
                    ("CP", category_icons["creator points"], "creator points"),
                    ("", None, None),
                ]

                with ui.grid(columns=10).classes("w-full min-w-[1080px] gap-2 items-center bg-[#0d0d0e] border border-white/5 rounded-2xl p-3 text-[11px] font-bold uppercase tracking-wide text-gray-400").style(f"grid-template-columns: {leaderboard_grid_columns}"):
                    for label, icon_url, cat_key in header_items:
                        if cat_key:
                            is_active = (selected_category["value"] == cat_key)
                            accent = category_colors.get(cat_key, "#ffffff")
                            glow = f"text-shadow: 0 0 10px {accent}44;" if is_active else ""
                            active_classes = "text-white bg-white/10 border border-white/10 rounded-lg px-2 py-1" if is_active else "hover:text-white cursor-pointer transition-colors px-2 py-1"
                            category_width = "w-auto" if cat_key == "creator points" else "w-full"
                            
                            with ui.row().classes(f"items-center justify-end gap-1.5 {category_width} {active_classes}").on("click", lambda ck=cat_key: select_category(ck)):
                                if icon_url:
                                    ui.image(icon_url).classes("w-4 h-4 object-contain")
                                lbl = ui.label(label).classes("whitespace-nowrap")
                                if is_active:
                                    lbl.style(f"color: {accent}; {glow}")
                        else:
                            with ui.row().classes("items-center justify-center gap-2 w-full"):
                                if icon_url:
                                    ui.image(icon_url).classes("w-4 h-4 object-contain")
                                ui.label(label if label else "").classes("whitespace-nowrap")

                for offset, (player, player_data) in enumerate(page_rows, start=start_index):
                    rank = offset + 1
                    discord_avatar_url = avatar_urls.get(player_data.get("id_user_discord"), "https://cdn.discordapp.com/embed/avatars/0.png")
                    gd_icon_url = player.get_icon_url()
                    with ui.grid(columns=10).classes("w-full min-w-[1080px] gap-2 items-center bg-[#111114] border border-white/5 rounded-2xl p-3 text-sm text-gray-200").style(f"grid-template-columns: {leaderboard_grid_columns}"):
                        ui.label(f"#{rank}").classes("font-bold font-mono text-pink-300 px-1 text-left")
                        
                        with ui.row().classes("items-center gap-2 no-wrap min-w-0 w-full"):
                            ui.image(gd_icon_url).classes("w-10 h-10 object-contain rounded-md bg-[#0d0d0e] p-1 shrink-0")
                            with ui.row().classes("items-center gap-2 no-wrap min-w-0 flex-1"):
                                ui.image(discord_avatar_url).classes("w-10 h-10 rounded-full object-cover border border-white/10 shrink-0")
                                ui.label(player.username).classes("font-semibold text-white truncate min-w-0 whitespace-nowrap")

                        stat_map = {
                            "stars": getattr(player, "stars", 0),
                            "moons": player.moons,
                            "demons": player.demons,
                            "secret coins": player.secretCoins,
                            "user coins": player.userCoins,
                            "diamonds": player.diamonds,
                            "creator points": player.creatorPoints,
                        }

                        for key, label in [
                            ("stars", format_stat(stat_map["stars"])),
                            ("moons", format_stat(stat_map["moons"])),
                            ("demons", format_stat(stat_map["demons"])),
                            ("secret coins", format_stat(stat_map["secret coins"])),
                            ("user coins", format_stat(stat_map["user coins"])),
                            ("diamonds", format_stat(stat_map["diamonds"])),
                            ("creator points", format_stat(stat_map["creator points"])),
                        ]:
                            is_highlighted = key == category
                            accent = category_colors.get(key, "#ffffff")
                            value_classes = "font-mono text-right w-full px-1 " + ("text-gray-200" if not is_highlighted else "")
                            value_style = f"color: {accent}; text-shadow: 0 0 12px {accent}55;" if is_highlighted else ""
                            ui.label(label).classes(value_classes).style(value_style)

                        ui.button(icon="delete", on_click=lambda p=player_data: open_delete_player_dialog(p)).props("flat").classes("bg-red-600 hover:bg-red-500 text-white rounded-lg min-w-[32px] w-[32px] h-[32px] p-0 justify-self-end")

                with ui.row().classes("w-full justify-center items-center gap-2 mt-3 flex-wrap"):
                    for target_page in range(page_count):
                        page_button = ui.button(
                            str(target_page + 1),
                            on_click=lambda target_page=target_page: go_to_page(target_page),
                        ).props("flat dense")
                        page_button.classes(
                            "bg-pink-500 text-zinc-950 font-bold" if target_page == page_index["value"]
                            else "bg-zinc-800 text-gray-200"
                        )

                if not rows:
                    with leaderboard_body:
                        ui.label("Belum ada data player untuk kategori ini.").classes("text-sm text-gray-400 italic")

        async def on_search_change():
            page_index["value"] = 0
            await render_leaderboard_rows()

        search_input.on("update:model-value", on_search_change)
        ui.timer(0.01, render_leaderboard_rows, once=True)

    return  # No real-time ticker callback needed