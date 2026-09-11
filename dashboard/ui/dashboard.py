import discord
from fastapi import Request
from nicegui import ui

from dashboard.auth import get_user_admin_role, is_authenticated_admin

from . import state
from .views.chatbot import render_chatbot_tab
from .views.forbidden import render_403_page
from .views.info_server import render_info_server_tab
from .views.leaderboard import render_leaderboard_tab
from .views.overview import render_overview_tab

current_tab = "overview"
current_update_func = None  # Receives callback from active view renderer


def setup_dashboard(bot: discord.Client):
    """Registers the dashboard UI page onto NiceGUI."""

    @ui.page("/")
    def dashboard(request: Request):
        if not request.session.get("user_id"):
            ui.navigate.to("/login")
            return

        if not is_authenticated_admin(request, bot):
            with ui.column().classes("w-full h-screen items-center justify-center bg-[#0d0d0e] text-white gap-4"):
                render_403_page(request)
            return
        
        # Retrieve authenticated user details from session & bot instance
        user_id = request.session.get("user_id")
        username = request.session.get("username", "Admin")
        avatar_url = request.session.get("avatar_url", "https://cdn.discordapp.com/embed/avatars/0.png")
        role_name, role_color = get_user_admin_role(bot, user_id)

        ui.dark_mode().enable()
        ui.add_head_html('<link rel="stylesheet" href="/static/style.css">')
        ui.add_head_html('<link href="https://fonts.googleapis.com/icon?family=Material+Icons" rel="stylesheet">')

        def render_tab_content():
            nonlocal bot
            global current_update_func
            
            if current_tab == "overview":
                current_update_func = render_overview_tab(bot)
            elif current_tab == "info_server":
                current_update_func = render_info_server_tab()
            elif current_tab == "chatbot":
                current_update_func = render_chatbot_tab(bot)
            elif current_tab == "leaderboard":
                current_update_func = render_leaderboard_tab(bot)

        def select_tab(tab_id):
            global current_tab, current_update_func
            current_tab = tab_id
            current_update_func = None
            
            main_content.clear()
            with main_content:
                render_tab_content()
                
            sidebar_menu.refresh()

        @ui.refreshable
        def sidebar_menu():
            """Generates the sidebar items and recalculates active tab."""
            nav_items = [
                ("overview", "grid_view", "Overview", "Status & console"),
                ("info_server", "article", "Info Server", "WIP"),
                ("chatbot", "auto_awesome", "Aika AI Chatbot", "Cek status API & kelola chat"),
                ("leaderboard", "emoji_events", "Leaderboard GD", "Kelola leaderboard GD BinRoom"),
            ]

            for tab_id, icon_name, title, subtitle in nav_items:
                is_active = (current_tab == tab_id)
                btn_bg = "bg-[#d675c5] text-zinc-950" if is_active else "bg-transparent text-gray-400 hover:bg-white/5 hover:text-white"
                
                with ui.row().classes(f"w-full items-center gap-3 p-3 rounded-2xl cursor-pointer transition-colors {btn_bg}") \
                        .on("click", lambda t=tab_id: select_tab(t)):
                    ui.icon(icon_name, size="sm")
                    with ui.column().classes("gap-0"):
                        ui.label(title).classes("text-sm font-bold leading-tight")
                        ui.label(subtitle).classes("text-xs opacity-70 leading-tight")

        # -------------------------------------------------------------
        # LEFT NAVIGATION SIDEBAR
        # -------------------------------------------------------------
        with ui.left_drawer(value=True).classes("bg-[#121214] text-white border-r border-white/5 p-4 flex flex-col justify-between w-64"):
            with ui.column().classes("w-full gap-6"):
                # Header Logo
                with ui.row().classes("items-center gap-3 px-4"):
                    ui.avatar(icon="smart_toy", color="pink-3", text_color="grey-10").classes("shadow-md")
                    with ui.column().classes("gap-0"):
                        ui.label("Aika Yokina#2556").classes("text-sm font-black text-white")
                        ui.label("Aika Dashboard").classes("text-xs text-gray-400 font-medium")

                # Navigation Buttons Container
                with ui.column().classes("w-full gap-2 mt-2"):
                    sidebar_menu()

            # -------------------------------------------------------------
            # USER PROFILE & FOOTER SECTION
            # -------------------------------------------------------------
            with ui.column().classes("w-full gap-3 pt-4"):
                # Profile Info (Avatar, Username, Role Pill)
                with ui.row().classes("items-center gap-3 w-full px-1"):
                    with ui.avatar(size="md").classes("ring-2 ring-white/10 shadow-lg overflow-hidden"):
                        ui.image(avatar_url).classes("w-full h-full object-cover")
                    with ui.column().classes("gap-1.5 overflow-hidden flex-1"):
                        ui.label(username).classes("text-base font-extrabold text-white truncate leading-none")
                        
                        # Dynamic Role Pill Badge
                        with ui.row().classes("items-center gap-1.5 px-2.5 py-0.5 rounded-full border text-xs font-semibold max-w-fit") \
                                .style(f"border-color: {role_color}; color: {role_color}; background-color: {role_color}15"):
                            ui.element("div").classes("w-2 h-2 rounded-full").style(f"background-color: {role_color}")
                            ui.label(role_name).classes("leading-tight")

                # Logout Button
                ui.button("LOGOUT", color="red", on_click=lambda: ui.navigate.to("/logout")) \
                    .classes("w-full bg-[#df5b61] hover:bg-[#cf4b51] text-white font-bold text-xs py-2.5 rounded-2xl shadow-md transition-all uppercase tracking-wider")

                ui.separator().classes("bg-white/5 my-1")

                # Bottom Status Footer
                with ui.row().classes("items-center gap-2 px-2 py-1 text-xs text-gray-400 font-mono"):
                    ui.icon("circle", size="xs").classes("text-emerald-400")
                    footer_status = ui.label(f"Bot Online • {state.latency_ms}ms")

        # -------------------------------------------------------------
        # MAIN CONTENT AREA
        # -------------------------------------------------------------
        main_content = ui.column().classes("w-full max-w-[1200px] mx-auto p-8 gap-6 bg-[#0d0d0e]")
        
        with main_content:
            render_tab_content()

        # -------------------------------------------------------------
        # REALTIME REFRESH LOOP
        # -------------------------------------------------------------
        def refresh_ui():
            footer_status.set_text(f"Bot Online • {state.latency_ms}ms")
            if current_update_func:
                current_update_func()

        ui.timer(1.0, refresh_ui)