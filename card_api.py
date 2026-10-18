import base64
import html
import os
from pathlib import Path

import aiohttp
import discord
from fastapi import Response
from nicegui import app, ui

import config

# Bot data cache
bot_data = {
    "name": "Aika Yokina",
    "discriminator": "#2556",
    "avatar_b64": "",
    "banner_b64": "",
    "status_color": "#f23f43",
    "custom_status": "Main di BinRoom..."
}

DIREKTORI_UTAMA = Path(__file__).resolve().parent

async def fetch_image_as_base64(url: str) -> str:
    """Fetch image from URL and convert to base64."""
    if not url:
        return ""
    try:
        async with aiohttp.ClientSession() as session, session.get(url, timeout=5) as resp:
            if resp.status == 200:
                content_type = resp.headers.get("Content-Type", "image/png")
                data = await resp.read()
                encoded = base64.b64encode(data).decode("utf-8")
                return f"data:{content_type};base64,{encoded}"
    except Exception as e:  # noqa: BLE001
        print(f"[Card API] Failed to fetch image: {e}")
    return ""

def get_local_image_base64(file_path: str, mime_type: str = "image/png") -> str:
    """Load local image and convert to base64."""
    full_path = DIREKTORI_UTAMA / file_path
    if full_path.exists():
        try:
            with open(full_path, "rb") as image_file:
                encoded = base64.b64encode(image_file.read()).decode("utf-8")
                return f"data:{mime_type};base64,{encoded}"
        except Exception as e:  # noqa: BLE001
            print(f"[Card API] Failed to load local image: {e}")
    return ""

async def update_bot_data():
    """Update bot data from Discord API."""
    token = config.pengaturan.token_bot
    if not token:
        print("[Card API] No TOKEN_BOT found, using default values")
        # Load fallback images
        bot_data["avatar_b64"] = get_local_image_base64("media/aika_marah.png", "image/png")
        bot_data["banner_b64"] = get_local_image_base64("media/banner.png", "image/png")
        return
    
    try:
        intents = discord.Intents.default()
        intents.guilds = True
        client = discord.Client(intents=intents)
        await client.login(token)
        
        if client.user:
            bot_data["name"] = html.escape(client.user.name)
            bot_data["discriminator"] = html.escape(f"#{client.user.discriminator}") if client.user.discriminator != "0" else "#2556"
            
            # Fetch avatar
            avatar_url = client.user.display_avatar.with_size(128).url
            bot_data["avatar_b64"] = await fetch_image_as_base64(avatar_url)
            if not bot_data["avatar_b64"]:
                bot_data["avatar_b64"] = get_local_image_base64("media/aika_marah.png", "image/png")
            
            # Fetch banner
            banner_url = client.user.banner.with_size(512).url if getattr(client.user, "banner", None) else ""
            bot_data["banner_b64"] = await fetch_image_as_base64(banner_url)
            if not bot_data["banner_b64"]:
                bot_data["banner_b64"] = get_local_image_base64("media/banner.png", "image/png")
            
            # Get status from first guild
            if client.guilds:
                me = client.guilds[0].me
                if me:
                    status_colors = {
                        "online": "#23a55a",
                        "idle": "#f0b232",
                        "dnd": "#f23f43",
                        "offline": "#80848e"
                    }
                    bot_data["status_color"] = status_colors.get(str(me.status), "#f23f43")
                    
                    if me.activity and hasattr(me.activity, "name") and me.activity.name:
                        bot_data["custom_status"] = html.escape(me.activity.name)
        
        await client.close()
        print(f"[Card API] Updated bot data: {bot_data['name']}")
    except Exception as e:  # noqa: BLE001
        print(f"[Card API] Failed to fetch bot data: {e}")
        # Load fallback images
        bot_data["avatar_b64"] = get_local_image_base64("media/aika_marah.png", "image/png")
        bot_data["banner_b64"] = get_local_image_base64("media/banner.png", "image/png")

# Define the card endpoint
@app.get("/api/card.svg")
async def card_endpoint():
    """Serve the Discord-style profile card as SVG."""
    # Update bot data on each request
    await update_bot_data()
    
    bot_name = bot_data["name"]
    discriminator = bot_data["discriminator"]
    avatar_b64 = bot_data["avatar_b64"]
    banner_b64 = bot_data["banner_b64"]
    status_color = bot_data["status_color"]
    custom_status = bot_data["custom_status"]
    
    svg_content = f'''<svg width="340" height="375" viewBox="0 0 340 375" xmlns="http://www.w3.org/2000/svg">
    <style>
        <![CDATA[
        .font-main {{ font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif; }}
        .bg-card {{ fill: #232428; rx: 16px; }}
        .bg-banner {{ fill: #111214; }}
        .avatar-border {{ fill: #232428; }}
        .text-title {{ font-size: 20px; font-weight: 800; fill: #ffffff; }}
        .text-handle {{ font-size: 13px; font-weight: 500; fill: #b5bac1; }}
        .text-section {{ font-size: 11px; font-weight: 700; fill: #b5bac1; text-transform: uppercase; letter-spacing: 0.5px; }}
        .text-body {{ font-size: 13px; fill: #dbdee1; }}
        .badge-app {{ fill: #5865f2; rx: 3px; }}
        .badge-app-text {{ font-size: 10px; font-weight: 800; fill: #ffffff; }}
        .bubble-bg {{ fill: #111214; rx: 12px; }}
        .bubble-text {{ font-size: 12px; fill: #dbdee1; font-weight: 500; }}
        .role-pill {{ fill: #2b2d31; rx: 12px; stroke: #35363c; stroke-width: 1px; }}
        .role-text {{ font-size: 11px; fill: #dbdee1; font-weight: 600; }}
        ]]>
    </style>

    <defs>
        <clipPath id="banner-clip">
            <rect width="340" height="105" rx="16" />
        </clipPath>
        <clipPath id="avatar-clip">
            <circle cx="62" cy="100" r="38" />
        </clipPath>
    </defs>

    <rect width="100%" height="100%" class="bg-card font-main" />

    <!-- Banner Header -->
    <g clip-path="url(#banner-clip)">
        <rect width="340" height="105" class="bg-banner" />
        {'<image href="' + banner_b64 + '" width="340" height="105" preserveAspectRatio="xMidYMid slice" />' if banner_b64 else ''}
    </g>

    <!-- Status Speech Bubble -->
    <rect x="120" y="85" width="160" height="28" class="bubble-bg font-main" />
    <text x="132" y="103" class="bubble-text font-main">{custom_status}</text>

    <!-- Avatar Circle -->
    <circle cx="62" cy="100" r="44" class="avatar-border" />
    <circle cx="62" cy="100" r="38" fill="#313338" />
    {'<image href="' + avatar_b64 + '" x="24" y="62" width="76" height="76" clip-path="url(#avatar-clip)" />' if avatar_b64 else ''}

    <!-- Status Indicator -->
    <circle cx="90" cy="126" r="11" class="avatar-border" />
    <circle cx="90" cy="126" r="8" fill="{status_color}" />

    <!-- Username & APP Tag -->
    <text x="24" y="172" class="text-title font-main">{bot_name}</text>
    <rect x="{28 + len(bot_name) * 12}" y="156" width="32" height="18" class="badge-app" />
    <text x="{33 + len(bot_name) * 12}" y="169" class="badge-app-text font-main">APP</text>

    <!-- Handle & Discriminator -->
    <text x="24" y="194" class="text-handle font-main">{bot_name.lower().replace(' ', '')}{discriminator}</text>

    <!-- Bio Description -->
    <text x="24" y="225" class="text-body font-main">Halo. Aku maskot BinRoom. Salam kenal.</text>

    <!-- Roles Header -->
    <text x="24" y="257" class="text-section font-main">Roles</text>

    <!-- Role Pills -->
    <rect x="24" y="269" width="100" height="24" class="role-pill" />
    <circle cx="36" cy="281" r="4" fill="#d675c5" />
    <text x="46" y="285" class="role-text font-main">Aika Yokina</text>

    <rect x="130" y="269" width="110" height="24" class="role-pill" />
    <circle cx="142" cy="281" r="4" fill="#d675c5" />
    <text x="152" y="285" class="role-text font-main">Maskot Server</text>

    <rect x="24" y="299" width="85" height="24" class="role-pill" />
    <circle cx="36" cy="311" r="4" fill="#ff79c6" />
    <text x="46" y="315" class="role-text font-main">Female</text>
</svg>'''

    headers = {
        "Content-Type": "image/svg+xml",
        "Cache-Control": "max-age=0, no-cache, no-store, must-revalidate",
    }
    return Response(content=svg_content, headers=headers, media_type="image/svg+xml")

# Add a simple health check endpoint
@app.get("/")
async def health_check():
    """Health check endpoint."""
    return {"status": "ok", "service": "card-api"}

if __name__ == "__main__":
    port = int(os.getenv("CARD_PORT", 16426))  # noqa: PLW1508
    print(f"\n🎨 Card API starting on port {port}")
    print(f"📊 Card available at: http://localhost:{port}/api/card.svg\n")
    
    ui.run(
        host="0.0.0.0",
        port=port,
        show=False,
        reload=False,
        title="Aika Card API",
        forwarded_allow_ips="*",
    )
