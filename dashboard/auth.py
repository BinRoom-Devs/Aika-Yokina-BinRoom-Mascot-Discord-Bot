import os
import httpx
from discord.ext import commands
from fastapi import Request
from fastapi.responses import RedirectResponse
from starlette.middleware.sessions import SessionMiddleware
from nicegui import app

OWNER_ID = 1524951093560213638 #@arumugi_4405
SERVER_ID = 1537905133311230112 #mugi cloud
DISCORD_CLIENT_ID = os.getenv("DISCORD_CLIENT_ID")
DISCORD_CLIENT_SECRET = os.getenv("DISCORD_CLIENT_SECRET")
REDIRECT_URI = os.getenv("DISCORD_REDIRECT_URI", "http://localhost:8080/auth/callback")


def setup_auth(fastapi_app):
    """Registers session middleware and OAuth2 endpoints."""
    secret_key = os.getenv("SESSION_SECRET_KEY", "change-this-in-production")
    fastapi_app.add_middleware(SessionMiddleware, secret_key=secret_key)

    @fastapi_app.get("/login")
    def login():
        discord_auth_url = (
            f"https://discord.com/oauth2/authorize?client_id={DISCORD_CLIENT_ID}"
            f"&redirect_uri={REDIRECT_URI}&response_type=code&scope=identify"
        )
        return RedirectResponse(discord_auth_url)

    @fastapi_app.get("/auth/callback")
    async def auth_callback(request: Request):
        code = request.query_params.get("code")
        if not code:
            return RedirectResponse("/login")

        data = {
            "client_id": DISCORD_CLIENT_ID,
            "client_secret": DISCORD_CLIENT_SECRET,
            "grant_type": "authorization_code",
            "code": code,
            "redirect_uri": REDIRECT_URI,
        }
        headers = {"Content-Type": "application/x-www-form-urlencoded"}

        async with httpx.AsyncClient() as client:
            token_res = await client.post(
                "https://discord.com/api/v10/oauth2/token",
                data=data,
                headers=headers,
            )
            token_json = token_res.json()
            access_token = token_json.get("access_token")

            if not access_token:
                return RedirectResponse("/login")

            user_res = await client.get(
                "https://discord.com/api/v10/users/@me",
                headers={"Authorization": f"Bearer {access_token}"},
            )
            user_data = user_res.json()

        # Save ID, username, and avatar in session
        user_id = int(user_data.get("id", 0))
        avatar_hash = user_data.get("avatar")
        
        request.session["user_id"] = user_id
        request.session["username"] = user_data.get("username", "Admin")
        
        if avatar_hash:
            ext = "gif" if avatar_hash.startswith("a_") else "png"
            request.session["avatar_url"] = f"https://cdn.discordapp.com/avatars/{user_id}/{avatar_hash}.{ext}"
        else:
            request.session["avatar_url"] = "https://cdn.discordapp.com/embed/avatars/0.png"

        return RedirectResponse("/")

    @fastapi_app.get("/logout")
    def logout(request: Request):
        request.session.clear()
        return RedirectResponse("/login")


def is_user_admin(bot: commands.Bot, user_id: int) -> bool:
    if user_id == OWNER_ID: return True
    if not bot.guilds: return False

    guild = bot.get_guild(SERVER_ID) or bot.guilds[0]
    
    member = guild.get_member(user_id)
    if member is None: return False

    return member.id == guild.owner_id or member.guild_permissions.administrator


def is_authenticated_admin(request: Request, bot: commands.Bot) -> bool:
    """Verifies if current session belongs to the server owner."""
    user_id = request.session.get("user_id")
    if not user_id:
        return False
    return is_user_admin(bot, int(user_id))


def get_user_admin_role(bot, user_id: int):
    """
    Finds the primary role with Administrator permissions for this user across servers.
    Returns (role_name, role_color_hex).
    """
    for guild in bot.guilds:
        member = guild.get_member(user_id)
        if member:
            # Server Owner always gets full admin authority
            if member.id == guild.owner_id:
                top_role = member.top_role
                color_hex = f"#{top_role.color.value:06x}" if top_role.color.value else "#d675c5"
                return top_role.name, color_hex
            
            # Check for explicitly assigned administrator roles
            for role in reversed(member.roles):
                if role.permissions.administrator and not role.is_default():
                    color_hex = f"#{role.color.value:06x}" if role.color.value else "#d675c5"
                    return role.name, color_hex
                    
    return "Admin", "#d675c5"