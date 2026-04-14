import os
import json
import random
import re
import asyncio
from pathlib import Path
from datetime import datetime, timedelta, timezone
from urllib.parse import urlparse

import discord
from discord.ext import commands

try:
    import yt_dlp
except ImportError:
    yt_dlp = None

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

print("SPRINGBOT SAFE BUILD ACTIVE")

TOKEN = os.getenv("DISCORD_TOKEN")
PREFIX = "!"
FFMPEG_PATH = os.getenv("FFMPEG_PATH", "ffmpeg")

CONFIG_FILE = Path("springbot_config.json")
ECONOMY_FILE = Path("springbot_economy.json")

DEFAULT_WELCOME_MESSAGES = [
    "🌸 Welcome to the server, {member.mention}! SpringBot is glad you're here.",
    "🌿 A new member has joined: {member.mention}. Welcome in.",
    "☀️ Everybody welcome {member.mention} to the server.",
    "🌷 Fresh energy just arrived. Welcome, {member.mention}.",
]

DEFAULT_GOODBYE_MESSAGES = [
    "🍃 {member} has left the server.",
    "🌙 Goodbye, {member}.",
    "🌧️ {member} has departed. SpringBot will remember you.",
    "🌸 {member} left the garden.",
]

DEFAULT_CONFIG = {
    "welcome_channel": None,
    "goodbye_channel": None,
    "welcome_messages": DEFAULT_WELCOME_MESSAGES,
    "goodbye_messages": DEFAULT_GOODBYE_MESSAGES,
}

DEFAULT_ECONOMY = {
    "users": {}
}

SPRINGBOT_RULES = [
    "Be respectful to everyone.",
    "No hate speech, racism, or harassment.",
    "No spam or excessive self-promotion.",
    "Keep content in the correct channels.",
    "Use common sense and listen to staff.",
]

ROAST_LINES = [
    "{target.mention}, you bring the same energy as a 2% phone battery.",
    "{target.mention}, even your shadow tries to avoid being seen with you.",
    "{target.mention}, you are proof that auto-correct gives up sometimes.",
    "{target.mention}, your Wi-Fi signal has more personality than you.",
]

EIGHT_BALL_ANSWERS = [
    "Yes.",
    "No.",
    "Definitely.",
    "Absolutely not.",
    "Ask again later.",
    "Without a doubt.",
    "Very unlikely.",
    "Signs point to yes.",
]

YTDL_FORMAT_OPTIONS = {
    "format": "bestaudio/best",
    "noplaylist": True,
    "quiet": True,
    "no_warnings": True,
    "source_address": "0.0.0.0",
    "extract_flat": False,
    "ignoreconfig": True,
    "default_search": "scsearch1",
}

FFMPEG_OPTIONS = {
    "before_options": "-reconnect 1 -reconnect_streamed 1 -reconnect_delay_max 5",
    "options": "-vn",
}

START_TIME = datetime.now(timezone.utc)


def load_json_file(path: Path, default_data: dict) -> dict:
    if not path.exists():
        path.write_text(json.dumps(default_data, indent=4), encoding="utf-8")
        return json.loads(json.dumps(default_data))
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return json.loads(json.dumps(default_data))


def save_json_file(path: Path, data: dict) -> None:
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=4)


def load_config() -> dict:
    data = load_json_file(CONFIG_FILE, DEFAULT_CONFIG)
    for key, value in DEFAULT_CONFIG.items():
        if key not in data:
            data[key] = value
    return data


def save_config(data: dict) -> None:
    save_json_file(CONFIG_FILE, data)


def load_economy() -> dict:
    data = load_json_file(ECONOMY_FILE, DEFAULT_ECONOMY)
    data.setdefault("users", {})
    return data


def save_economy(data: dict) -> None:
    save_json_file(ECONOMY_FILE, data)


config = load_config()
economy = load_economy()

intents = discord.Intents.default()
intents.message_content = True
intents.members = True
intents.voice_states = True

bot = commands.Bot(command_prefix=PREFIX, intents=intents, help_command=None)


class GuildMusicState:
    def __init__(self):
        self.queue = []
        self.now_playing = None
        self.text_channel_id = None
        self.lock = asyncio.Lock()


music_states = {}


def get_music_state(guild_id: int) -> GuildMusicState:
    if guild_id not in music_states:
        music_states[guild_id] = GuildMusicState()
    return music_states[guild_id]


def get_user_record(user_id: int) -> dict:
    user_key = str(user_id)
    users = economy.setdefault("users", {})
    if user_key not in users:
        users[user_key] = {
            "wallet": 0,
            "last_daily": None,
        }
    return users[user_key]


def get_welcome_channel(guild: discord.Guild):
    channel_id = config.get("welcome_channel")
    return guild.get_channel(channel_id) if channel_id else None


def get_goodbye_channel(guild: discord.Guild):
    channel_id = config.get("goodbye_channel")
    return guild.get_channel(channel_id) if channel_id else None


def format_uptime() -> str:
    delta = datetime.now(timezone.utc) - START_TIME
    total_seconds = int(delta.total_seconds())
    days, rem = divmod(total_seconds, 86400)
    hours, rem = divmod(rem, 3600)
    minutes, seconds = divmod(rem, 60)
    return f"{days}d {hours}h {minutes}m {seconds}s"


def build_help_embed() -> discord.Embed:
    embed = discord.Embed(
        title="🌸 SpringBot Commands",
        description="Only working commands are shown here