from discord.ext import commands

from ._cog import BinrumLeaderboard


async def setup(bot:commands.Bot):
    await bot.add_cog(BinrumLeaderboard(bot))