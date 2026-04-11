import discord
from discord.ext import commands

class Utility(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.command()
    async def avatar(self, ctx, member: discord.Member = None):
        member = member or ctx.author
        await ctx.send(member.display_avatar.url)

async def setup(bot):
    await bot.add_cog(Utility(bot))
