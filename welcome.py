import random
import discord
from discord.ext import commands

WELCOME_CHANNEL_NAME = "general"  # change this to your channel name if needed

WELCOME_MESSAGES = [
    "Welcome {mention} to the server.",
    "Glad you made it in, {mention}.",
    "Everybody welcome {mention}.",
    "{mention} just joined. Try not to scare them away.",
    "Welcome in, {mention}.",
    "A new challenger appears: {mention}.",
    "{mention} has entered the server.",
]

LEAVE_MESSAGES = [
    "{name} has left the server.",
    "{name} dipped.",
    "{name} has exited the chat permanently.",
    "{name} left the server. That is tough.",
    "{name} vanished into the void.",
]


class Welcome(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    def get_welcome_channel(self, guild: discord.Guild):
        # First try system channel
        if guild.system_channel and guild.system_channel.permissions_for(guild.me).send_messages:
            return guild.system_channel

        # Then try channel by name
        for channel in guild.text_channels:
            if channel.name.lower() == WELCOME_CHANNEL_NAME.lower():
                if channel.permissions_for(guild.me).send_messages:
                    return channel

        # Then try first writable text channel
        for channel in guild.text_channels:
            if channel.permissions_for(guild.me).send_messages:
                return channel

        return None

    @commands.Cog.listener()
    async def on_member_join(self, member: discord.Member):
        channel = self.get_welcome_channel(member.guild)
        if channel:
            msg = random.choice(WELCOME_MESSAGES).format(mention=member.mention)
            await channel.send(msg)

    @commands.Cog.listener()
    async def on_member_remove(self, member: discord.Member):
        channel = self.get_welcome_channel(member.guild)
        if channel:
            msg = random.choice(LEAVE_MESSAGES).format(name=member.name)
            await channel.send(msg)


async def setup(bot):
    await bot.add_cog(Welcome(bot))