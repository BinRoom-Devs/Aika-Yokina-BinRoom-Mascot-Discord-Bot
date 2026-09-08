from nicegui import app, ui
from fastapi import Request

MASCOT_URL = "media/aika_marah.png"
LOGO_URL = "media/binroom_logo_white.png"
app.add_static_files('/media', 'media')

def render_403_page(request: Request):
    username = request.session.get("username", "Unknown")
    avatar_url = request.session.get("avatar_url", "https://cdn.discordapp.com/embed/avatars/0.png")

    ui.dark_mode().enable()
    
    ui.add_head_html("""
        <style>
            @font-face {
                font-family: 'Unageo';
                src: url('/static/fonts/Unageo.woff2') format('woff2'),
                     url('/static/fonts/Unageo.ttf') format('truetype');
                font-weight: 100 900;
                font-style: normal;
                font-display: swap;
            }
            * { font-family: 'Unageo', sans-serif !important; }
            body, html {
                margin: 0 !important;
                padding: 0 !important;
                width: 100vw;
                min-height: 100vh;
                overflow-x: hidden !important; 
                overflow-y: auto !important; 
                background-color: #191919;
            }
            /* Neutralize NiceGUI/Quasar default page wrapper padding that causes edge gaps */
            .nicegui-content {
                padding: 0 !important;
                max-width: none !important;
            }
            .font-mono, .font-mono * {
                font-family: Consolas, Monaco, "Andale Mono", "Ubuntu Mono", monospace !important;
            }
        </style>
    """)

    # --- MAIN WRAPPER ---
    with ui.element('div').classes('relative w-screen min-h-screen bg-[#191919] overflow-x-hidden flex flex-col items-center justify-between m-0 p-0'):
        
        # --- CSS BACKGROUND FLOWERS & GRADIENT ---
        ui.image('/media/bunga_abu2.png').classes('absolute -left-[100px] top-[15%] w-[550px] h-[550px] pointer-events-none z-10 object-contain')
        ui.image('/media/bunga_abu2.png').classes('absolute -right-[100px] -top-[50px] w-[550px] h-[550px] pointer-events-none z-10 object-contain -scale-x-100')
        
        # Absolute bottom fixed gradient wrapper forcing 0 offset bounds
        ui.element('div').classes('absolute inset-x-0 bottom-0 w-full h-48 bg-gradient-to-t from-[#db3e43]/25 via-[#db3e43]/5 to-transparent pointer-events-none z-0')

        # --- HEADER ---
        with ui.row().classes('w-full max-w-[1100px] px-6 md:px-16 py-4 justify-between items-center z-20'):
            ui.image(LOGO_URL).classes('w-40 md:w-52')
            
            with ui.row().classes('items-center gap-3 md:gap-4'):
                with ui.column().classes('items-end gap-0 flex'):
                    ui.label(username).classes('text-white font-extrabold text-sm md:text-base leading-tight')
                    ui.label('(BUKAN ADMIN)').classes('text-[#db3e43] font-black text-[20px] md:text-xs tracking-wider')
                with ui.avatar(size="3.2rem").classes('ring-2 ring-white/20 shadow-xl overflow-hidden shrink-0'):
                    ui.image(avatar_url).classes('w-full h-full object-cover')

        # --- CENTER CONTENT CONTAINER ---
        with ui.column().classes('z-20 items-center justify-center max-w-[950px] w-full px-6 md:px-8 py-8 md:pb-12'):
            
            with ui.element('div').classes('flex flex-col md:flex-row w-full items-center justify-center gap-8 md:gap-14 mb-8 md:mb-[-30px] text-center md:text-left'):
                ui.image(MASCOT_URL).classes('w-[240px] md:w-[360px] drop-shadow-[0_25px_25px_rgba(0,0,0,0.6)]')
                
                with ui.column().classes('gap-0 items-center md:items-start'):
                    ui.label('403').classes('font-black tracking-tighter leading-none text-[6rem] md:text-[8rem]').style('color: #c469b8;')
                    ui.label('Nggak boleh.').classes('text-3xl md:text-4xl font-extrabold mb-2 md:mb-3').style('color: #c469b8;')
                    ui.label('Cuma admin yang boleh masuk\nke dashboard-nya Aika.').classes('text-white text-lg md:text-xl font-bold whitespace-pre-line leading-snug')

            ui.button('LOG OUT', on_click=lambda: ui.navigate.to('/logout')) \
                .classes('w-full py-4 rounded-full text-lg md:text-xl font-black text-white shadow-2xl transition-transform hover:scale-[1.01]') \
                .style('background-color: #db3e43 !important; letter-spacing: 2px;')

        # --- FOOTER ---
        ui.label("Art by Nekouci (2023), website by TheCoreProne using Python's NiceGUI").classes('pb-6 px-4 text-center text-white/30 text-[10px] md:text-xs font-medium z-10')