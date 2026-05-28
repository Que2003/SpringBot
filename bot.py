import asyncio
import json
import os
import random
import re
from datetime import datetime, timedelta, timezone
from pathlib import Path
from urllib.parse import urlparse

import aiohttp
import discord
from discord.ext import commands

try:
    import yt_dlp
except ImportError:
    yt_dlp = None

try:
    import imageio_ffmpeg
except ImportError:
    imageio_ffmpeg = None

try:
    from openai import OpenAI
except ImportError:
    OpenAI = None

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass


TOKEN = os.getenv("DISCORD_TOKEN")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
SPRING_API_URL = os.getenv("SPRING_API_URL", "https://spring-virtual-offiice-pro.com")
PREFIX = os.getenv("BOT_PREFIX", "!")
FFMPEG_PATH = os.getenv("FFMPEG_PATH", "ffmpeg")
if FFMPEG_PATH == "ffmpeg" and imageio_ffmpeg is not None:
    try:
        FFMPEG_PATH = imageio_ffmpeg.get_ffmpeg_exe()
    except Exception:
        FFMPEG_PATH = "ffmpeg"

client = OpenAI(api_key=OPENAI_API_KEY) if OpenAI and OPENAI_API_KEY else None

CONFIG_FILE = Path("springbot_config.json")
DATA_FILE = Path("springbot_data.json")
START_TIME = datetime.now(timezone.utc)

DEFAULT_CONFIG = {
    "welcome_channel": None,
    "goodbye_channel": None,
    "log_channel": None,
    "ticket_category": None,
    "support_role": None,
    "automod_enabled": True,
    "blocked_words": [],
    "block_invites": True,
    "spam_limit": 5,
    "spring_theme": "black",
}

DEFAULT_DATA = {
    "economy": {},
    "warnings": {},
    "reaction_roles": {},
    "tickets": {},
}

RULES = [
    "Be respectful to everyone.",
    "No hate speech, harassment, threats, or targeted bullying.",
    "No spam, scams, raids, or excessive self-promotion.",
    "Keep content in the correct channels.",
    "Listen to staff and use common sense.",
]

EIGHT_BALL = [
    "Yes.",
    "No.",
    "Definitely.",
    "Absolutely not.",
    "Ask again later.",
    "Without a doubt.",
    "Very unlikely.",
    "Signs point to yes.",
]

YTDL_OPTIONS = {
    "format": "bestaudio[ext=m4a]/bestaudio/best",
    "noplaylist": True,
    "quiet": True,
    "no_warnings": True,
    "source_address": "0.0.0.0",
    "ignoreconfig": True,
    "default_search": "ytsearch1",
    "extractor_args": {"youtube": {"player_client": ["android", "web"]}},
}

FFMPEG_OPTIONS = {
    "before_options": "-reconnect 1 -reconnect_streamed 1 -reconnect_delay_max 5",
    "options": "-vn",
}

APLUS_PORTS = [
    ("20/21", "FTP", "File Transfer Protocol"),
    ("22", "SSH/SFTP", "Secure Shell and Secure File Transfer"),
    ("23", "Telnet", "Plaintext remote terminal"),
    ("25", "SMTP", "Mail sending"),
    ("53", "DNS", "Name resolution"),
    ("67/68", "DHCP", "Automatic IP addressing"),
    ("80", "HTTP", "Web traffic"),
    ("110", "POP3", "Mail retrieval"),
    ("143", "IMAP", "Mail retrieval/sync"),
    ("443", "HTTPS", "Encrypted web traffic"),
    ("445", "SMB", "Windows file sharing"),
    ("3389", "RDP", "Remote Desktop"),
]


def load_json(path: Path, default: dict) -> dict:
    if not path.exists():
        path.write_text(json.dumps(default, indent=2), encoding="utf-8")
        return json.loads(json.dumps(default))
    try:
        with path.open("r", encoding="utf-8") as handle:
            data = json.load(handle)
    except Exception:
        return json.loads(json.dumps(default))
    for key, value in default.items():
        data.setdefault(key, json.loads(json.dumps(value)))
    return data


def save_json(path: Path, data: dict) -> None:
    with path.open("w", encoding="utf-8") as handle:
        json.dump(data, handle, indent=2)


config = load_json(CONFIG_FILE, DEFAULT_CONFIG)
data = load_json(DATA_FILE, DEFAULT_DATA)
recent_messages = {}

intents = discord.Intents.default()
intents.message_content = True
intents.members = True
intents.voice_states = True

bot = commands.Bot(command_prefix=commands.when_mentioned_or(PREFIX), intents=intents, help_command=None, case_insensitive=True)


class MusicState:
    def __init__(self):
        self.queue = []
        self.now_playing = None
        self.text_channel_id = None
        self.lock = asyncio.Lock()


music_states = {}


def guild_key(guild_id: int) -> str:
    return str(guild_id)


def user_key(user_id: int) -> str:
    return str(user_id)


def get_music_state(guild_id: int) -> MusicState:
    if guild_id not in music_states:
        music_states[guild_id] = MusicState()
    return music_states[guild_id]


def get_channel(guild: discord.Guild, key: str):
    channel_id = config.get(key)
    return guild.get_channel(channel_id) if channel_id else None


def get_user_bank(user_id: int) -> dict:
    users = data.setdefault("economy", {})
    record = users.setdefault(user_key(user_id), {"wallet": 0, "last_daily": None})
    record.setdefault("wallet", 0)
    record.setdefault("last_daily", None)
    return record


def get_warnings(guild_id: int, user_id: int) -> list[dict]:
    warnings = data.setdefault("warnings", {}).setdefault(guild_key(guild_id), {})
    return warnings.setdefault(user_key(user_id), [])


def format_uptime() -> str:
    delta = datetime.now(timezone.utc) - START_TIME
    days, rem = divmod(int(delta.total_seconds()), 86400)
    hours, rem = divmod(rem, 3600)
    minutes, seconds = divmod(rem, 60)
    return f"{days}d {hours}h {minutes}m {seconds}s"


def chunk_text(text: str, limit: int = 1900) -> list[str]:
    return [text[i:i + limit] for i in range(0, len(text), limit)] or [""]


async def send_log(guild: discord.Guild, title: str, description: str, color: discord.Color = discord.Color.orange()) -> None:
    channel = get_channel(guild, "log_channel")
    if not channel:
        return
    embed = discord.Embed(title=title, description=description[:3900], color=color, timestamp=datetime.now(timezone.utc))
    try:
        await channel.send(embed=embed)
    except discord.HTTPException:
        pass


def build_help_embed() -> discord.Embed:
    embed = discord.Embed(
        title="SpringBot Commands",
        description="All-in-one Discord bot for community, moderation, tickets, roles, AI, music, study, and utility.",
        color=discord.Color.green(),
    )
    groups = {
        "Core": "`!help` `!about` `!ping` `!uptime` `!prefix`",
        "Server": "`!rules` `!setwelcome` `!setgoodbye` `!setlogs` `!setsupport` `!ticketcategory`",
        "Moderation": "`!warn` `!warnings` `!clearwarnings` `!timeout` `!kick` `!ban` `!purge`",
        "Automod": "`!automod on/off` `!blockedwords list/add/remove`",
        "Community": "`!reactionrole` `!ticket` `!close` `!remindme`",
        "Utility": "`!userinfo` `!serverinfo` `!membercount` `!avatar`",
        "Economy": "`!balance` `!daily` `!pay`",
        "Fun": "`!8ball` `!coinflip` `!roll` `!quote`",
        "AI": "`!ask` `!spring` `!springchat` `!springtheme`",
        "Music": "`!join` `!play <song/link>` `!queue` `!nowplaying` `!pause` `!resume` `!skip` `!stop` `!leave`",
        "Study": "`!aplus` `!aplusports`",
    }
    for name, value in groups.items():
        embed.add_field(name=name, value=value, inline=False)
    return embed


async def spring_api_chat(message: str) -> str:
    try:
        async with aiohttp.ClientSession() as session:
            async with session.post(
                f"{SPRING_API_URL}/api/chat",
                json={"message": message},
                timeout=aiohttp.ClientTimeout(total=12),
            ) as response:
                if response.status != 200:
                    return "Spring Virtual Office is temporarily unavailable."
                payload = await response.json()
                return payload.get("reply", "No response from SpringBot.")
    except Exception as exc:
        return f"Connection error: {exc}"


def is_url(text: str) -> bool:
    parsed = urlparse(text)
    return parsed.scheme in {"http", "https"} and bool(parsed.netloc)


async def join_author_voice(ctx) -> discord.VoiceClient | None:
    if not ctx.author.voice or not ctx.author.voice.channel:
        await ctx.send("Join a voice channel first.")
        return None
    channel = ctx.author.voice.channel
    me = ctx.guild.me or ctx.guild.get_member(bot.user.id)
    permissions = channel.permissions_for(me)
    if not permissions.connect or not permissions.speak:
        await ctx.send("I need connect and speak permissions in that voice channel.")
        return None
    voice_client = ctx.guild.voice_client
    if voice_client and voice_client.is_connected():
        if voice_client.channel != channel:
            await voice_client.move_to(channel)
        return voice_client
    return await channel.connect()


async def extract_song(query: str) -> dict:
    if yt_dlp is None:
        raise RuntimeError("yt-dlp is not installed.")

    def run_extract():
        target = query.strip()
        with yt_dlp.YoutubeDL(YTDL_OPTIONS) as ydl:
            lookup = target if is_url(target) else f"ytsearch1:{target}"
            info = ydl.extract_info(lookup, download=False)
            if not info:
                return None
            if "entries" in info:
                entries = info.get("entries") or []
                if not entries:
                    return None
                info = entries[0]
            webpage_url = info.get("webpage_url") or ""
            return {
                "title": info.get("title", "Unknown title"),
                "url": info.get("url"),
                "webpage_url": webpage_url,
                "duration": info.get("duration"),
                "uploader": info.get("uploader", "Unknown"),
                "thumbnail": info.get("thumbnail"),
            }

    loop = asyncio.get_running_loop()
    return await loop.run_in_executor(None, run_extract)


def format_duration(seconds: int | None) -> str:
    if not seconds:
        return "Unknown"
    minutes, seconds = divmod(int(seconds), 60)
    hours, minutes = divmod(minutes, 60)
    return f"{hours}:{minutes:02d}:{seconds:02d}" if hours else f"{minutes}:{seconds:02d}"


async def play_next(guild: discord.Guild) -> None:
    state = get_music_state(guild.id)
    voice_client = guild.voice_client
    if not voice_client or not voice_client.is_connected():
        state.now_playing = None
        return
    async with state.lock:
        if not state.queue:
            state.now_playing = None
            return
        song = state.queue.pop(0)
        state.now_playing = song

    source = discord.FFmpegPCMAudio(song["url"], executable=FFMPEG_PATH, **FFMPEG_OPTIONS)

    def after_playing(error):
        if error:
            print(f"Playback error: {error}")
        future = asyncio.run_coroutine_threadsafe(play_next(guild), bot.loop)
        try:
            future.result()
        except Exception as exc:
            print(f"Queue advance error: {exc}")

    voice_client.play(source, after=after_playing)
    channel = guild.get_channel(state.text_channel_id) if state.text_channel_id else None
    if channel:
        embed = discord.Embed(title="Now Playing", description=f"**{song['title']}**", color=discord.Color.green())
        embed.add_field(name="Duration", value=format_duration(song.get("duration")), inline=True)
        embed.add_field(name="Uploader", value=song.get("uploader", "Unknown"), inline=True)
        embed.add_field(name="Requested By", value=song["requested_by"].mention, inline=True)
        if song.get("webpage_url"):
            embed.add_field(name="Link", value=song["webpage_url"], inline=False)
        if song.get("thumbnail"):
            embed.set_thumbnail(url=song["thumbnail"])
        await channel.send(embed=embed)


@bot.event
async def on_ready():
    print(f"Logged in as {bot.user}")
    await bot.change_presence(activity=discord.Game(name=f"SpringBot | {PREFIX}help"))


@bot.event
async def on_member_join(member: discord.Member):
    channel = get_channel(member.guild, "welcome_channel")
    if channel:
        await channel.send(f"Welcome {member.mention} to **{member.guild.name}**. Use `{PREFIX}help` to see what I can do.")
    await send_log(member.guild, "Member Joined", f"{member.mention} joined.\nAccount created: {member.created_at:%Y-%m-%d %H:%M:%S}", discord.Color.green())


@bot.event
async def on_member_remove(member: discord.Member):
    channel = get_channel(member.guild, "goodbye_channel")
    if channel:
        await channel.send(f"{member} left the server.")
    await send_log(member.guild, "Member Left", f"{member} left the server.", discord.Color.dark_gray())


@bot.event
async def on_message_delete(message: discord.Message):
    if message.guild and not message.author.bot:
        await send_log(message.guild, "Message Deleted", f"Author: {message.author.mention}\nChannel: {message.channel.mention}\nContent: {(message.content or '[no text]')[:900]}", discord.Color.red())


@bot.event
async def on_message_edit(before: discord.Message, after: discord.Message):
    if before.guild and not before.author.bot and before.content != after.content:
        await send_log(before.guild, "Message Edited", f"Author: {before.author.mention}\nChannel: {before.channel.mention}\nBefore: {before.content[:500]}\nAfter: {after.content[:500]}", discord.Color.blue())


@bot.event
async def on_message(message: discord.Message):
    if not message.guild or message.author.bot:
        return
    if config.get("automod_enabled", True):
        lowered = message.content.lower()
        blocked_words = [word.lower() for word in config.get("blocked_words", [])]
        hit_word = next((word for word in blocked_words if word and word in lowered), None)
        hit_invite = config.get("block_invites", True) and re.search(r"(discord\.gg/|discord\.com/invite/)", lowered)
        now = datetime.now(timezone.utc)
        key = (message.guild.id, message.author.id)
        bucket = [stamp for stamp in recent_messages.get(key, []) if (now - stamp).total_seconds() <= 8]
        bucket.append(now)
        recent_messages[key] = bucket
        hit_spam = len(bucket) >= int(config.get("spam_limit", 5) or 5)
        if hit_word or hit_invite or hit_spam:
            try:
                await message.delete()
            except discord.HTTPException:
                pass
            reason = "blocked word" if hit_word else "invite link" if hit_invite else "spam"
            await message.channel.send(f"{message.author.mention}, automod removed that message for {reason}.", delete_after=6)
            await send_log(message.guild, "Automod Action", f"User: {message.author.mention}\nReason: {reason}\nContent: {message.content[:700]}", discord.Color.red())
            return
    await bot.process_commands(message)


@bot.event
async def on_raw_reaction_add(payload: discord.RawReactionActionEvent):
    if payload.guild_id is None or payload.member is None or payload.member.bot:
        return
    role_id = data.setdefault("reaction_roles", {}).get(guild_key(payload.guild_id), {}).get(str(payload.message_id), {}).get(str(payload.emoji))
    guild = bot.get_guild(payload.guild_id)
    role = guild.get_role(role_id) if guild and role_id else None
    if role:
        await payload.member.add_roles(role, reason="SpringBot reaction role")


@bot.event
async def on_raw_reaction_remove(payload: discord.RawReactionActionEvent):
    if payload.guild_id is None:
        return
    role_id = data.setdefault("reaction_roles", {}).get(guild_key(payload.guild_id), {}).get(str(payload.message_id), {}).get(str(payload.emoji))
    guild = bot.get_guild(payload.guild_id)
    member = guild.get_member(payload.user_id) if guild else None
    role = guild.get_role(role_id) if guild and role_id else None
    if member and role:
        await member.remove_roles(role, reason="SpringBot reaction role removed")


@bot.command(name="help")
async def help_command(ctx):
    await ctx.send(embed=build_help_embed())


@bot.command(name="about")
async def about_command(ctx):
    await ctx.send("SpringBot is an all-in-one Discord bot for moderation, automod, logs, tickets, reaction roles, AI, music, economy, reminders, utilities, and study help.")


@bot.command(name="prefix")
async def prefix_command(ctx):
    await ctx.send(f"My current prefix is `{PREFIX}`.")


@bot.command(name="ping")
async def ping_command(ctx):
    await ctx.send(f"Pong: `{round(bot.latency * 1000)}ms`")


@bot.command(name="uptime")
async def uptime_command(ctx):
    await ctx.send(f"Uptime: **{format_uptime()}**")


@bot.command(name="rules")
async def rules_command(ctx):
    await ctx.send(embed=discord.Embed(title="Server Rules", description="\n".join(f"**{i}.** {rule}" for i, rule in enumerate(RULES, 1)), color=discord.Color.green()))


@bot.command(name="setwelcome")
@commands.has_permissions(administrator=True)
async def setwelcome_command(ctx, channel: discord.TextChannel = None):
    config["welcome_channel"] = (channel or ctx.channel).id
    save_json(CONFIG_FILE, config)
    await ctx.send(f"Welcome channel set to {(channel or ctx.channel).mention}.")


@bot.command(name="setgoodbye")
@commands.has_permissions(administrator=True)
async def setgoodbye_command(ctx, channel: discord.TextChannel = None):
    config["goodbye_channel"] = (channel or ctx.channel).id
    save_json(CONFIG_FILE, config)
    await ctx.send(f"Goodbye channel set to {(channel or ctx.channel).mention}.")


@bot.command(name="setlogs")
@commands.has_permissions(administrator=True)
async def setlogs_command(ctx, channel: discord.TextChannel = None):
    config["log_channel"] = (channel or ctx.channel).id
    save_json(CONFIG_FILE, config)
    await ctx.send(f"Log channel set to {(channel or ctx.channel).mention}.")


@bot.command(name="setsupport")
@commands.has_permissions(administrator=True)
async def setsupport_command(ctx, role: discord.Role):
    config["support_role"] = role.id
    save_json(CONFIG_FILE, config)
    await ctx.send(f"Support role set to {role.mention}.")


@bot.command(name="ticketcategory")
@commands.has_permissions(administrator=True)
async def ticketcategory_command(ctx, category: discord.CategoryChannel = None):
    category = category or ctx.channel.category
    if not category:
        await ctx.send("Mention a category or run this in a channel that has one.")
        return
    config["ticket_category"] = category.id
    save_json(CONFIG_FILE, config)
    await ctx.send(f"Ticket category set to **{category.name}**.")


@bot.command(name="warn")
@commands.has_permissions(moderate_members=True)
async def warn_command(ctx, member: discord.Member, *, reason: str = "No reason provided."):
    warnings = get_warnings(ctx.guild.id, member.id)
    warnings.append({"reason": reason, "moderator": str(ctx.author), "created_at": datetime.now(timezone.utc).isoformat()})
    save_json(DATA_FILE, data)
    await ctx.send(f"Warned **{member}**. Total warnings: **{len(warnings)}**.")
    await send_log(ctx.guild, "User Warned", f"User: {member.mention}\nModerator: {ctx.author.mention}\nReason: {reason}")


@bot.command(name="warnings")
@commands.has_permissions(moderate_members=True)
async def warnings_command(ctx, member: discord.Member):
    warnings = get_warnings(ctx.guild.id, member.id)
    if not warnings:
        await ctx.send(f"**{member}** has no warnings.")
        return
    rows = [f"`{i}.` {item.get('reason')} - {item.get('moderator')}" for i, item in enumerate(warnings[-10:], 1)]
    await ctx.send(embed=discord.Embed(title=f"Warnings for {member}", description="\n".join(rows), color=discord.Color.orange()))


@bot.command(name="clearwarnings")
@commands.has_permissions(moderate_members=True)
async def clearwarnings_command(ctx, member: discord.Member):
    warnings = data.setdefault("warnings", {}).setdefault(guild_key(ctx.guild.id), {})
    count = len(warnings.get(user_key(member.id), []))
    warnings[user_key(member.id)] = []
    save_json(DATA_FILE, data)
    await ctx.send(f"Cleared **{count}** warning(s) for **{member}**.")


@bot.command(name="timeout")
@commands.has_permissions(moderate_members=True)
async def timeout_command(ctx, member: discord.Member, minutes: int, *, reason: str = "No reason provided."):
    if minutes < 1 or minutes > 10080:
        await ctx.send("Choose 1 to 10080 minutes.")
        return
    until = datetime.now(timezone.utc) + timedelta(minutes=minutes)
    await member.timeout(until, reason=f"{reason} | Timed out by {ctx.author}")
    await ctx.send(f"Timed out **{member}** for **{minutes}** minute(s).")
    await send_log(ctx.guild, "User Timed Out", f"User: {member.mention}\nModerator: {ctx.author.mention}\nReason: {reason}")


@bot.command(name="kick")
@commands.has_permissions(kick_members=True)
async def kick_command(ctx, member: discord.Member, *, reason: str = "No reason provided."):
    if member == ctx.author or member == ctx.guild.owner:
        await ctx.send("That action is blocked.")
        return
    await member.kick(reason=f"{reason} | Kicked by {ctx.author}")
    await ctx.send(f"Kicked **{member}**. Reason: {reason}")


@bot.command(name="ban")
@commands.has_permissions(ban_members=True)
async def ban_command(ctx, member: discord.Member, *, reason: str = "No reason provided."):
    if member == ctx.author or member == ctx.guild.owner:
        await ctx.send("That action is blocked.")
        return
    await member.ban(reason=f"{reason} | Banned by {ctx.author}")
    await ctx.send(f"Banned **{member}**. Reason: {reason}")


@bot.command(name="purge")
@commands.has_permissions(manage_messages=True)
async def purge_command(ctx, amount: int):
    if amount < 1 or amount > 200:
        await ctx.send("Choose a number between 1 and 200.")
        return
    deleted = await ctx.channel.purge(limit=amount + 1)
    await ctx.send(f"Deleted **{len(deleted) - 1}** message(s).", delete_after=5)


@bot.command(name="automod")
@commands.has_permissions(administrator=True)
async def automod_command(ctx, setting: str = None):
    if setting is None:
        await ctx.send(f"Automod is **{'on' if config.get('automod_enabled', True) else 'off'}**.")
        return
    setting = setting.lower()
    if setting not in {"on", "off"}:
        await ctx.send("Use `!automod on` or `!automod off`.")
        return
    config["automod_enabled"] = setting == "on"
    save_json(CONFIG_FILE, config)
    await ctx.send(f"Automod turned **{setting}**.")


@bot.command(name="blockedwords")
@commands.has_permissions(administrator=True)
async def blockedwords_command(ctx, action: str = "list", *, word: str = None):
    words = config.setdefault("blocked_words", [])
    action = action.lower()
    if action == "list":
        await ctx.send("Blocked words: " + (", ".join(f"`{item}`" for item in words) if words else "none"))
    elif action == "add" and word:
        cleaned = word.lower().strip()
        if cleaned not in words:
            words.append(cleaned)
            save_json(CONFIG_FILE, config)
        await ctx.send(f"Added `{cleaned}`.")
    elif action in {"remove", "delete"} and word:
        cleaned = word.lower().strip()
        if cleaned in words:
            words.remove(cleaned)
            save_json(CONFIG_FILE, config)
        await ctx.send(f"Removed `{cleaned}`.")
    else:
        await ctx.send("Use `!blockedwords list`, `!blockedwords add <word>`, or `!blockedwords remove <word>`.")


@bot.command(name="reactionrole")
@commands.has_permissions(manage_roles=True)
async def reactionrole_command(ctx, message_id: int, emoji: str, role: discord.Role):
    mapping = data.setdefault("reaction_roles", {}).setdefault(guild_key(ctx.guild.id), {})
    mapping.setdefault(str(message_id), {})[emoji] = role.id
    save_json(DATA_FILE, data)
    try:
        message = await ctx.channel.fetch_message(message_id)
        await message.add_reaction(emoji)
    except discord.HTTPException:
        pass
    await ctx.send(f"Saved reaction role: {emoji} gives {role.mention}.")


@bot.command(name="ticket")
async def ticket_command(ctx, *, reason: str = "Support request"):
    category = ctx.guild.get_channel(config.get("ticket_category") or 0)
    support_role = ctx.guild.get_role(config.get("support_role") or 0)
    overwrites = {
        ctx.guild.default_role: discord.PermissionOverwrite(view_channel=False),
        ctx.author: discord.PermissionOverwrite(view_channel=True, send_messages=True, read_message_history=True),
        ctx.guild.me: discord.PermissionOverwrite(view_channel=True, send_messages=True, manage_channels=True),
    }
    if support_role:
        overwrites[support_role] = discord.PermissionOverwrite(view_channel=True, send_messages=True, read_message_history=True)
    channel = await ctx.guild.create_text_channel(
        name=f"ticket-{ctx.author.name}".lower()[:90],
        category=category if isinstance(category, discord.CategoryChannel) else None,
        overwrites=overwrites,
        reason=f"Ticket opened by {ctx.author}: {reason}",
    )
    tickets = data.setdefault("tickets", {}).setdefault(guild_key(ctx.guild.id), {})
    tickets[str(channel.id)] = {"owner_id": ctx.author.id, "reason": reason, "created_at": datetime.now(timezone.utc).isoformat()}
    save_json(DATA_FILE, data)
    await channel.send(f"{ctx.author.mention} opened a ticket.\nReason: {reason}\nStaff can close it with `!close`.")
    await ctx.send(f"Ticket created: {channel.mention}")


@bot.command(name="close")
@commands.has_permissions(manage_channels=True)
async def close_command(ctx, *, reason: str = "Ticket closed"):
    tickets = data.setdefault("tickets", {}).setdefault(guild_key(ctx.guild.id), {})
    if str(ctx.channel.id) not in tickets:
        await ctx.send("This channel is not a SpringBot ticket.")
        return
    ticket = tickets.pop(str(ctx.channel.id))
    save_json(DATA_FILE, data)
    await send_log(ctx.guild, "Ticket Closed", f"Channel: #{ctx.channel.name}\nOwner ID: {ticket.get('owner_id')}\nReason: {reason}", discord.Color.dark_gray())
    await ctx.send("Closing ticket in 5 seconds.")
    await asyncio.sleep(5)
    await ctx.channel.delete(reason=reason)


@bot.command(name="remindme")
async def remindme_command(ctx, minutes: int, *, text: str):
    if minutes < 1 or minutes > 10080:
        await ctx.send("Choose a reminder between 1 minute and 7 days.")
        return
    await ctx.send(f"I will remind you in **{minutes}** minute(s).")
    await asyncio.sleep(minutes * 60)
    try:
        await ctx.author.send(f"Reminder from #{ctx.channel}: {text}")
    except discord.HTTPException:
        await ctx.send(f"{ctx.author.mention} reminder: {text}")


@bot.command(name="userinfo")
async def userinfo_command(ctx, member: discord.Member = None):
    member = member or ctx.author
    embed = discord.Embed(title=f"User Info - {member}", color=discord.Color.green())
    embed.set_thumbnail(url=member.display_avatar.url)
    embed.add_field(name="ID", value=member.id, inline=True)
    embed.add_field(name="Joined", value=member.joined_at.strftime("%Y-%m-%d %H:%M:%S") if member.joined_at else "Unknown", inline=False)
    embed.add_field(name="Created", value=member.created_at.strftime("%Y-%m-%d %H:%M:%S"), inline=False)
    roles = [role.mention for role in member.roles if role.name != "@everyone"]
    embed.add_field(name="Roles", value=", ".join(roles[:20]) if roles else "No roles", inline=False)
    await ctx.send(embed=embed)


@bot.command(name="serverinfo")
async def serverinfo_command(ctx):
    guild = ctx.guild
    embed = discord.Embed(title=f"Server Info - {guild.name}", color=discord.Color.green())
    if guild.icon:
        embed.set_thumbnail(url=guild.icon.url)
    embed.add_field(name="Owner", value=str(guild.owner), inline=False)
    embed.add_field(name="Members", value=guild.member_count, inline=True)
    embed.add_field(name="Roles", value=len(guild.roles), inline=True)
    embed.add_field(name="Channels", value=len(guild.channels), inline=True)
    embed.add_field(name="Created", value=guild.created_at.strftime("%Y-%m-%d %H:%M:%S"), inline=False)
    await ctx.send(embed=embed)


@bot.command(name="membercount")
async def membercount_command(ctx):
    await ctx.send(f"Member count: **{ctx.guild.member_count}**")


@bot.command(name="avatar")
async def avatar_command(ctx, member: discord.Member = None):
    member = member or ctx.author
    embed = discord.Embed(title=f"{member.display_name}'s Avatar", color=discord.Color.green())
    embed.set_image(url=member.display_avatar.url)
    await ctx.send(embed=embed)


@bot.command(name="balance")
async def balance_command(ctx, member: discord.Member = None):
    member = member or ctx.author
    record = get_user_bank(member.id)
    save_json(DATA_FILE, data)
    await ctx.send(f"{member.mention} has **{record['wallet']} SpringCoins**.")


@bot.command(name="daily")
async def daily_command(ctx):
    record = get_user_bank(ctx.author.id)
    now = datetime.now(timezone.utc)
    last_daily = datetime.fromisoformat(record["last_daily"]) if record.get("last_daily") else None
    if last_daily and now < last_daily + timedelta(hours=24):
        remaining = last_daily + timedelta(hours=24) - now
        hours, rem = divmod(int(remaining.total_seconds()), 3600)
        minutes, _ = divmod(rem, 60)
        await ctx.send(f"Try again in **{hours}h {minutes}m**.")
        return
    reward = random.randint(100, 250)
    record["wallet"] += reward
    record["last_daily"] = now.isoformat()
    save_json(DATA_FILE, data)
    await ctx.send(f"{ctx.author.mention} claimed **{reward} SpringCoins**. Balance: **{record['wallet']}**.")


@bot.command(name="pay")
async def pay_command(ctx, member: discord.Member, amount: int):
    if amount < 1:
        await ctx.send("Amount must be positive.")
        return
    sender = get_user_bank(ctx.author.id)
    receiver = get_user_bank(member.id)
    if sender["wallet"] < amount:
        await ctx.send("You do not have enough SpringCoins.")
        return
    sender["wallet"] -= amount
    receiver["wallet"] += amount
    save_json(DATA_FILE, data)
    await ctx.send(f"{ctx.author.mention} paid {member.mention} **{amount} SpringCoins**.")


@bot.command(name="8ball")
async def eightball_command(ctx, *, question: str):
    await ctx.send(f"Question: **{question}**\nAnswer: **{random.choice(EIGHT_BALL)}**")


@bot.command(name="coinflip")
async def coinflip_command(ctx):
    await ctx.send(f"Coinflip result: **{random.choice(['Heads', 'Tails'])}**")


@bot.command(name="roll")
async def roll_command(ctx, dice: str = "1d6"):
    match = re.fullmatch(r"(\d+)d(\d+)", dice.lower().strip())
    if not match:
        await ctx.send("Use `!roll 1d6`, `!roll 2d20`, etc.")
        return
    count, sides = int(match.group(1)), int(match.group(2))
    if count < 1 or count > 20 or sides < 2 or sides > 1000:
        await ctx.send("Dice count must be 1-20 and sides 2-1000.")
        return
    rolls = [random.randint(1, sides) for _ in range(count)]
    await ctx.send(f"Rolled **{dice}**: {', '.join(map(str, rolls))}\nTotal: **{sum(rolls)}**")


@bot.command(name="quote")
async def quote_command(ctx):
    quotes = [
        "Small steps still move the whole story forward.",
        "Discipline is remembering what you wanted.",
        "Build the thing, then make it better.",
    ]
    await ctx.send(random.choice(quotes))


@bot.command(name="ask")
async def ask_command(ctx, *, question: str):
    if OpenAI is None:
        await ctx.send("The openai package is not installed.")
        return
    if client is None:
        await ctx.send("OPENAI_API_KEY is missing.")
        return
    async with ctx.typing():
        def run_ai():
            response = client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {"role": "system", "content": "You are SpringBot, a clear and helpful Discord assistant."},
                    {"role": "user", "content": question},
                ],
            )
            return response.choices[0].message.content or ""

        answer = await asyncio.get_running_loop().run_in_executor(None, run_ai)
    for chunk in chunk_text(answer):
        await ctx.send(chunk)


@bot.command(name="spring")
async def spring_command(ctx, *, action: str = None):
    if not action:
        embed = discord.Embed(title="Spring Virtual Office", description="Your AI-powered workspace for modern teams.", color=discord.Color.green())
        embed.add_field(name="Commands", value="`!springchat <message>`\n`!springtheme black/glass/light`", inline=False)
        embed.add_field(name="Website", value=SPRING_API_URL, inline=False)
        await ctx.send(embed=embed)
        return
    if action.lower().strip() == "chat":
        await ctx.send("Use `!springchat <message>`.")
    elif action.lower().strip() == "theme":
        await ctx.send("Use `!springtheme black`, `!springtheme glass`, or `!springtheme light`.")
    else:
        await ctx.send(SPRING_API_URL)


@bot.command(name="springchat")
async def springchat_command(ctx, *, message: str):
    async with ctx.typing():
        response = await spring_api_chat(message)
    for chunk in chunk_text(response):
        await ctx.send(chunk)


@bot.command(name="springtheme")
@commands.has_permissions(administrator=True)
async def springtheme_command(ctx, theme: str):
    if theme.lower() not in {"black", "glass", "light"}:
        await ctx.send("Use `black`, `glass`, or `light`.")
        return
    config["spring_theme"] = theme.lower()
    save_json(CONFIG_FILE, config)
    await ctx.send(f"Spring theme set to **{theme.lower()}**.")


@bot.command(name="aplus")
async def aplus_command(ctx):
    await ctx.send("A+ study commands: `!aplusports`. More study modules can be added as separate topic packs.")


@bot.command(name="aplusports")
async def aplusports_command(ctx):
    rows = [f"`{port}` - **{name}**: {desc}" for port, name, desc in APLUS_PORTS]
    await ctx.send(embed=discord.Embed(title="A+ Ports and Protocols", description="\n".join(rows), color=discord.Color.blurple()))


@bot.command(name="join")
async def join_command(ctx):
    voice_client = await join_author_voice(ctx)
    if voice_client:
        await ctx.send(f"Joined **{voice_client.channel.name}**.")


@bot.command(name="leave")
async def leave_command(ctx):
    voice_client = ctx.guild.voice_client
    if not voice_client or not voice_client.is_connected():
        await ctx.send("I am not in a voice channel.")
        return
    get_music_state(ctx.guild.id).queue.clear()
    await voice_client.disconnect()
    await ctx.send("Left the voice channel.")


@bot.command(name="play")
async def play_command(ctx, *, query: str):
    voice_client = await join_author_voice(ctx)
    if not voice_client:
        return
    state = get_music_state(ctx.guild.id)
    state.text_channel_id = ctx.channel.id
    async with ctx.typing():
        try:
            song = await extract_song(query)
        except Exception as exc:
            await ctx.send(f"Music error: {exc}")
            return
    if not song or not song.get("url"):
        await ctx.send("I could not find a playable audio source.")
        return
    song["requested_by"] = ctx.author
    state.queue.append(song)
    if voice_client.is_playing() or voice_client.is_paused() or state.now_playing:
        await ctx.send(f"Added to queue: **{song['title']}**")
    else:
        await ctx.send(f"Loaded: **{song['title']}**")
        await play_next(ctx.guild)


@bot.command(name="queue")
async def queue_command(ctx):
    state = get_music_state(ctx.guild.id)
    if not state.now_playing and not state.queue:
        await ctx.send("The queue is empty.")
        return
    rows = []
    if state.now_playing:
        rows.append(f"Now: **{state.now_playing['title']}**")
    rows.extend(f"{i}. {song['title']}" for i, song in enumerate(state.queue[:10], 1))
    await ctx.send("\n".join(rows))


@bot.command(name="nowplaying")
async def nowplaying_command(ctx):
    song = get_music_state(ctx.guild.id).now_playing
    await ctx.send(f"Now playing: **{song['title']}**" if song else "Nothing is playing.")


@bot.command(name="pause")
async def pause_command(ctx):
    voice_client = ctx.guild.voice_client
    if voice_client and voice_client.is_playing():
        voice_client.pause()
        await ctx.send("Paused.")
    else:
        await ctx.send("Nothing is playing.")


@bot.command(name="resume")
async def resume_command(ctx):
    voice_client = ctx.guild.voice_client
    if voice_client and voice_client.is_paused():
        voice_client.resume()
        await ctx.send("Resumed.")
    else:
        await ctx.send("Nothing is paused.")


@bot.command(name="skip")
async def skip_command(ctx):
    voice_client = ctx.guild.voice_client
    if voice_client and (voice_client.is_playing() or voice_client.is_paused()):
        voice_client.stop()
        await ctx.send("Skipped.")
    else:
        await ctx.send("Nothing is playing.")


@bot.command(name="stop")
async def stop_command(ctx):
    voice_client = ctx.guild.voice_client
    state = get_music_state(ctx.guild.id)
    state.queue.clear()
    state.now_playing = None
    if voice_client and (voice_client.is_playing() or voice_client.is_paused()):
        voice_client.stop()
    await ctx.send("Stopped playback and cleared the queue.")


@bot.event
async def on_command_error(ctx, error):
    if isinstance(error, commands.CommandNotFound):
        return
    if isinstance(error, commands.MissingPermissions):
        await ctx.send("You do not have permission to use that command.")
        return
    if isinstance(error, commands.BotMissingPermissions):
        await ctx.send("I do not have the permissions needed for that command.")
        return
    if isinstance(error, commands.MissingRequiredArgument):
        await ctx.send(f"Missing argument: `{error.param.name}`")
        return
    if isinstance(error, commands.BadArgument):
        await ctx.send("Invalid argument for that command.")
        return
    original = getattr(error, "original", error)
    await ctx.send(f"Error: {original}")


if not TOKEN:
    raise ValueError("DISCORD_TOKEN is missing from your environment variables.")

bot.run(TOKEN)
