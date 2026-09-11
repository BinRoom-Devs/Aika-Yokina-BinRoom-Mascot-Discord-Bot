from nicegui import ui


def render_info_server_tab():
    ui.label("Info Server").classes("text-3xl font-extrabold text-white tracking-tight")
    with ui.card().classes("w-full bg-[#18181b] border border-white/5 rounded-2xl p-6 text-gray-300"):
        ui.label("Server channel configuration and information synchronization will appear here.").classes("text-sm")