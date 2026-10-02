import re
import time
from datetime import datetime, timedelta, timezone

import discord
from discord.ext import commands

from ._views import HapusIngatan

wib_tz = timezone(timedelta(hours=7))


class StatsButtonsView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)
        
        self.add_item(discord.ui.Button(
            label="Info model AI",
            url="https://qwen.ai/blog?id=qwen3.6-27b",
            style=discord.ButtonStyle.link 
        ))
        
        self.add_item(discord.ui.Button(
            label="Source code (repositori GitHub)",
            url="https://github.com/AbinDai/Aika-Yokina-BinRoom-Mascot-Discord-Bot",
            style=discord.ButtonStyle.link
        ))


class AICommands(commands.Cog):
    def __init__(self, bot:commands.Bot):
        self.bot = bot
        if not hasattr(self.bot, "start_time"):
            self.bot.start_time = time.time()
    
    def get_ai_cog(self):
        cog = self.bot.get_cog("AIPersona")
        if not cog:
            print("[Aika] Gagal menemukan instance cog 'AIPersona'.")
        return cog
    
    def ubah_reset_groq_ke_unix(self, reset_str:str) -> int:
        if not reset_str or reset_str == "N/A":
            return None
            
        total_detik = 0.0
        jam = re.search(r'(\d+(\.\d+)?)h', reset_str)
        menit = re.search(r'(\d+(\.\d+)?)m', reset_str)
        detik = re.search(r'(\d+(\.\d+)?)s', reset_str)
        
        if jam:
            total_detik += float(jam.group(1)) * 3600
        if menit:
            total_detik += float(menit.group(1)) * 60
        if detik:
            total_detik += float(detik.group(1))
            
        if total_detik == 0.0:
            return None
        
        return int(time.time() + total_detik)
    
    def bikin_progress_bar(self, jumlah:int, total:int, panjang:int=13) -> str:
        if total <= 0:
            return "\u001b[30m░"*panjang+"\u001b[0m"
        
        progress = min(max(jumlah/total, 0.0), 1.0)
        terisi = round(panjang*progress)
        
        MERAH = "\u001b[31m"
        KUNING = "\u001b[33m"
        IJO = "\u001b[32m"
        ABUABU = "\u001b[30m"
        RESET = "\u001b[0m"
        
        bar = ""
        for i in range(panjang):
            if i < terisi:
                rasio = i / panjang
                
                if rasio < 0.25: warna = MERAH
                elif rasio < 0.50: warna = KUNING
                else: warna = IJO
                
                bar += f"{warna}█"
            else:
                bar += f"{ABUABU}░"
            
        return bar + RESET
    
    @commands.hybrid_group(name="ai", hidden=True)
    async def ai(self, ctx:commands.Context):
        pass
    
    @ai.command(
        name="kuota",
        description="Nampilin sisa kuota real-time Groq API.",
        aliases=["quota", "usage", "cek-kuota"]
    )
    async def kuota(self, ctx: commands.Context):
        await ctx.defer()
        
        ai_cog = self.get_ai_cog()
        if not ai_cog:
            await ctx.send("❌ Error: Cog AIPersona belum dimuat.", ephemeral=True)
            return
        
        meta = getattr(ai_cog, "last_api_meta", {})
        
        embed = discord.Embed(title="Kuota Chatbot Aika", color=0xF05237)
        embed.set_author(
            name="Ditenagai oleh Groq Qwen 3.8 27B",
            icon_url="https://cdn.discordapp.com/attachments/863959650448703538/1541385549254885506/groq-icon-logo-png_seeklogo-605779.png?ex=6a8eb828&is=6a8d66a8&hm=210df3a52c0d20e870523919d668d7be881ca5c3862e4735e12c65f4955f762a&"
        )
        
        if meta:
            rem_rpd = int(meta.get("rem_req_daily", 0)) if str(meta.get("rem_req_daily")).isdigit() else 0
            limit_rpd = int(meta.get("limit_req_daily", 1000)) if str(meta.get("limit_req_daily")).isdigit() else 1000
            
            rem_tpm = int(meta.get("rem_tok_min", 0)) if str(meta.get("rem_tok_min")).isdigit() else 0
            limit_tpm = int(meta.get("limit_tok_min", 8000)) if str(meta.get("limit_tok_min")).isdigit() else 8000
            
            bar_rpd = self.bikin_progress_bar(rem_rpd, limit_rpd, panjang=12)
            pct_rpd = int((rem_rpd / limit_rpd) * 100) if limit_rpd > 0 else 0
            
            bar_tpm = self.bikin_progress_bar(rem_tpm, limit_tpm, panjang=10)
            pct_tpm = int((rem_tpm / limit_tpm) * 100) if limit_tpm > 0 else 0
            
            rpd_unix = self.ubah_reset_groq_ke_unix(meta.get("reset_req_daily"))
            tpm_unix = self.ubah_reset_groq_ke_unix(meta.get("reset_tok_min"))
            
            rpd_str = f"<t:{rpd_unix}:R>" if rpd_unix else meta.get("reset_req_daily", "N/A")
            tpm_str = f"<t:{tpm_unix}:R>" if tpm_unix else meta.get("reset_tok_min", "N/A")
            
            rpd_field_value = (
                "```ansi\n"
                f"0 [{bar_rpd}] {rem_rpd}\n"
                "```\n"
                f"-# Reset {rpd_str}"
            )
            
            tpm_field_value = (
                "```ansi\n"
                f"0 [{bar_tpm}] {rem_tpm}\n"
                "```\n"
                f"-# Reset {tpm_str}"
            )
            
            embed.add_field(name=f"Kuota request harian: {pct_rpd}%", value=rpd_field_value, inline=True)
            embed.add_field(name=f"Kuota token per menit: {pct_tpm}%", value=tpm_field_value, inline=True)
        else:
            embed.description = "*Menunggu header respon pertama dari API...*"
        
        await ctx.send(embed=embed)
    
    @ai.command(
        name="statistik",
        description="Nampilin statistik penggunaan chatbot Aika.",
        aliases=["stats", "stat"]
    )
    async def stats(self, ctx:commands.Context):
        await ctx.defer()
        
        ai_cog = self.get_ai_cog()
        if not ai_cog:
            print("[Aika] Command dibatalkan karena cog AIPersona tidak terdeteksi.")
            await ctx.send("❌ Error: Cog AIPersona belum dimuat.", ephemeral=True)
            return
        
        meta = getattr(ai_cog, "last_api_meta", {})
        session = getattr(ai_cog, "session_usage", {
            "total_requests": 0,
            "prompt_tokens": 0,
            "completion_tokens": 0,
            "total_tokens": 0
        })
        
        print(f"[Aika] Mengambil data statistik. Total request sesi: {session.get('total_requests', 0)} | Ada data meta: {bool(meta)}")
        
        embed = discord.Embed(
            title="Statistik AI Aika",
            color=0xF05237,
        )
        
        icon_footer = "https://cdn.discordapp.com/attachments/863959650448703538/1540201066455371888/bunga.png?ex=6a8c6345&is=6a8b11c5&hm=b8a5432ef12255a46f3f94d6490a5fa22e4517b5182b4a52aea2ae41da76b117&"
        
        start_time = getattr(self.bot, "start_time", time.time())
        restart_wib = datetime.fromtimestamp(start_time, tz=wib_tz).strftime("%H:%M")
        
        embed.set_author(
            name="Ditenagai oleh Groq Qwen 3.8 27B",
            icon_url="https://cdn.discordapp.com/attachments/863959650448703538/1541386627434414160/Groq_Icon_-_Colored_-_338x512_-_zonalogo.com.png?ex=6a8d67a9&is=6a8c1629&hm=c61d6312865796f54c472103ae51b2151c003287f865e61473b29ec7d18d677a&"
        )
        embed.set_thumbnail(url="https://cdn.discordapp.com/attachments/863959650448703538/1541385549254885506/groq-icon-logo-png_seeklogo-605779.png?ex=6a8d66a8&is=6a8c1528&hm=00a831a2abda8bdc02f2cc949b86ca425cfd6b3de293825c35a9e92779000577&")
        embed.set_footer(icon_url=icon_footer, text=f"Aika sempat restart pada {restart_wib} WIB")
        
        field_1_name = "Performa request terkini"
        if meta:
            tps = meta.get("tok_per_sec", 0.0)
            q_time = meta.get("queue_time", 0.0)
            p_time = meta.get("prompt_time", 0.0)
            c_time = meta.get("completion_time", 0.0)
            t_time = meta.get("total_time", 0.0)
            
            perf_text = (
                f"`{tps:.1f}` token/detik\n"
                f"Total waktu: `{t_time:.3f}s`\n"
                f"-# └ Antrean: `{q_time:.3f}s`\n"
                f"-# └ Prompt: `{p_time:.3f}s`\n"
                f"-# └ Proses: `{c_time:.3f}s`"
            )
        else:
            perf_text = "*Belum ada rekaman panggilan API pada sesi ini.*"
        embed.add_field(name=field_1_name, value=perf_text, inline=True)
        
        field_2_name = "Akumulasi sesi"
        session_text = (
            f"Total request: `{session['total_requests']}`\n"
            f"Token prompt: `{session['prompt_tokens']:,}`\n"
            f"Token kelar: `{session['completion_tokens']:,}`\n"
            f"Token total: `{session['total_tokens']:,}`\n"
            f"Pengguna tercatat: `{len(getattr(ai_cog, 'user_chats', {}))}`"
        )
        embed.add_field(name=field_2_name, value=session_text, inline=True)
        
        field_3_name = "Token API terakhir"
        if meta:
            field_3_desc = (
                f"Input: `{meta.get('prompt_tokens')}`\n"
                f"Output: `{meta.get('completion_tokens')}`\n"
                f"Total: `{meta.get('total_tokens')}`"
            )
        else:
            field_3_desc = "*Menunggu...*"
        embed.add_field(name=field_3_name, value=field_3_desc, inline=True)
        
        if meta:
            rem_rpd = int(meta.get("rem_req_daily", 0)) if str(meta.get("rem_req_daily")).isdigit() else 0
            limit_rpd = int(meta.get("limit_req_daily", 1000)) if str(meta.get("limit_req_daily")).isdigit() else 1000
            
            rem_tpm = int(meta.get("rem_tok_min", 0)) if str(meta.get("rem_tok_min")).isdigit() else 0
            limit_tpm = int(meta.get("limit_tok_min", 8000)) if str(meta.get("limit_tok_min")).isdigit() else 8000
            
            bar_rpd = self.bikin_progress_bar(rem_rpd, limit_rpd, panjang=12)
            pct_rpd = int((rem_rpd / limit_rpd) * 100) if limit_rpd > 0 else 0
            
            bar_tpm = self.bikin_progress_bar(rem_tpm, limit_tpm, panjang=10)
            pct_tpm = int((rem_tpm / limit_tpm) * 100) if limit_tpm > 0 else 0
            
            rpd_unix = self.ubah_reset_groq_ke_unix(meta.get("reset_req_daily"))
            tpm_unix = self.ubah_reset_groq_ke_unix(meta.get("reset_tok_min"))
            
            rpd_str = f"<t:{rpd_unix}:R>" if rpd_unix else meta.get("reset_req_daily", "N/A")
            tpm_str = f"<t:{tpm_unix}:R>" if tpm_unix else meta.get("reset_tok_min", "N/A")
            
            rpd_field_value = (
                "```ansi\n"
                f"0 [{bar_rpd}] {rem_rpd}\n"
                "```\n"
                f"-# Reset {rpd_str}"
            )
            
            tpm_field_value = (
                "```ansi\n"
                f"0 [{bar_tpm}] {rem_tpm}\n"
                "```\n"
                f"-# Reset {tpm_str}"
            )
            
            embed.add_field(name=f"Kuota request harian: {pct_rpd}%", value=rpd_field_value, inline=True)
            embed.add_field(name=f"Kuota token per menit: {pct_tpm}%", value=tpm_field_value, inline=True)
        else:
            embed.add_field(name="Kuota real-time Groq", value="*Menunggu header respon pertama dari API...*", inline=True)
        
        view = StatsButtonsView()
        print("[Aika] Membalas embed statistik")
        await ctx.send(embed=embed, view=view)
    
    @ai.command(
        name="memory",
        description="Ngecek kapasitas memori percakapan Aika denganmu.",
        aliases=["memori", "status-memori", "memory-status", "cek-memori"]
    )
    async def memory_status(self, ctx:commands.Context):
        ai_cog = self.get_ai_cog()
        if not ai_cog:
            pesan = "❌ Eror: perintah ini belum terhubung dengan modul chat AI."
            if ctx.interaction:
                await ctx.interaction.response.send_message(pesan, ephemeral=True)
            else:
                await ctx.send(pesan)
            return
        
        if ctx.author.id not in ai_cog.user_chats:
            msg = "Mau cek apa? Aika aja belum tau apapun soalmu. 😒"
            if ctx.interaction:
                await ctx.interaction.response.send_message(msg, ephemeral=True)
            else:
                await ctx.send(msg, delete_after=12)
            return
        
        chat = ai_cog.user_chats[ctx.author.id]
        pesan_chat = [message for message in chat if message["role"] != "system"]
        jumlah_pesan = len(pesan_chat)
        
        kapasitas_max = ai_cog.max_memory_messages
        persentase = min(int((jumlah_pesan / kapasitas_max) * 100), 100)
        kotak_terisi = int(persentase / 10)
        bar = ("█" * kotak_terisi + "░" * (10 - kotak_terisi))
        
        if persentase < 25:
            flavor = "Baru kenal dikit... ingatan masih ringan."
        elif persentase >= 50:
            flavor = "Kita mulai kenal dekat nih."
        elif persentase < 75:
            flavor = "Udah lumayan sering ngobrol nih."
        else:
            flavor = "Kita udah kenal banyak..."
        
        embed = discord.Embed(
            title=f"Status Ingatan Aika ({ctx.author.display_name})",
            description=f"**Kapasitas:** [{bar}] `{persentase}%`\n**Pesan tersimpan:** `{jumlah_pesan}/{kapasitas_max}` pesan\n\n",
            color=0xD675C1
        )
        embed.set_footer(
            text="Pesan paling lama akan dihapus otomatis saat penuh.\nMau hapus semua sekalian? Gunakan ak!reset-memori",
            icon_url="https://cdn.discordapp.com/attachments/863959650448703538/1540201066455371888/bunga.png?ex=6a8b11c5&is=6a89c045&hm=2f7837e9e91cf914975584cb8ba5f001f80ea54d36c86e643547b1f23a111b26&"
        )
        embed.set_thumbnail(url=ctx.author.display_avatar.url)
        
        if ctx.interaction:
            await ctx.interaction.response.send_message(content=flavor, embed=embed, ephemeral=True)
        else:
            await ctx.send(content=flavor, embed=embed)
    
    @ai.command(
        name="memory-reset",
        description="Ngehapus ingatan percakapan Aika denganmu.",
        aliases=["reset", "hapus-ingatan", "reset-memory", "reset-memori"]
    )
    async def reset_memori(self, ctx:commands.Context):
        ai_cog = self.get_ai_cog()
        if not ai_cog:
            await ctx.send("❌ Eror: perintah ini belum terhubung dengan modul chat AI.", ephemeral=True)
            return
        
        if ctx.author.id not in ai_cog.user_chats:
            await ctx.send("Mau reset apa? Aika aja belum tau apapun soalmu. 🧐", ephemeral=True, delete_after=12)
            return
        
        timeout_timestamp = int(time.time() + 30)
        embed = discord.Embed(
            title="⚠️ Konfirmasi Reset Memori",
            description=f"Kamu yakin ingin menghapus semua ingatan percakapan Aika denganmu? Tindakan ini gabisa dibalikin.\n\n-# Batal otomatis <t:{timeout_timestamp}:R>",
            color=discord.Color.orange()
        )
        
        view = HapusIngatan(cog=ai_cog, user_id=ctx.author.id)
        
        if ctx.interaction:
            await ctx.interaction.response.send_message(embed=embed, view=view, ephemeral=True)
            view.message = await ctx.interaction.original_response()
        else:
            view.message = await ctx.send(embed=embed, view=view)
    

async def setup(bot:commands.Bot):
    await bot.add_cog(AICommands(bot))