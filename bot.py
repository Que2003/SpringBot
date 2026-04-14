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

print("SPRINGBOT ADVANCED BUILD ACTIVE")

TOKEN = os.getenv("DISCORD_TOKEN")
PREFIX = "!"
FFMPEG_PATH = os.getenv("FFMPEG_PATH", "ffmpeg")

CONFIG_FILE = Path("springbot_config.json")
ECONOMY_FILE = Path("springbot_economy.json")
MOD_FILE = Path("springbot_mod.json")

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
    "autorole_id": None,
    "reaction_roles": []
}

DEFAULT_ECONOMY = {
    "users": {}
}

DEFAULT_MOD = {
    "warnings": {}
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


def load_economy() -> dict:
    data = load_json_file(ECONOMY_FILE, DEFAULT_ECONOMY)
    data.setdefault("users", {})
    return data


def load_mod_data() -> dict:
    data = load_json_file(MOD_FILE, DEFAULT_MOD)
    data.setdefault("warnings", {})
    return data


def save_all() -> None:
    save_json_file(CONFIG_FILE, config)
    save_json_file(ECONOMY_FILE, economy)
    save_json_file(MOD_FILE, mod_data)


config = load_config()
economy = load_economy()
mod_data = load_mod_data()

intents = discord.Intents.default()
intents.message_content = True
intents.members = True
intents.voice_states = True
intents.guilds = True
intents.reactions = True

bot = commands.Bot(command_prefix=PREFIX, intents=intents, help_command=None)


class GuildMusicState:
    def __init__(self):
        self.queue = []
        self.now_playing = None
        self.text_channel_id = None
        self.lock = asyncio.Lock()
        self.loop_enabled = False


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


def get_warning_key(guild_id: int, user_id: int) -> str:
    return f"{guild_id}:{user_id}"


def get_warnings(guild_id: int, user_id: int) -> list:
    warnings = mod_data.setdefault("warnings", {})
    key = get_warning_key(guild_id, user_id)
    warnings.setdefault(key, [])
    return warnings[key]


def get_welcome_channel(guild: discord.Guild):
    channel_id = config.get("welcome_channel")
    return guild.get_channel(channel_id) if channel_id else None


def get_goodbye_channel(guild: discord.Guild):
    channel_id = config.get("goodbye_channel")
    return guild.get_channel(channel_id) if channel_id else None


def get_autorole(guild: discord.Guild):
    role_id = config.get("autorole_id")
    return guild.get_role(role_id) if role_id else None


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
        description="Only working commands are shown here.",
        color=discord.Color.green()
    )

    embed.add_field(
        name="Core",
        value="`!help`\n`!about`\n`!ping`\n`!uptime`\n`!prefix`",
        inline=False
    )

    embed.add_field(
        name="Server",
        value="`!rules`\n`!welcome`\n`!goodbye`\n`!setwelcome`\n`!setgoodbye`\n`!testwelcome`\n`!testgoodbye`\n`!autorole`\n`!reactionrole`",
        inline=False
    )

    embed.add_field(
        name="Utility",
        value="`!userinfo`\n`!serverinfo`\n`!membercount`\n`!avatar`",
        inline=False
    )

    embed.add_field(
        name="Fun",
        value="`!roast`\n`!8ball`\n`!coinflip`\n`!roll`",
        inline=False
    )

    embed.add_field(
        name="Economy",
        value="`!balance`\n`!daily`",
        inline=False
    )

    embed.add_field(
        name="Voice / Music",
        value="`!join`\n`!leave`\n`!play <soundcloud link or song>`\n`!pause`\n`!resume`\n`!skip`\n`!stop`\n`!queue`\n`!shuffle`\n`!loop`\n`!nowplaying`",
        inline=False
    )

    embed.add_field(
        name="Moderation",
        value="`!ban`\n`!kick`\n`!timeout`\n`!untimeout`\n`!warn`\n`!warnings`\n`!clearwarns`\n`!purge`\n`!slowmode`\n`!lock`\n`!unlock`",
        inline=False
    )

    embed.add_field(
        name="AI",
        value="`!ask`",
        inline=False
    )

    return embed


async def set_welcome_channel_logic(ctx, channel: discord.TextChannel) -> None:
    config["welcome_channel"] = channel.id
    save_all()
    await ctx.send(f"✅ Welcome channel set to {channel.mention}")


async def set_goodbye_channel_logic(ctx, channel: discord.TextChannel) -> None:
    config["goodbye_channel"] = channel.id
    save_all()
    await ctx.send(f"✅ Goodbye channel set to {channel.mention}")


def is_url(text: str) -> bool:
    try:
        parsed = urlparse(text)
        return parsed.scheme in ("http", "https") and bool(parsed.netloc)
    except Exception:
        return False


def is_soundcloud_url(text: str) -> bool:
    try:
        host = urlparse(text).netloc.lower()
        return "soundcloud.com" in host or "snd.sc" in host
    except Exception:
        return False


def normalize_emoji(emoji: str) -> str:
    return emoji.strip()


async def join_author_voice_channel(ctx) -> discord.VoiceClient | None:
    if not ctx.author.voice or not ctx.author.voice.channel:
        await ctx.send("Join a voice channel first, then use this command.")
        return None

    voice_channel = ctx.author.voice.channel
    voice_client = ctx.guild.voice_client

    me = ctx.guild.me or ctx.guild.get_member(bot.user.id)
    permissions = voice_channel.permissions_for(me)

    if not permissions.connect:
        await ctx.send("I do not have permission to connect to that voice channel.")
        return None

    if not permissions.speak:
        await ctx.send("I do not have permission to speak in that voice channel.")
        return None

    try:
        if voice_client and voice_client.is_connected():
            if voice_client.channel != voice_channel:
                await voice_client.move_to(voice_channel)
            return voice_client
        return await voice_channel.connect()
    except Exception as e:
        await ctx.send(f"Voice error: {e}")
        return None


async def extract_soundcloud_song_info(search: str) -> dict:
    if yt_dlp is None:
        raise RuntimeError("yt-dlp is not installed.")

    loop = asyncio.get_running_loop()

    def _extract():
        target = search.strip()
        with yt_dlp.YoutubeDL(YTDL_FORMAT_OPTIONS) as ydl:
            if is_url(target):
                if not is_soundcloud_url(target):
                    raise RuntimeError("Only SoundCloud links are allowed.")
                info = ydl.extract_info(target, download=False)
            else:
                info = ydl.extract_info(target, download=False)

            if info is None:
                return None

            if "entries" in info:
                entries = info.get("entries") or []
                if not entries:
                    return None
                info = entries[0]

            webpage_url = info.get("webpage_url") or ""
            extractor = str(info.get("extractor", "")).lower()
            extractor_key = str(info.get("extractor_key", "")).lower()

            valid_sc = (
                "soundcloud" in extractor
                or "soundcloud" in extractor_key
                or is_soundcloud_url(webpage_url)
            )
            if not valid_sc:
                raise RuntimeError(f"Blocked non-SoundCloud result: {extractor_key or extractor}")

            return {
                "title": info.get("title", "Unknown title"),
                "url": info.get("url"),
                "webpage_url": webpage_url,
                "duration": info.get("duration"),
                "uploader": info.get("uploader", "Unknown uploader"),
                "thumbnail": info.get("thumbnail"),
                "requested_by": None,
            }

    return await loop.run_in_executor(None, _extract)


def format_duration(seconds: int | None) -> str:
    if not seconds:
        return "Unknown"
    minutes, seconds = divmod(int(seconds), 60)
    hours, minutes = divmod(minutes, 60)
    return f"{hours}:{minutes:02d}:{seconds:02d}" if hours else f"{minutes}:{seconds:02d}"


async def play_next_song(guild: discord.Guild):
    state = get_music_state(guild.id)
    voice_client = guild.voice_client

    if not voice_client or not voice_client.is_connected():
        state.now_playing = None
        return

    async with state.lock:
        if state.loop_enabled and state.now_playing:
            song = state.now_playing
        else:
            if not state.queue:
                state.now_playing = None
                return
            song = state.queue.pop(0)
            state.now_playing = song

    source = discord.FFmpegPCMAudio(
        song["url"],
        executable=FFMPEG_PATH,
        **FFMPEG_OPTIONS
    )

    def after_playing(error):
        if error:
            print(f"Playback error: {error}")
        future = asyncio.run_coroutine_threadsafe(play_next_song(guild), bot.loop)
        try:
            future.result()
        except Exception as exc:
            print(f"Queue advance error: {exc}")

    voice_client.play(source, after=after_playing)

    if state.text_channel_id:
        text_channel = guild.get_channel(state.text_channel_id)
        if text_channel:
            embed = discord.Embed(title="🎶 Now Playing", description=f"**{song['title']}**", color=discord.Color.green())
            embed.add_field(name="Duration", value=format_duration(song.get("duration")), inline=True)
            embed.add_field(name="Uploader", value=song.get("uploader", "Unknown"), inline=True)
            embed.add_field(name="Requested By", value=song["requested_by"].mention, inline=True)
            if song.get("webpage_url"):
                embed.add_field(name="Link", value=song["webpage_url"], inline=False)
            if song.get("thumbnail"):
                embed.set_thumbnail(url=song["thumbnail"])
            await text_channel.send(embed=embed)


@bot.event
async def on_ready():
    print(f"LOGGED IN AS: {bot.user}")
    await bot.change_presence(activity=discord.Game(name="SpringBot | !help"))


@bot.event
async def on_member_join(member: discord.Member):
    channel = get_welcome_channel(member.guild)
    if channel:
        message = random.choice(config.get("welcome_messages", DEFAULT_WELCOME_MESSAGES)).format(member=member)
        await channel.send(message)

    autorole = get_autorole(member.guild)
    if autorole:
        try:
            await member.add_roles(autorole, reason="SpringBot autorole")
        except discord.Forbidden:
            pass


@bot.event
async def on_member_remove(member: discord.Member):
    channel = get_goodbye_channel(member.guild)
    if channel:
        message = random.choice(config.get("goodbye_messages", DEFAULT_GOODBYE_MESSAGES)).format(member=member)
        await channel.send(message)


@bot.event
async def on_raw_reaction_add(payload: discord.RawReactionActionEvent):
    if payload.guild_id is None or payload.user_id == bot.user.id:
        return

    guild = bot.get_guild(payload.guild_id)
    if guild is None:
        return

    member = guild.get_member(payload.user_id)
    if member is None or member.bot:
        return

    emoji_str = str(payload.emoji)

    for entry in config.get("reaction_roles", []):
        if entry["message_id"] == payload.message_id and entry["emoji"] == emoji_str:
            role = guild.get_role(entry["role_id"])
            if role:
                try:
                    await member.add_roles(role, reason="SpringBot reaction role")
                except discord.Forbidden:
                    pass
            break


@bot.event
async def on_raw_reaction_remove(payload: discord.RawReactionActionEvent):
    if payload.guild_id is None:
        return

    guild = bot.get_guild(payload.guild_id)
    if guild is None:
        return

    member = guild.get_member(payload.user_id)
    if member is None or member.bot:
        return

    emoji_str = str(payload.emoji)

    for entry in config.get("reaction_roles", []):
        if entry["message_id"] == payload.message_id and entry["emoji"] == emoji_str:
            role = guild.get_role(entry["role_id"])
            if role:
                try:
                    await member.remove_roles(role, reason="SpringBot reaction role removal")
                except discord.Forbidden:
                    pass
            break


@bot.command(name="help")
async def help_command(ctx):
    await ctx.send(embed=build_help_embed())


@bot.command(name="about")
async def about_command(ctx):
    embed = discord.Embed(
        title="About SpringBot",
        description="SpringBot is a multi-purpose Discord bot with moderation, welcome/goodbye, utility, fun, economy, SoundCloud music, reaction roles, and autoroles.",
        color=discord.Color.green()
    )
    await ctx.send(embed=embed)


@bot.command(name="prefix")
async def prefix_command(ctx):
    await ctx.send(f"My current prefix is `{PREFIX}`")


@bot.command(name="ping")
async def ping_command(ctx):
    latency = round(bot.latency * 1000)
    await ctx.send(f"🏓 Pong: `{latency}ms`")


@bot.command(name="uptime")
async def uptime_command(ctx):
    await ctx.send(f"⏱️ Uptime: **{format_uptime()}**")


@bot.command(name="rules")
async def rules_command(ctx):
    rules_text = "\n".join([f"**{i + 1}.** {rule}" for i, rule in enumerate(SPRINGBOT_RULES)])
    embed = discord.Embed(title="📜 Server Rules", description=rules_text, color=discord.Color.green())
    await ctx.send(embed=embed)


@bot.command(name="welcome")
async def welcome_command(ctx, channel: discord.TextChannel = None):
    if channel is not None:
        if not ctx.author.guild_permissions.administrator:
            await ctx.send("You need administrator permission to set the welcome channel.")
            return
        await set_welcome_channel_logic(ctx, channel)
        return
    current_channel = get_welcome_channel(ctx.guild)
    await ctx.send(f"🌸 Welcome channel is currently set to {current_channel.mention}" if current_channel else f"No welcome channel is set yet. Use `{PREFIX}welcome #channel`.")


@bot.command(name="goodbye")
async def goodbye_command(ctx, channel: discord.TextChannel = None):
    if channel is not None:
        if not ctx.author.guild_permissions.administrator:
            await ctx.send("You need administrator permission to set the goodbye channel.")
            return
        await set_goodbye_channel_logic(ctx, channel)
        return
    current_channel = get_goodbye_channel(ctx.guild)
    await ctx.send(f"🍃 Goodbye channel is currently set to {current_channel.mention}" if current_channel else f"No goodbye channel is set yet. Use `{PREFIX}goodbye #channel`.")


@bot.command(name="setwelcome")
@commands.has_permissions(administrator=True)
async def setwelcome_command(ctx, channel: discord.TextChannel = None):
    channel = channel or ctx.channel
    await set_welcome_channel_logic(ctx, channel)


@bot.command(name="setgoodbye")
@commands.has_permissions(administrator=True)
async def setgoodbye_command(ctx, channel: discord.TextChannel = None):
    channel = channel or ctx.channel
    await set_goodbye_channel_logic(ctx, channel)


@bot.command(name="testwelcome")
@commands.has_permissions(administrator=True)
async def testwelcome_command(ctx):
    message = random.choice(config.get("welcome_messages", DEFAULT_WELCOME_MESSAGES)).format(member=ctx.author)
    await ctx.send(message)


@bot.command(name="testgoodbye")
@commands.has_permissions(administrator=True)
async def testgoodbye_command(ctx):
    message = random.choice(config.get("goodbye_messages", DEFAULT_GOODBYE_MESSAGES)).format(member=ctx.author)
    await ctx.send(message)


@bot.command(name="autorole")
@commands.has_permissions(administrator=True)
async def autorole_command(ctx, *, role_name: str = None):
    if role_name is None:
        role = get_autorole(ctx.guild)
        return await ctx.send(f"Autorole is set to **{role.name}**." if role else "No autorole is set.")

    if role_name.lower() in {"off", "none", "disable"}:
        config["autorole_id"] = None
        save_all()
        return await ctx.send("Autorole disabled.")

    role = discord.utils.get(ctx.guild.roles, name=role_name)
    if role is None:
        return await ctx.send("Role not found.")

    config["autorole_id"] = role.id
    save_all()
    await ctx.send(f"Autorole set to **{role.name}**.")


@bot.command(name="reactionrole")
@commands.has_permissions(administrator=True)
async def reactionrole_command(ctx,