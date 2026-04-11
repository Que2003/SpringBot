import os
import discord
from discord.ext import commands
from dotenv import load_dotenv
import asyncio

load_dotenv()

TOKEN = os.getenv("DISCORD_TOKEN")
PREFIX = "!"

if not TOKEN:
    raise RuntimeError("Missing DISCORD_TOKEN")

intents = discord.Intents.default()
intents.message_content = True
intents.guilds = True
intents.members = True

bot = commands.Bot(command_prefix=PREFIX, intents=intents)

EXTENSIONS = [
    "cogs.basic",
    "cogs.fun",
    "cogs.utility",
    "cogs.moderation",
    "cogs.education",
    "cogs.security",
    "cogs.history",
]

@bot.event
async def on_ready():
    print(f"Logged in as {bot.user}")

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
    asyncio.run(main())
