import random
from discord.ext import commands

JOKES = [
    "Why do programmers hate nature? Too many bugs.",
    "Why was the computer cold? It left its Windows open.",
    "Why did the keyboard break up with the mouse? Too many clicks."
]

FACTS = [
    "Octopuses have three hearts.",
    "A day on Venus is longer than a year on Venus.",
    "Bananas are berries, but strawberries are not."
]

class Fun(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @commands.command(name="joke")
    async def joke(self, ctx: commands.Context):
        await ctx.send(random.choice(JOKES))

    @commands.command(name="fact")
    async def fact(self, ctx: commands.Context):
        await ctx.send(random.choice(FACTS))

async def setup(bot: commands.Bot):
    await bot.add_cog(Fun(bot))
