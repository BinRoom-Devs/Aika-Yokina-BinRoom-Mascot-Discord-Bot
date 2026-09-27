"""Berisi komponen UI Discord yang interaktif buat tombol & konteks menu."""

import discord
from discord import app_commands


class HapusIngatan(discord.ui.View):
    def __init__(self, cog, user_id:int):
        super().__init__(timeout=30)
        self.cog = cog
        self.user_id = user_id
        self.message: discord.Message | None = None
    
    async def on_timeout(self):
        for child in self.children:
            child.disabled = True
        
        embed = discord.Embed(
            title="Gak jadi reset, ya?",
            description="Sip, deh, Aika masih bakal ingat kamu. 😌",
            color=0xD675C1,
        )
        if self.message:
            try:
                await self.message.edit(embed=embed, view=self)
            except discord.NotFound:
                pass
    
    async def cek_beda_orang(self, interaction:discord.Interaction) -> bool:
        if interaction.user.id != self.user_id:
            bot = getattr(self.cog, "bot", interaction.client)
            target_user = bot.get_user(self.user_id)
            user_name = target_user.display_name if target_user else "orang lain"
            
            await interaction.response.send_message(
                f"Kamu siapa? Ini konfirmasinya {user_name}, bukan punyamu. 🧐😒",
                ephemeral=True
            )
            
            return True
        
        return False
    
    async def hapus_ingatan(self, interaction:discord.Interaction, judul:str, desc:str, color:int, clear_mem:bool):
        if await self.cek_beda_orang(interaction):
            return
        
        if clear_mem and self.user_id in self.cog.user_chats:
            del self.cog.user_chats[self.user_id]
            await self.cog.simpan_chat(self.user_id)
        
        for child in self.children:
            child.disabled = True
        
        self.stop()
        embed = discord.Embed(title=judul, description=desc, color=color)
        await interaction.response.edit_message(embed=embed, view=self)
    
    @discord.ui.button(label="Ya, konfirmasi", style=discord.ButtonStyle.success, emoji="✅")
    async def konfirmasi(self, interaction:discord.Interaction, button:discord.ui.Button):
        await self.hapus_ingatan(
            interaction,
            "✅ Memori dihapus",
            "Ingatan Aika tentangmu udah di-reset.",
            0xD675C1,
            clear_mem=True
        )
        if interaction.guild:
            self.cog.bot.dispatch(
                "ai_log",
                interaction.guild,
                interaction.user,
                "Ingatan Dihapus",
                f"{interaction.user.mention} telah mereset memori percakapannya dengan Aika.",
                discord.Color.gold()
            )
    
    @discord.ui.button(label="Jangan, batalin", style=discord.ButtonStyle.secondary, emoji="❌")
    async def batal(self, interaction:discord.Interaction, button:discord.ui.Button):
        await self.hapus_ingatan(
            interaction,
            "Dibatalkan",
            "Reset ingatan dibatalkan. Aika masih ingat kamu.",
            0xD675C1,
            clear_mem=False
        )


@app_commands.context_menu(name="Buat ulang respon")
@app_commands.guild_only()
async def buat_ulang_konteks_standalone(interaction:discord.Interaction, message:discord.Message):
    cog = interaction.client.get_cog("AIPersona")
    if cog:
        await cog._eksekusi_regenerate(interaction, message)
    else:
        await interaction.response.send_message("Fitur sedang tidak tersedia.", ephemeral=True)