from __future__ import annotations

import asyncio
import logging
import os
from datetime import datetime, timezone

import discord
from discord.ext import commands
from dotenv import load_dotenv

from storage import ensure_data_files

load_dotenv()

TOKEN = os.getenv("DISCORD_TOKEN", "").strip()
PREFIX = os.getenv("BOT_PREFIX", "!")
STATUS_TEXT = os.getenv(
    "STATUS_TEXT",
    "SpringBot | Intelligent. Fast. A little sarcastic.",
)
WELCOME_CHANNEL_ID = int(os.getenv("WELCOME_CHANNEL_ID", "0") or 0)

if not TOKEN:
    raise RuntimeError("Missing DISCORD_TOKEN")

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
)
log = logging.getLogger("springbot")

intents = discord.Intents.default()
intents.message_content = True
intents.guilds = True
intents.members = True
intents.voice_states = True
intents.messages = True
intents.reactions = True

EXTENSIONS = [
    "cogs.basic",
    "cogs.moderation",
    "cogs.fun",
    "cogs.utility",
    "cogs.information",
    "cogs.news",
    "cogs.music",
    "cogs.education",
    "cogs.empathy",
    "cogs.writing",
    "cogs.study",
    "cogs.economy",
    "cogs.assistant",
    "cogs.servertools",
    "cogs.live",
]


class SpringBot(commands.Bot):
    def __init__(self) -> None:
        super().__init__(
            command_prefix=commands.when_mentioned_or(PREFIX),
            intents=intents,
            help_command=None,
            case_insensitive=True,
        )
        self.welcome_channel_id = WELCOME_CHANNEL_ID
        self.started_at = datetime.now(timezone.utc)
        self.command_docs: dict[str, str] = {}

    async def setup_hook(self) -> None:
        ensure_data_files()
        

    async def on_ready(self) -> None:
        await self.change_presence(activity=discord.Game(name=STATUS_TEXT))
        log.info("Logged in as %s", self.user)
        log.info("Connected to %s guild(s).", len(self.guilds))


bot = SpringBot()


async def main() -> None:
    async with bot:
        await bot.start(TOKEN)


if __name__ == "__main__":
    asyncio.run(main())
