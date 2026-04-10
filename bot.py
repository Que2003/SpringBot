{
  "chapter1": {import os
import logging
import asyncio
import discord
from discord.ext import commands
from dotenv import load_dotenv

print("BOT FILE STARTING")

load_dotenv()

TOKEN = os.getenv("DISCORD_TOKEN", "").strip()
PREFIX = os.getenv("BOT_PREFIX", "!")
STATUS_TEXT = os.getenv("STATUS_TEXT", "SpringBot Realtime | !help")

print("TOKEN EXISTS:", bool(TOKEN))

if not TOKEN:
    raise RuntimeError("Missing DISCORD_TOKEN")

logging.basicConfig(level=logging.INFO)

intents = discord.Intents.default()
intents.message_content = True
intents.guilds = True
intents.members = True
intents.voice_states = True

bot = commands.Bot(command_prefix=PREFIX, intents=intents, help_command=None)

@bot.event
async def on_ready():
    print(f"LOGGED IN AS: {bot.user}")
    await bot.change_presence(activity=discord.Game(name=STATUS_TEXT))

@bot.command()
async def ping(ctx):
    await ctx.send("Pong!")

async def main():
    async with bot:
        await bot.start(TOKEN)

if __name__ == "__main__":
    asyncio.run(main())
