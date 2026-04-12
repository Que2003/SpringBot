import os
import json
import random
import discord
from discord.ext import commands


class Welcome(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.file_path = "welcome_settings.json"
        self.data = self.load_data()

    def default_data(self):
        return {}

    def default_guild_settings(self):
        return {
            "channel_id": 0,
            "welcome_enabled": False,
            "leave_enabled": False,
            "welcome_messages": [
                "Welcome {mention} to **{server}**. You are member **#{count}**.",
                "Everybody welcome {mention} to **{server}**.",
                "{mention} just joined **{server}**. Show some love.",
                "A wild {mention} appeared in **{server}**.",
                "Glad to have you here, {mention}. Welcome to **{server}**.",
                "{mention} has entered the server. Let the chaos begin.",
                "Welcome in, {mention}. **{server}** just got better.",
                "{mention} pulled up to **{server}**."
            ],
            "leave_messages": [
                "**{user}** left **{server}**. We now have **{count}** members.",
                "{user} has left the building.",
                "**{user}** dipped from **{server}**.",
                "{user} is gone. The server will remember this.",
                "**{user}** left **{server}**. That is tough.",
                "{user} checked out. We are now at **{count}** members.",
                "**{user}** is out. Onward we go.",
                "{user} left **{server}**. Another one bites the dust."
            ]
        }

    def load_data(self):
        if not os.path.exists(self.file_path):
            return self.default_data()

        try:
            with open(self.file_path, "r", encoding="utf-8") as f:
                data = json.load(f)

            if isinstance(data, dict):
                return data

            return self.default_data()
        except Exception:
            return self.default_data()

    def save_data(self):
        with open(self.file_path, "w", encoding="utf-8") as f:
            json.dump(self.data, f, indent=2)

    def get_guild_settings(self, guild_id: int):
        guild_id = str(guild_id)

        if guild_id not in self.data:
            self.data[guild_id] = self.default_guild_settings()

        settings = self.data[guild_id]
        defaults = self.default_guild_settings()

        for key, value in defaults.items():
            settings.setdefault(key, value)

        return settings

    def get_channel(self, guild: discord.Guild):
        settings = self.get_guild_settings(guild.id)
        channel_id = int(settings.get("channel_id", 0) or 0)

        if not channel_id:
            return None

        return guild.get_channel(channel_id)

    def format_message(self, template: str, member: discord.Member):
        return template.format(
            mention=member.mention,
            user=str(member),
            name=member.display_name,
            server=member.guild.name,
            count=member.guild.member_count
        )

    @commands.Cog.listener()
    async def on_member_join(self, member: discord.Member):
        settings = self.get_guild_settings(member.guild.id)

        if not settings.get("welcome_enabled", False):
            return

        channel = self.get_channel(member.guild)
        if channel is None:
            return

        messages = settings.get("welcome_messages", [])
        if not messages:
            return

        template = random.choice(messages)
        message = self.format_message(template, member)

        embed = discord.Embed(
            title="Member Joined",
            description=message,
            color=discord.Color.green()
        )

        if member.display_avatar:
            embed.set_thumbnail(url=member.display_avatar.url)

        await channel.send(embed=embed)

    @commands.Cog.listener()
    async def on_member_remove(self, member: discord.Member):
        settings = self.get_guild_settings(member.guild.id)

        if not settings.get("leave_enabled", False):
            return

        channel = self.get_channel(member.guild)
        if channel is None:
            return

        messages = settings.get("leave_messages", [])
        if not messages:
            return

        template = random.choice(messages)
        message = self.format_message(template, member)

        embed = discord.Embed(
            title="Member Left",
            description=message,
            color=discord.Color.red()
        )

        if member.display_avatar:
            embed.set_thumbnail(url=member.display_avatar.url)

        await channel.send(embed=embed)

    @commands.command(help="Set this channel as the welcome/leave channel.")
    @commands.has_permissions(manage_guild=True)
    async def setwelcomechannel(self, ctx):
        settings = self.get_guild_settings(ctx.guild.id)
        settings["channel_id"] = ctx.channel.id
        self.save_data()
        await ctx.send(f"This channel is now the welcome/leave channel.\nChannel ID: **{ctx.channel.id}**")

    @commands.command(help="Turn welcome messages on.")
    @commands.has_permissions(manage_guild=True)
    async def welcomeon(self, ctx):
        settings = self.get_guild_settings(ctx.guild.id)
        settings["welcome_enabled"] = True
        self.save_data()
        await ctx.send("Welcome messages are now **ON**.")

    @commands.command(help="Turn welcome messages off.")
    @commands.has_permissions(manage_guild=True)
    async def welcomeoff(self, ctx):
        settings = self.get_guild_settings(ctx.guild.id)
        settings["welcome_enabled"] = False
        self.save_data()
        await ctx.send("Welcome messages are now **OFF**.")

    @commands.command(help="Turn leave messages on.")
    @commands.has_permissions(manage_guild=True)
    async def leaveon(self, ctx):
        settings = self.get_guild_settings(ctx.guild.id)
        settings["leave_enabled"] = True
        self.save_data()
        await ctx.send("Leave messages are now **ON**.")

    @commands.command(help="Turn leave messages off.")
    @commands.has_permissions(manage_guild=True)
    async def leaveoff(self, ctx):
        settings = self.get_guild_settings(ctx.guild.id)
        settings["leave_enabled"] = False
        self.save_data()
        await ctx.send("Leave messages are now **OFF**.")

    @commands.command(help="Add a custom welcome message. Use {mention}, {user}, {name}, {server}, {count}")
    @commands.has_permissions(manage_guild=True)
    async def addwelcome(self, ctx, *, message: str):
        settings = self.get_guild_settings(ctx.guild.id)
        settings["welcome_messages"].append(message)
        self.save_data()
        await ctx.send("Added a new welcome message.")

    @commands.command(help="Add a custom leave message. Use {mention}, {user}, {name}, {server}, {count}")
    @commands.has_permissions(manage_guild=True)
    async def addleave(self, ctx, *, message: str):
        settings = self.get_guild_settings(ctx.guild.id)
        settings["leave_messages"].append(message)
        self.save_data()
        await ctx.send("Added a new leave message.")

    @commands.command(help="List all welcome messages.")
    @commands.has_permissions(manage_guild=True)
    async def listwelcomes(self, ctx):
        settings = self.get_guild_settings(ctx.guild.id)
        messages = settings.get("welcome_messages", [])

        if not messages:
            await ctx.send("There are no welcome messages.")
            return

        lines = [f"{i}. {msg}" for i, msg in enumerate(messages, start=1)]
        output = "\n".join(lines)

        if len(output) > 1900:
            output = output[:1900] + "..."

        await ctx.send(f"**Welcome Messages**\n{output}")

    @commands.command(help="List all leave messages.")
    @commands.has_permissions(manage_guild=True)
    async def listleaves(self, ctx):
        settings = self.get_guild_settings(ctx.guild.id)
        messages = settings.get("leave_messages", [])

        if not messages:
            await ctx.send("There are no leave messages.")
            return

        lines = [f"{i}. {msg}" for i, msg in enumerate(messages, start=1)]
        output = "\n".join(lines)

        if len(output) > 1900:
            output = output[:1900] + "..."

        await ctx.send(f"**Leave Messages**\n{output}")

    @commands.command(help="Remove a welcome message by number.")
    @commands.has_permissions(manage_guild=True)
    async def removewelcome(self, ctx, index: int):
        settings = self.get_guild_settings(ctx.guild.id)
        messages = settings.get("welcome_messages", [])

        if index < 1 or index > len(messages):
            await ctx.send("That welcome message number does not exist.")
            return

        removed = messages.pop(index - 1)
        self.save_data()
        await ctx.send(f"Removed welcome message:\n`{removed}`")

    @commands.command(help="Remove a leave message by number.")
    @commands.has_permissions(manage_guild=True)
    async def removeleave(self, ctx, index: int):
        settings = self.get_guild_settings(ctx.guild.id)
        messages = settings.get("leave_messages", [])

        if index < 1 or index > len(messages):
            await ctx.send("That leave message number does not exist.")
            return

        removed = messages.pop(index - 1)
        self.save_data()
        await ctx.send(f"Removed leave message:\n`{removed}`")

    @commands.command(help="Preview a random welcome message.")
    async def testwelcome(self, ctx):
        settings = self.get_guild_settings(ctx.guild.id)
        messages = settings.get("welcome_messages", [])

        if not messages:
            await ctx.send("There are no welcome messages set.")
            return

        template = random.choice(messages)
        message = self.format_message(template, ctx.author)

        embed = discord.Embed(
            title="Welcome Preview",
            description=message,
            color=discord.Color.green()
        )

        if ctx.author.display_avatar:
            embed.set_thumbnail(url=ctx.author.display_avatar.url)

        await ctx.send(embed=embed)

    @commands.command(help="Preview a random leave message.")
    async def testleave(self, ctx):
        settings = self.get_guild_settings(ctx.guild.id)
        messages = settings.get("leave_messages", [])

        if not messages:
            await ctx.send("There are no leave messages set.")
            return

        template = random.choice(messages)
        message = self.format_message(template, ctx.author)

        embed = discord.Embed(
            title="Leave Preview",
            description=message,
            color=discord.Color.red()
        )

        if ctx.author.display_avatar:
            embed.set_thumbnail(url=ctx.author.display_avatar.url)

        await ctx.send(embed=embed)

    @commands.command(help="Show current welcome settings.")
    async def welcomestatus(self, ctx):
        settings = self.get_guild_settings(ctx.guild.id)
        await ctx.send(
            f"Welcome channel ID: **{settings.get('channel_id', 0)}**\n"
            f"Welcome enabled: **{settings.get('welcome_enabled', False)}**\n"
            f"Leave enabled: **{settings.get('leave_enabled', False)}**\n"
            f"Welcome messages: **{len(settings.get('welcome_messages', []))}**\n"
            f"Leave messages: **{len(settings.get('leave_messages', []))}**"
        )

    @commands.command(help="Show all welcome/leave commands.")
    async def welcomehelp(self, ctx):
        await ctx.send(
            "**Welcome Commands**\n"
            "!setwelcomechannel\n"
            "!welcomeon\n"
            "!welcomeoff\n"
            "!leaveon\n"
            "!leaveoff\n"
            "!addwelcome <message>\n"
            "!addleave <message>\n"
            "!listwelcomes\n"
            "!listleaves\n"
            "!removewelcome <number>\n"
            "!removeleave <number>\n"
            "!testwelcome\n"
            "!testleave\n"
            "!welcomestatus\n"
            "!welcomehelp\n\n"
            "Variables you can use in messages:\n"
            "{mention} {user} {name} {server} {count}"
        )


async def setup(bot):
    await bot.add_cog(Welcome(bot))