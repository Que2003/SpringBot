import discord
from discord.ext import commands

class Basic(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @commands.command(name="help")
    async def help_command(self, ctx: commands.Context):
        embed = discord.Embed(
            title="SpringBot Clean",
            description="Simple stable bot build."
        )
        embed.add_field(name="Core", value="`!help` `!ping` `!status`", inline=False)
        embed.add_field(name="Fun", value="`!joke` `!fact`", inline=False)
        embed.add_field(name="Utility", value="`!userinfo` `!serverinfo`", inline=False)
        await ctx.send(embed=embed)

    @commands.command(name="ping")
    async def ping(self, ctx: commands.Context):
        await ctx.send(f"Pong. `{round(self.bot.latency * 1000)}ms`")

    @commands.command(name="status")
    async def status(self, ctx: commands.Context):
        embed = discord.Embed(title="SpringBot Status")
        embed.add_field(name="Latency", value=f"`{round(self.bot.latency * 1000)}ms`")
        embed.add_field(name="Guilds", value=f"`{len(self.bot.guilds)}`")
        await ctx.send(embed=embed)

    @commands.Cog.listener()
    async def on_command_error(self, ctx: commands.Context, error: Exception):
        if isinstance(error, commands.CommandNotFound):
            return
        if isinstance(error, commands.MissingRequiredArgument):
            await ctx.send(f"Missing argument: `{error.param.name}`")
            return
        await ctx.send(f"Error: {getattr(error, 'original', error)}")

async def setup(bot: commands.Bot):
    await bot.add_cog(Basic(bot))
