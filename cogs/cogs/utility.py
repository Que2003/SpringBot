
import discord
from discord.ext import commands

class Utility(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @commands.command(name="userinfo")
    async def userinfo(self, ctx: commands.Context, member: discord.Member | None = None):
        member = member or ctx.author
        embed = discord.Embed(title=f"User Info: {member}")
        embed.add_field(name="ID", value=f"`{member.id}`", inline=False)
        embed.add_field(name="Joined", value=discord.utils.format_dt(member.joined_at, "F") if member.joined_at else "Unknown", inline=False)
        embed.add_field(name="Created", value=discord.utils.format_dt(member.created_at, "F"), inline=False)
        embed.set_thumbnail(url=member.display_avatar.url)
        await ctx.send(embed=embed)

    @commands.command(name="serverinfo")
    async def serverinfo(self, ctx: commands.Context):
        guild = ctx.guild
        embed = discord.Embed(title=f"Server Info: {guild.name}")
        embed.add_field(name="Members", value=f"`{guild.member_count}`")
        embed.add_field(name="Channels", value=f"`{len(guild.channels)}`")
        embed.add_field(name="Roles", value=f"`{len(guild.roles)}`")
        embed.add_field(name="Owner", value=f"`{guild.owner}`", inline=False)
        if guild.icon:
            embed.set_thumbnail(url=guild.icon.url)
        await ctx.send(embed=embed)

    @commands.command(name="avatar")
    async def avatar(self, ctx: commands.Context, member: discord.Member | None = None):
        member = member or ctx.author
        embed = discord.Embed(title=f"{member}'s avatar")
        embed.set_image(url=member.display_avatar.url)
        await ctx.send(embed=embed)

    @commands.command(name="poll")
    async def poll(self, ctx: commands.Context, *, raw: str):
        parts = [p.strip() for p in raw.split("|") if p.strip()]
        if len(parts) < 3:
            await ctx.send("Use: `!poll Question | Option 1 | Option 2`")
            return
        question = parts[0]
        options = parts[1:11]
        emojis = ["1️⃣","2️⃣","3️⃣","4️⃣","5️⃣","6️⃣","7️⃣","8️⃣","9️⃣","🔟"]
        desc = "\n".join(f"{emojis[i]} {opt}" for i, opt in enumerate(options))
        embed = discord.Embed(title="Poll", description=f"**{question}**\n\n{desc}")
        message = await ctx.send(embed=embed)
        for i in range(len(options)):
            await message.add_reaction(emojis[i])

async def setup(bot: commands.Bot):
    await bot.add_cog(Utility(bot))
