import os
import logging
import discord
from discord.ext import commands
from dotenv import load_dotenv

load_dotenv()

TOKEN = os.getenv("DISCORD_TOKEN", "").strip()
PREFIX = os.getenv("BOT_PREFIX", "!")

if not TOKEN:
    raise RuntimeError("Missing DISCORD_TOKEN")

logging.basicConfig(level=logging.INFO)
log = logging.getLogger("springbot")

intents = discord.Intents.default()
intents.message_content = True
intents.guilds = True
intents.members = True
intents.voice_states = True

EXTENSIONS = [
    "cogs.basic",
    "cogs.fun",
    "cogs.utility",
    "cogs.moderation",
    "cogs.education",
    "cogs.empathy",
    "cogs.writing",
]

bot = commands.Bot(
    command_prefix=PREFIX,
    intents=intents,
    help_command=None,
    case_insensitive=True
)

@bot.event
async def on_ready():
    print(f"Logged in as {bot.user}")

async def load_extensions():
    for ext in EXTENSIONS:
        try:
            await bot.load_extension(ext)
            print(f"Loaded: {ext}")
        except Exception as e:
            print(f"Failed to load {ext}: {e}")

@bot.command()
async def ping(ctx):
    await ctx.send("Pong!")

async def main():
    async with bot:
        await load_extensions()
        await bot.start(TOKEN)

if __name__ == "__main__":
    import asyncio
    asyncio.run(main())
