import random
from discord.ext import commands

JOKES = [
    "Why do programmers hate nature? Too many bugs.",
    "Why was the computer cold? It left its Windows open.",
    "Why did the keyboard break up with the mouse? Too many clicks.",
]
FACTS = [
    "Octopuses have three hearts.",
    "A day on Venus is longer than a year on Venus.",
    "Bananas are berries, but strawberries are not.",
]
QUOTES = [
    "Discipline beats motivation when motivation disappears.",
    "Consistency is louder than hype.",
    "Knowledge grows when you actually use it.",
]
WYR = [
    "Would you rather time travel to the past or the future?",
    "Would you rather have unlimited knowledge or unlimited money?",
    "Would you rather be famous online or respected offline?",
]
BALL = ["Yes.", "No.", "Maybe.", "Absolutely.", "Not likely.", "Ask again later.", "Without a doubt."]

class Fun(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.command(name="joke")
    async def joke(self, ctx):
        await ctx.send(random.choice(JOKES))

    @commands.command(name="fact")
    async def fact(self, ctx):
        await ctx.send(random.choice(FACTS))

    @commands.command(name="quote")
    async def quote(self, ctx):
        await ctx.send(random.choice(QUOTES))

    @commands.command(name="wouldyourather", aliases=["wyr"])
    async def wyr(self, ctx):
        await ctx.send(random.choice(WYR))

    @commands.command(name="8ball")
    async def eightball(self, ctx, *, question: str):
        await ctx.send(f"🎱 Question: {question}\nAnswer: {random.choice(BALL)}")

async def setup(bot):
    await bot.add_cog(Fun(bot))
