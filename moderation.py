import json
import os
from datetime import timedelta

import discord
from discord.ext import commands


class Moderation(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.warn_file = "warnings.json"
        self.warn_data = self.load_warnings()

    def load_warnings(self):
        if not os.path.exists(self.warn_file):
            return {}

        try:
            with open(self.warn_file, "r", encoding="utf-8") as f:
                data = json.load(f)
            if isinstance(data, dict):
                return data
            return {}
        except Exception:
            return {}

    def save_warnings(self):
        with open(self.warn_file, "w", encoding="utf-8") as f:
            json.dump(self.warn_data, f, indent=2)

    def get_guild_warns(self, guild_id):
        guild_id = str(guild_id)
        if guild_id not in self.warn_data:
            self.warn_data[guild_id] = {}
        return self.warn_data[guild_id]

    def get_member_warns(self, guild_id, member_id):
        guild_warns = self.get_guild_warns(guild_id)
        member_id = str(member_id)
        if member_id not in guild_warns:
            guild_warns[member_id] = []
        return guild_warns[member_id]

    def can_target(self, ctx, member: discord.Member):
        if member == ctx.author:
            return False, "You cannot target yourself."

        if member == ctx.guild.me:
            return False, "I cannot target myself."

        if ctx.author != ctx.guild.owner and member.top_role >= ctx.author.top_role:
            return False, "You cannot target someone with an equal or higher role than yours."

        if member.top_role >= ctx.guild.me.top_role:
            return False, "I cannot target that member because their role is equal to or higher than mine."

        return True, None

    @commands.command(help="Delete a number of recent messages. Example: !clear 10")
    @commands.has_permissions(manage_messages=True)
    async def clear(self, ctx, amount: int = 5):
        if amount < 1:
            await ctx.send("You must delete at least 1 message.")
            return

        deleted = await ctx.channel.purge(limit=amount + 1)
        msg = await ctx.send(f"Deleted **{len(deleted) - 1}** message(s).")
        await msg.delete(delay=3)

    @commands.command(help="Kick a member. Example: !kick @user spamming")
    @commands.has_permissions(kick_members=True)
    async def kick(self, ctx, member: discord.Member, *, reason="No reason provided"):
        ok, error = self.can_target(ctx, member)
        if not ok:
            await ctx.send(error)
            return

        await member.kick(reason=reason)
        await ctx.send(f"Kicked {member.mention}\nReason: **{reason}**")

    @commands.command(help="Ban a member. Example: !ban @user repeated abuse")
    @commands.has_permissions(ban_members=True)
    async def ban(self, ctx, member: discord.Member, *, reason="No reason provided"):
        ok, error = self.can_target(ctx, member)
        if not ok:
            await ctx.send(error)
            return

        await member.ban(reason=reason)
        await ctx.send(f"Banned {member.mention}\nReason: **{reason}**")

    @commands.command(help="Unban a user by username#discriminator. Example: !unban User#1234")
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

    @commands.command(help="Timeout a member in minutes. Example: !timeout @user 10 spam")
    @commands.has_permissions(moderate_members=True)
    async def timeout(self, ctx, member: discord.Member, minutes: int, *, reason="No reason provided"):
        ok, error = self.can_target(ctx, member)
        if not ok:
            await ctx.send(error)
            return

        if minutes < 1 or minutes > 40320:
            await ctx.send("Timeout minutes must be between 1 and 40320.")
            return

        until = timedelta(minutes=minutes)
        await member.timeout(until, reason=reason)
        await ctx.send(f"Timed out {member.mention} for **{minutes}** minute(s).\nReason: **{reason}**")

    @commands.command(help="Remove timeout from a member. Example: !untimeout @user")
    @commands.has_permissions(moderate_members=True)
    async def untimeout(self, ctx, member: discord.Member):
        ok, error = self.can_target(ctx, member)
        if not ok:
            await ctx.send(error)
            return

        await member.timeout(None)
        await ctx.send(f"Removed timeout from {member.mention}")

    @commands.command(help="Lock the current channel.")
    @commands.has_permissions(manage_channels=True)
    async def lock(self, ctx):
        overwrite = ctx.channel.overwrites_for(ctx.guild.default_role)
        overwrite.send_messages = False
        await ctx.channel.set_permissions(ctx.guild.default_role, overwrite=overwrite)
        await ctx.send("This channel is now locked.")

    @commands.command(help="Unlock the current channel.")
    @commands.has_permissions(manage_channels=True)
    async def unlock(self, ctx):
        overwrite = ctx.channel.overwrites_for(ctx.guild.default_role)
        overwrite.send_messages = None
        await ctx.channel.set_permissions(ctx.guild.default_role, overwrite=overwrite)
        await ctx.send("This channel is now unlocked.")

    @commands.command(help="Set slowmode in seconds. Example: !slowmode 10")
    @commands.has_permissions(manage_channels=True)
    async def slowmode(self, ctx, seconds: int = 0):
        if seconds < 0 or seconds > 21600:
            await ctx.send("Slowmode must be between 0 and 21600 seconds.")
            return

        await ctx.channel.edit(slowmode_delay=seconds)
        await ctx.send(f"Slowmode set to **{seconds}** second(s).")

    @commands.command(help="Warn a member. Example: !warn @user language")
    @commands.has_permissions(manage_messages=True)
    async def warn(self, ctx, member: discord.Member, *, reason="No reason provided"):
        ok, error = self.can_target(ctx, member)
        if not ok:
            await ctx.send(error)
            return

        warns = self.get_member_warns(ctx.guild.id, member.id)
        warns.append({
            "moderator": str(ctx.author),
            "reason": reason
        })
        self.save_warnings()

        await ctx.send(
            f"Warned {member.mention}\n"
            f"Reason: **{reason}**\n"
            f"Total warnings: **{len(warns)}**"
        )

    @commands.command(help="Show a member's warnings. Example: !warnings @user")
    @commands.has_permissions(manage_messages=True)
    async def warnings(self, ctx, member: discord.Member):
        warns = self.get_member_warns(ctx.guild.id, member.id)

        if not warns:
            await ctx.send(f"{member.mention} has no warnings.")
            return

        lines = []
        for i, warn in enumerate(warns[:10], start=1):
            lines.append(
                f"{i}. **Reason:** {warn.get('reason', 'No reason')}"
                f" | **Moderator:** {warn.get('moderator', 'Unknown')}"
            )

        await ctx.send(
            f"Warnings for {member.mention} (**{len(warns)}** total):\n" + "\n".join(lines)
        )

    @commands.command(help="Clear all warnings for a member. Example: !clearwarnings @user")
    @commands.has_permissions(manage_messages=True)
    async def clearwarnings(self, ctx, member: discord.Member):
        guild_warns = self.get_guild_warns(ctx.guild.id)
        member_id = str(member.id)

        if member_id in guild_warns:
            guild_warns[member_id] = []
            self.save_warnings()
            await ctx.send(f"Cleared all warnings for {member.mention}")
            return

        await ctx.send(f"{member.mention} has no warnings to clear.")

    @commands.command(help="Change a member nickname. Example: !nickname @user NewName")
    @commands.has_permissions(manage_nicknames=True)
    async def nickname(self, ctx, member: discord.Member, *, nickname: str = None):
        ok, error = self.can_target(ctx, member)
        if not ok:
            await ctx.send(error)
            return

        await member.edit(nick=nickname)
        if nickname:
            await ctx.send(f"Changed nickname for {member.mention} to **{nickname}**")
        else:
            await ctx.send(f"Removed nickname for {member.mention}")

    @commands.command(help="Add a role to a member. Example: !addrole @user Members")
    @commands.has_permissions(manage_roles=True)
    async def addrole(self, ctx, member: discord.Member, *, role: discord.Role):
        ok, error = self.can_target(ctx, member)
        if not ok:
            await ctx.send(error)
            return

        if role >= ctx.guild.me.top_role:
            await ctx.send("I cannot assign a role that is equal to or higher than my top role.")
            return

        await member.add_roles(role)
        await ctx.send(f"Added role **{role.name}** to {member.mention}")

    @commands.command(help="Remove a role from a member. Example: !removerole @user Members")
    @commands.has_permissions(manage_roles=True)
    async def removerole(self, ctx, member: discord.Member, *, role: discord.Role):
        ok, error = self.can_target(ctx, member)
        if not ok:
            await ctx.send(error)
            return

        if role >= ctx.guild.me.top_role:
            await ctx.send("I cannot remove a role that is equal to or higher than my top role.")
            return

        await member.remove_roles(role)
        await ctx.send(f"Removed role **{role.name}** from {member.mention}")

    @commands.command(help="Show all moderation commands.")
    async def modhelp(self, ctx):
        await ctx.send(
            "**Super Admin Commands**\n"
            "!clear <amount>\n"
            "!kick @user <reason>\n"
            "!ban @user <reason>\n"
            "!unban User#1234\n"
            "!timeout @user <minutes> <reason>\n"
            "!untimeout @user\n"
            "!lock\n"
            "!unlock\n"
            "!slowmode <seconds>\n"
            "!warn @user <reason>\n"
            "!warnings @user\n"
            "!clearwarnings @user\n"
            "!nickname @user <new name>\n"
            "!addrole @user <role>\n"
            "!removerole @user <role>\n"
            "!modhelp"
        )

    @clear.error
    @kick.error
    @ban.error
    @unban.error
    @timeout.error
    @untimeout.error
    @lock.error
    @unlock.error
    @slowmode.error
    @warn.error
    @warnings.error
    @clearwarnings.error
    @nickname.error
    @addrole.error
    @removerole.error
    async def moderation_error(self, ctx, error):
        if isinstance(error, commands.MissingPermissions):
            await ctx.send("You do not have permission to use that command.")
        elif isinstance(error, commands.BotMissingPermissions):
            await ctx.send("I do not have the required server permissions for that command.")
        elif isinstance(error, commands.MissingRequiredArgument):
            await ctx.send("You are missing a required argument.")
        elif isinstance(error, commands.BadArgument):
            await ctx.send("That member, role, or value could not be found.")
        else:
            await ctx.send(f"Command failed: {error}")


async def setup(bot):
    await bot.add_cog(Moderation(bot))