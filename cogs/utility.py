import discord
from discord.ext import commands

class Utility(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.command(
        help="Shows the avatar of you or another server member."
    )
    async def avatar(self, ctx, member: discord.Member = None):
        member = member or ctx.author
        await ctx.send(
            f"Avatar for **{member.display_name}**:\n{member.display_avatar.url}"
        )

    @commands.command(
        help="Shows the current server name and member count."
    )
    async def server(self, ctx):
        guild = ctx.guild
        await ctx.send(
            f"Server name: **{guild.name}**\n"
            f"Server ID: **{guild.id}**\n"
            f"Total members: **{guild.member_count}**"
        )

    @commands.command(
        help="Shows information about you or another server member."
    )
    async def userinfo(self, ctx, member: discord.Member = None):
        member = member or ctx.author
        joined_at = member.joined_at.strftime("%Y-%m-%d %H:%M:%S") if member.joined_at else "Unknown"
        created_at = member.created_at.strftime("%Y-%m-%d %H:%M:%S")

        await ctx.send(
            f"User information for **{member}**\n"
            f"Display name: **{member.display_name}**\n"
            f"User ID: **{member.id}**\n"
            f"Account created: **{created_at}**\n"
            f"Joined server: **{joined_at}**"
        )

    @commands.command(
        help="Shows the current bot prefix."
    )
    async def prefix(self, ctx):
        await ctx.send("The current command prefix is: **!**")

    @commands.command(
        help="Shows the bot latency in milliseconds."
    )
    async def pinginfo(self, ctx):
        latency = round(self.bot.latency * 1000)
        await ctx.send(f"Current bot latency: **{latency}ms**")

async def setup(bot):
    await bot.add_cog(Utility(bot))
