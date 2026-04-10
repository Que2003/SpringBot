import discord
from discord.ext import commands

class Basic(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @commands.command(name="help")
    async def help_command(self, ctx: commands.Context):
        embed = discord.Embed(
            title="SpringBot Realtime",
            description="Full multi-purpose Discord bot with study tools and live info feeds."
        )
        embed.add_field(name="Core", value="`!help` `!ping` `!status`", inline=False)
        embed.add_field(name="Music", value="`!join` `!radio <lofi|jazz|classical|news>` `!stream <audio_url>` `!queueadd <audio_url>` `!queue` `!skip` `!stop` `!leave` `!volume <0-100>`", inline=False)
        embed.add_field(name="Study", value="`!chapters` `!chapter <number>` `!studysearch <term>` `!quiz <topic>` `!flashcard` `!studytip` `!explain <topic>`", inline=False)
        embed.add_field(name="News/Info", value="`!news tech` `!news world` `!news science` `!headlines` `!wiki <topic>` `!define <word>` `!timein <city>` `!math <expression>`", inline=False)
        embed.add_field(name="Writing", value="`!grammar <text>` `!betterphrase <text>` `!rewrite <tone> | <text>`", inline=False)
        embed.add_field(name="Empathy/Fun", value="`!comfort` `!encourage` `!checkin` `!vent <text>` `!joke` `!fact` `!quote` `!wyr` `!8ball <question>`", inline=False)
        embed.add_field(name="Utility/Mod", value="`!userinfo` `!serverinfo` `!avatar` `!poll` `!purge` `!kick` `!ban` `!timeout` `!say`", inline=False)
        await ctx.send(embed=embed)

    @commands.command(name="ping")
    async def ping(self, ctx: commands.Context):
        await ctx.send(f"Pong. `{round(self.bot.latency * 1000)}ms`")

    @commands.command(name="status")
    async def status(self, ctx: commands.Context):
        embed = discord.Embed(title="SpringBot Status")
        embed.add_field(name="Latency", value=f"`{round(self.bot.latency * 1000)}ms`")
        embed.add_field(name="Guilds", value=f"`{len(self.bot.guilds)}`")
        embed.add_field(name="Cogs", value=", ".join(self.bot.extensions.keys())[:1024], inline=False)
        await ctx.send(embed=embed)

    @commands.Cog.listener()
    async def on_member_join(self, member: discord.Member):
        channel_id = getattr(self.bot, "welcome_channel_id", 0)
        if not channel_id:
            return
        channel = member.guild.get_channel(channel_id)
        if channel and isinstance(channel, discord.TextChannel):
            await channel.send(f"Welcome {member.mention} to **{member.guild.name}**. Use `!help` to see commands.")

    @commands.Cog.listener()
    async def on_command_error(self, ctx: commands.Context, error: Exception):
        if isinstance(error, commands.CommandNotFound):
            return
        if isinstance(error, commands.MissingRequiredArgument):
            await ctx.send(f"Missing argument: `{error.param.name}`")
            return
        if isinstance(error, commands.MissingPermissions):
            await ctx.send("You do not have permission for that.")
            return
        await ctx.send(f"Error: {getattr(error, 'original', error)}")

async def setup(bot: commands.Bot):
    await bot.add_cog(Basic(bot))
