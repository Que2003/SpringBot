import os
import asyncio
import discord
from discord.ext import commands
from dotenv import load_dotenv

load_dotenv()

TOKEN = os.getenv("DISCORD_TOKEN")
PREFIX = os.getenv("BOT_PREFIX", "!")

if not TOKEN:
    raise RuntimeError("Missing DISCORD_TOKEN")

intents = discord.Intents.default()
intents.message_content = True
intents.guilds = True
intents.members = True
intents.voice_states = True

bot = commands.Bot(
    command_prefix=PREFIX,
    intents=intents,
    help_command=None,
    case_insensitive=True
)

EXTENSIONS = [
    "cogs.basic",
    "cogs.fun",
    "cogs.utility",
    "cogs.moderation",
    "cogs.education",
    "cogs.security",
    "cogs.history",
    "cogs.music",
    "cogs.math",
    "cogs.chat",
    "cogs.search",
    "cogs.news",
    "cogs.voicechat",
]

@bot.event
async def on_ready():
    print(f"Logged in as {bot.user} (ID: {bot.user.id})")
    print("SpringBot is online.")

@bot.event
async def on_command_error(ctx, error):
    if isinstance(error, commands.CommandNotFound):
        return
    if isinstance(error, commands.MissingRequiredArgument):
        await ctx.send("You are missing part of that command.")
        return
    if isinstance(error, commands.BadArgument):
        await ctx.send("That argument is invalid.")
        return
    if isinstance(error, commands.MissingPermissions):
        await ctx.send("You do not have permission to use that command.")
        return
    if isinstance(error, commands.BotMissingPermissions):
        await ctx.send("I do not have the required permissions for that command.")
        return

    await ctx.send(f"Command error: {error}")
    print(f"Command error: {error}")

async def load_extensions():
    for ext in EXTENSIONS:
        try:
            await bot.load_extension(ext)
            print(f"Loaded {ext}")
        except Exception as e:
            print(f"FAILED {ext}: {e}")

async def main():
    async with bot:
        await load_extensions()
        await bot.start(TOKEN)

if __name__ == "__main__":
    asyncio.run(main()