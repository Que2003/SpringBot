from discord.ext import commands

class Basic(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.command()
    async def ping(self, ctx):
        await ctx.send("Pong!")

    @commands.command()
    async def hello(self, ctx):
        await ctx.send("Hey, I'm online.")

async def setup(bot):
    await bot.add_cog(Basic(bot))
