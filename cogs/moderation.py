import asyncio
from datetime import timedelta
import discord
from discord.ext import commands

class Moderation(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.command(name="say")
    @commands.has_permissions(manage_messages=True)
    async def say(self, ctx, *, message: str):
        await ctx.send(message)

    @commands.command(name="purge")
    @commands.has_permissions(manage_messages=True)
    async def purge(self, ctx, amount: int):
        amount = max(1, min(amount, 100))
        deleted = await ctx.channel.purge(limit=amount + 1)
        msg = await ctx.send(f"Deleted `{len(deleted) - 1}` messages.")
        await asyncio.sleep(3)
        try:
            await msg.delete()
        except Exception:
            pass

    @commands.command(name="kick")
    @commands.has_permissions(kick_members=True)
    async def kick(self, ctx, member: discord.Member, *, reason: str = "No reason provided"):
        await member.kick(reason=reason)
        await ctx.send(f"Kicked **{member}** | Reason: {reason}")

    @commands.command(name="ban")
    @commands.has_permissions(ban_members=True)
    async def ban(self, ctx, member: discord.Member, *, reason: str = "No reason provided"):
        await member.ban(reason=reason)
        await ctx.send(f"Banned **{member}** | Reason: {reason}")

    @commands.command(name="timeout")
    @commands.has_permissions(moderate_members=True)
    async def timeout(self, ctx, member: discord.Member, minutes: int, *, reason: str = "No reason provided"):
        until = discord.utils.utcnow() + timedelta(minutes=max(1, min(minutes, 40320)))
        await member.timeout(until, reason=reason)
        await ctx.send(f"Timed out **{member}** for `{minutes}` minutes.")

async def setup(bot):
    await bot.add_cog(Moderation(bot))
