import asyncio
import os
import sys
import time

import discord
from discord.ext import commands


class TombolKonfirmasi(discord.ui.View):
    def __init__(self, author_id:int, action_name:str):
        super().__init__(timeout=15.0)
        self.author_id = author_id
        self.action_name = action_name
        self.confirmed = False
        self.interaction: discord.Interaction = None

    async def interaction_check(self, interaction:discord.Interaction) -> bool:
        if interaction.user.id != self.author_id:
            await interaction.response.send_message("❌ Hanya pemilik bot yang dapat mengonfirmasi ini.", ephemeral=True)
            return False
        return True

    @discord.ui.button(label="⏻ Konfirmasi", style=discord.ButtonStyle.danger)
    async def confirm(self, interaction:discord.Interaction, button:discord.ui.Button):
        self.confirmed = True
        self.interaction = interaction
        self.stop()

    @discord.ui.button(label="🔙 Batal", style=discord.ButtonStyle.secondary)
    async def cancel(self, interaction: discord.Interaction, button:discord.ui.Button):
        self.confirmed = False
        self.interaction = interaction
        self.stop()


class TombolPower(commands.Cog):
    def __init__(self, bot:commands.Bot):
        self.bot = bot

    async def _trigger_log(self, action: str):
        try:
            logger_cog = self.bot.get_cog("ServerLogger")
            if logger_cog:
                if action == "shutdown" and hasattr(logger_cog, "send_shutdown_log"):
                    await logger_cog.send_shutdown_log()
                elif action == "restart" and hasattr(logger_cog, "send_restart_log"):
                    await logger_cog.send_restart_log()
        except (discord.HTTPException, AttributeError) as e:
            print(f"[Aika] Error saat membaca log untuk {action}: {e}")

    @commands.hybrid_command(name="shutdown", aliases=["turn_off", "stop", "power_off", "log_off"])
    @commands.is_owner()
    async def shutdown(self, ctx:commands.Context):
        target_waktu = int(time.time())+15
        
        embed_konfirm = discord.Embed(
            title = "⚠️🌸 Yakin ingin mematikan Aika?",
            description = f"-# Batal otomatis <t:{target_waktu}:R>",
            color = 0xFFCC4D
        )
        view = TombolKonfirmasi(ctx.author.id, "shutdown")
        msg = await ctx.send(embed=embed_konfirm, view=view)
        
        await view.wait()
        
        if not view.confirmed:
            embed_batal = discord.Embed(title="✅🌸 Shutdown dibatalkan.", color=0x77B155)
            await msg.edit(embed=embed_batal, view=None)
            if view.interaction:
                await view.interaction.response.edit_message(embed=embed_batal, view=None)
            else:
                await msg.edit(embed=embed_batal, view=None)
            return
        
        embed_shutdown = discord.Embed(title="⏻🌸 Aika akan shutdown sesaat lagi...", color=0xD42C41)
        if view.interaction:
            await view.interaction.response.edit_message(embed=embed_shutdown, view=None)
        else:
            await msg.edit(embed=embed_shutdown, view=None)
        
        await self._trigger_log("shutdown")
        await asyncio.sleep(7)
        
        try:
            await self.bot.change_presence(status=discord.Status.invisible)
        except discord.HTTPException as e:
            print(f"[Aika] Gagal mengubah status menjadi offline: {e}")
        
        try:
            embed_final = discord.Embed(title="⏻🌸 Aika sudah offline. Dadah.")
            await msg.edit(embed=embed_final)
        except discord.HTTPException as e:
            print(f"[Aika] Gagal mengedit pesan shutdown: {e}")
        
        try:
            await self.bot.close()
        except discord.HTTPException as e:
            print(f"[Aika] Gagal menutup bot: {e}")
        finally:
            os._exit(0)

    @commands.hybrid_command(name="restart", aliases=["reboot"])
    @commands.is_owner()
    async def restart(self, ctx:commands.Context):
        target_waktu = int(time.time())+15
        
        embed_konfirm = discord.Embed(
            title = "⚠️🌸 Yakin ingin memulai ulang Aika?",
            description = f"-# Batal otomatis <t:{target_waktu}:R>",
            color = 0xFFCC4D
        )
        view = TombolKonfirmasi(ctx.author.id, "restart")
        msg = await ctx.send(embed=embed_konfirm, view=view)
        
        await view.wait()
        
        if not view.confirmed:
            embed_batal = discord.Embed(title="✅🌸 Restart dibatalkan.", color=0x77B155)
            if view.interaction:
                await view.interaction.response.edit_message(embed=embed_batal, view=None)
            else:
                await msg.edit(embed=embed_batal, view=None)
            return


        embed_restart = discord.Embed(title="🔄🌸 Aika akan restart...", color=discord.Color.gold())
        
        if view.interaction:
            await view.interaction.response.edit_message(embed=embed_restart, view=None)
        else:
            await msg.edit(embed=embed_restart, view=None)
            
        await self._trigger_log("restart")
        
        try:
            await self.bot.close()
        except discord.HTTPException as e:
            print(f"[Aika] Gagal menutup bot untuk restart: {e}")
        
        restart_args = sys.argv.copy() + ["--restart-msg", str(ctx.channel.id), str(msg.id)]
        
        try:
            await asyncio.create_subprocess_exec(sys.executable, *restart_args)
        except OSError as e:
            print(f"[Aika] Gagal menitip subprocess untuk restart: {e}")
        finally:
            os._exit(0)

    @commands.Cog.listener()
    async def on_ready(self):
        if "--restart-msg" in sys.argv:
            try:
                index = sys.argv.index("--restart-msg")
                channel_id = int(sys.argv[index+1])
                message_id = int(sys.argv[index+2])
                
                del sys.argv[index:index+3]
                
                channel = self.bot.get_channel(channel_id)
                if channel is None:
                    try:
                        channel = await self.bot.fetch_channel(channel_id)
                    except (discord.NotFound, discord.Forbidden):
                        print(f"[Aika] Tidak dapat menemukan channel dengan ID {channel_id}.")
                        return
                    
                if channel:
                    try:
                        message = await channel.fetch_message(message_id)
                        embed = discord.Embed(title="✅🌸 Aika selesai restart!", color=0x76AE58)
                        await message.edit(embed=embed)
                    except discord.NotFound:
                        print(f"[Aika] Tidak dapat menemukan pesan dengan ID {message_id} di channel {channel_id}.")
                    except discord.Forbidden:
                        print(f"[Aika] Tidak memiliki izin untuk mengedit pesan dengan ID {message_id} di channel {channel_id}.")
            except (ValueError, IndexError) as e:
                print(f"[Aika] Kesalahan saat memproses argumen restart: {e}")
            except discord.HTTPException as e:
                print(f"[Aika] Error saat mengedit pesan untuk restart: {e}")

    async def command_cog_error(self, ctx:commands.Context, error:Exception):
        if isinstance(error, commands.NotOwner):
            try:
                await ctx.send("❌ Fitur ini khusus untuk developer Aika!")
            except discord.HTTPException:
                pass
        else:
            print(f"[Aika] Terjadi error pada command {ctx.command}: {error}")

async def setup(bot:commands.Bot):
    await bot.add_cog(TombolPower(bot))