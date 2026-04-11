import discord
from discord.ext import commands

class Moderation(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.command(
        help="Deletes a set number of recent messages from the current channel."
    )
    @commands.has_permissions(manage_messages=True)
    async def clear(self, ctx, amount: int = 5):
        if amount < 1:
            await ctx.send("You must choose at least 1 message to delete.")
            return

        deleted = await ctx.channel.purge(limit=amount + 1)
        confirm = await ctx.send(f"Deleted **{len(deleted) - 1}** message(s).")
        await confirm.delete(delay=3)

    @commands.command(
        help="Kicks a member from the server."
    )
    @commands.has_permissions(kick_members=True)
    async def kick(self, ctx, member: discord.Member, *, reason="No reason provided"):
        if member == ctx.author:
            await ctx.send("You cannot kick yourself.")
            return

        if member == ctx.guild.me:
            await ctx.send("I cannot kick myself.")
            return

        await member.kick(reason=reason)
        await ctx.send(f"Kicked **{member}**\nReason: **{reason}**")

    @commands.command(
        help="Bans a member from the server."
    )
    @commands.has_permissions(ban_members=True)
    async def ban(self, ctx, member: discord.Member, *, reason="No reason provided"):
        if member == ctx.author:
            await ctx.send("You cannot ban yourself.")
            return

        if member == ctx.guild.me:
            await ctx.send("I cannot ban myself.")
            return

        await member.ban(reason=reason)
        await ctx.send(f"Banned **{member}**\nReason: **{reason}**")

    @commands.command(
        help="Unbans a user by username and discriminator, like User#1234."
    )
    @commands.has_permissions(ban_members=True)
    async def unban(self, ctx, *, member_name):
        banned_users = [entry async for entry in ctx.guild.bans()]

        for ban_entry in banned_users:
            user = ban_entry.user
            if str(user) == member_name:
                await ctx.guild.unban(user)
                await ctx.send(f"Unbanned **{user}**")
                return

        await ctx.send("That banned user was not found.")

    @commands.command(
        help="Locks the current channel so regular members cannot send messages."
    )
    @commands.has_permissions(manage_channels=True)
    async def lock(self, ctx):
        overwrite = ctx.channel.overwrites_for(ctx.guild.default_role)
        overwrite.send_messages = False
        await ctx.channel.set_permissions(ctx.guild.default_role, overwrite=overwrite)
        await ctx.send("This channel is now locked.")

    @commands.command(
        help="Unlocks the current channel so regular members can send messages again."
    )
    @commands.has_permissions(manage_channels=True)
    async def unlock(self, ctx):
        overwrite = ctx.channel.overwrites_for(ctx.guild.default_role)
        overwrite.send_messages = True
        await ctx.channel.set_permissions(ctx.guild.default_role, overwrite=overwrite)
        await ctx.send("This channel is now unlocked.")

    @clear.error
    @kick.error
    @ban.error
    @unban.error
    @lock.error
    @unlock.error
    async def mod_command_error(self, ctx, error):
        if isinstance(error, commands.MissingPermissions):
            await ctx.send("You do not have permission to use that command.")
        elif isinstance(error, commands.MissingRequiredArgument):
            await ctx.send("You are missing a required argument for that command.")
        elif isinstance(error, commands.BadArgument):
            await ctx.send("That member or value could not be found.")
        else:
            await ctx.send("That command could not be completed.")

async def setup(bot):
    await bot.add_cog(Moderation(bot))
