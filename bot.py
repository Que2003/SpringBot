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

intents = discord.Intents.default()
intents.message_content = True
intents.guilds = True
intents.members = True

bot = commands.Bot(
    command_prefix=PREFIX,
    intents=intents,
    help_command=None,
    case_insensitive=True
)

@bot.event
async def on_ready():
    print(f"Logged in as {bot.user}")

@bot.command()
async def ping(ctx):
    await ctx.send("Pong!")

@bot.command()
async def hello(ctx):
    await ctx.send("Hey, I'm online.")

@bot.command()
async def helpme(ctx):
    await ctx.send("Commands: !ping, !hello, !helpme")

bot.run(TOKEN)
