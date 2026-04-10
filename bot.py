import os
import logging
import asyncio
import discord
from discord.ext import commands
from dotenv import load_dotenv

load_dotenv()

TOKEN = os.getenv("DISCORD_TOKEN", "").strip()
PREFIX = os.getenv("BOT_PREFIX", "!")
STATUS_TEXT = os.getenv("STATUS_TEXT", "SpringBot Realtime | !help")
WELCOME_CHANNEL_ID = int(os.getenv("WELCOME_CHANNEL_ID", "0") or 0)

if not TOKEN:
    raise RuntimeError("Missing DISCORD_TOKEN")

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s"
)
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
    "cogs.information",
    "cogs.news",
    "cogs.music",
    "cogs.study",
]

bot = commands.Bot(command_prefix=PREFIX, intents=intents, help_command=None, case_insensitive=True)
bot.welcome_channel_id = WELCOME_CHANNEL_ID

@bot.event
async def on_ready():
    log.info("Logged in as %s", bot.user)
    await bot.change_presence(activity=discord.Game(name=STATUS_TEXT))

async def load_extensions():
    for ext in EXTENSIONS:
        await bot.load_extension(ext)
        log.info("Loaded extension: %s", ext)

async def main():
    async with bot:
        await load_extensions()
        await bot.start(TOKEN)

if __name__ == "__main__":
    asyncio.run(main())
