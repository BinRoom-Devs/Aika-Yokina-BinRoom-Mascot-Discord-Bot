import discord
from nicegui import ui

from .. import state


def render_overview_tab(bot: discord.Client):
    ui.label("Overview").classes("text-3xl font-extrabold text-white tracking-tight mb-2")

    with ui.grid(columns=2).classes("w-full gap-6"):
        # 1. System Status Card
        with ui.card().classes("w-full bg-[#18181b] border border-white/5 rounded-2xl p-6 gap-6 shadow-xl text-white"):
            with ui.row().classes("w-full justify-between items-center"):
                ui.label("System Status").classes("text-sm font-bold text-gray-200")
                ui.badge("Realtime").classes("bg-zinc-800 text-gray-400 text-xs px-2 py-1 rounded-full")

            with ui.row().classes("items-center gap-4"):
                ui.avatar(icon="smart_toy", color="pink-3", text_color="grey-10").classes("w-12 h-12 shadow-lg")
                with ui.column().classes("gap-0"):
                    with ui.row().classes("items-center gap-2"):
                        ui.icon("circle", size="xs").classes("text-emerald-400")
                        bot_name_label = ui.label(state.bot_status_text).classes("text-base font-bold text-white")
                    ui.label("Connected to the Discord gateway").classes("text-xs text-gray-400")

            with ui.grid(columns=3).classes("w-full bg-[#0d0d0e] p-4 rounded-xl border border-white/5 text-center gap-2"):
                with ui.column().classes("items-center gap-0"):
                    ui.label("UPTIME").classes("text-[10px] font-bold text-gray-500 tracking-wider")
                    uptime_label = ui.label(state.get_uptime()).classes("text-lg font-bold text-white font-mono")
                with ui.column().classes("items-center gap-0"):
                    ui.label("GUILDS").classes("text-[10px] font-bold text-gray-500 tracking-wider")
                    guilds_label = ui.label(str(state.guild_count)).classes("text-lg font-bold text-white font-mono")
                with ui.column().classes("items-center gap-0"):
                    ui.label("LATENCY").classes("text-[10px] font-bold text-gray-500 tracking-wider")
                    ping_label = ui.label(f"{state.latency_ms}ms").classes("text-lg font-bold text-white font-mono")

        # 2. Presence Controls Card
        with ui.card().classes("w-full bg-[#18181b] border border-white/5 rounded-2xl p-6 gap-4 shadow-xl text-white"):
            ui.label("Presence Controls").classes("text-sm font-bold text-gray-200")
            ui.label("Atur status dan aktivitas Aika secara langsung.").classes("text-xs text-gray-400 -mt-2")

            ui.label("Status").classes("text-xs font-semibold text-gray-300 mt-1")
            status_dropdown = (
                ui.select(
                    options={
                        "online": "Online",
                        "idle": "Idle",
                        "dnd": "Do Not Disturb",
                        "invisible": "Invisible",
                    },
                    value=state.bot_presence_status,
                )
                .props("outlined dense dark")
                .classes("w-full binroom-input")
            )

            ui.label("Custom activity").classes("text-xs font-semibold text-gray-300 mt-1")
            activity_input = (
                ui.input(value=state.bot_activity)
                .props("outlined dense dark")
                .classes("w-full binroom-input")
            )

            async def update_presence():
                if bot.is_ready():
                    selected_status = getattr(discord.Status, status_dropdown.value, discord.Status.dnd)
                    act_text = activity_input.value or "nemenin BinRoom"
                    
                    state.bot_presence_status = status_dropdown.value
                    state.bot_activity = act_text
                    
                    await bot.change_presence(
                        status=selected_status,
                        activity=discord.CustomActivity(name=act_text),
                    )
                    state.log_event(f"[Admin UI] Presence updated: {status_dropdown.value} | {act_text}")
                    ui.notify("Status berhasil diperbarui!", type="positive", color="pink")

            ui.button("Perbarui Status", on_click=update_presence).classes(
                "w-full bg-[#000000] hover:bg-white text-zinc-950 font-bold py-2 rounded-full mt-2 transition-colors"
            ).props("unelevated")

    # 3. Terminal Console Card
    with ui.card().classes("w-full bg-[#18181b] border border-white/5 rounded-2xl p-4 gap-3 shadow-xl text-white mt-2"):
        with ui.row().classes("w-full justify-between items-center px-2"), ui.row().classes("items-center gap-2"):
            ui.element("div").classes("w-3 h-3 rounded-full bg-rose-500")
            ui.element("div").classes("w-3 h-3 rounded-full bg-amber-500")
            ui.element("div").classes("w-3 h-3 rounded-full bg-emerald-500")
            ui.label("aika@binroom — console").classes("text-xs font-mono text-gray-400 ml-2")

        log_area = ui.log(max_lines=50).classes(
            "w-full h-64 bg-[#09090b] text-gray-300 font-mono text-xs p-4 rounded-xl border border-white/5"
        )

    def update_overview_state():
        bot_name_label.set_text(state.bot_status_text)
        uptime_label.set_text(state.get_uptime())
        guilds_label.set_text(str(state.guild_count))
        ping_label.set_text(f"{state.latency_ms}ms")
        
        log_area.clear()
        for entry in state.latest_logs:
            log_area.push(entry)

    return update_overview_state