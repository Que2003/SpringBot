import random
from discord.ext import commands

class Fun(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.command()
    async def joke(self, ctx):
        jokes = [
            "Why did the bot lag? Too many bad commands.",
            "SpringBot never sleeps.",
            "You called, I answered."
        ]
        await ctx.send(random.choice(jokes))

async def setup(bot):
    await bot.add_cog(Fun(bot))
