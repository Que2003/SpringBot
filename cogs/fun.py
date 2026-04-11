import random
from discord.ext import commands

class Fun(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.command(
        help="Tells a random joke."
    )
    async def joke(self, ctx):
        jokes = [
            "Why did the bot lag? Because it was carrying too many bad commands at once.",
            "SpringBot does not sleep. It just waits for the next command.",
            "You called for help, so I showed up before your Wi-Fi gave up.",
            "Why did the Discord bot get promoted? Because it always knew how to handle commands properly.",
            "I am not ignoring you. I am just processing your greatness one command at a time."
        ]
        await ctx.send(f"Here is your joke: {random.choice(jokes)}")

    @commands.command(
        help="Flips a coin and returns Heads or Tails."
    )
    async def coinflip(self, ctx):
        result = random.choice(["Heads", "Tails"])
        await ctx.send(f"The coin landed on: **{result}**")

    @commands.command(
        help="Rolls a standard six-sided dice."
    )
    async def roll(self, ctx):
        result = random.randint(1, 6)
        await ctx.send(f"You rolled a **{result}** on a 6-sided die.")

    @commands.command(
        help="Repeats the message you provide."
    )
    async def say(self, ctx, *, message):
        await ctx.send(f"You said: {message}")

    @commands.command(
        help="Answers with an 8-ball style response."
    )
    async def eightball(self, ctx, *, question):
        responses = [
            "Yes, definitely.",
            "No, not at all.",
            "It is possible.",
            "Ask again later.",
            "Without a doubt.",
            "That does not look likely.",
            "The signs point to yes.",
            "I would not count on it."
        ]
        await ctx.send(
            f"Question: {question}\nAnswer: **{random.choice(responses)}**"
        )

async def setup(bot):
    await bot.add_cog(Fun(bot))
