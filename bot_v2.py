import os
import json
import sqlite3
import asyncio
from pathlib import Path
from datetime import datetime, timezone, timedelta

import discord
from discord.ext import commands

try:
    from dotenv import load_dotenv
    load_dotenv()
except Exception:
    pass

try:
    from openai import OpenAI
except Exception:
    OpenAI = None

TOKEN = os.getenv("DISCORD_TOKEN")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
OPENAI_MODEL = os.getenv("OPENAI_MODEL", "gpt-4o-mini")
PREFIX = os.getenv("SPRINGBOT_PREFIX", "!")
DB_PATH = os.getenv("SPRINGBOT_DB", "springbot_v2.db")

client = OpenAI(api_key=OPENAI_API_KEY) if OpenAI and OPENAI_API_KEY else None
START_TIME = datetime.now(timezone.utc)

intents = discord.Intents.default()
intents.message_content = True
intents.members = True
intents.guilds = True
bot = commands.Bot(command_prefix=PREFIX, intents=intents, help_command=None)

SYSTEM_PROMPT = """
You are SpringBot, an advanced AI assistant for Discord communities, IT support, cybersecurity study, server management, and Spring Virtual Office.
Be useful, direct, professional, and practical. When you give technical help, give steps that can actually be followed.
Never expose API keys, tokens, passwords, or private environment variables.
"""

SAFE_ACTIONS = {
    "create_ticket": "Create a private support ticket channel.",
    "server_health": "Analyze server activity and give admin recommendations.",
    "study_quiz": "Generate a study quiz.",
    "summarize_channel": "Summarize recent channel messages.",
    "make_announcement": "Draft a server announcement.",
}

ACTIONS_HELP = "\n".join([f"`{name}` - {desc}" for name, desc in SAFE_ACTIONS.items()])


def db_connect():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def setup_database():
    with db_connect() as conn:
        conn.execute("""
        CREATE TABLE IF NOT EXISTS user_memory (
            user_id TEXT NOT NULL,
            guild_id TEXT NOT NULL,
            key TEXT NOT NULL,
            value TEXT NOT NULL,
            created_at TEXT NOT NULL,
            PRIMARY KEY (user_id, guild_id, key)
        )
        """)
        conn.execute("""
        CREATE TABLE IF NOT EXISTS conversations (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id TEXT NOT NULL,
            guild_id TEXT NOT NULL,
            channel_id TEXT NOT NULL,
            role TEXT NOT NULL,
            content TEXT NOT NULL,
            created_at TEXT NOT NULL
        )
        """)
        conn.execute("""
        CREATE TABLE IF NOT EXISTS tickets (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            guild_id TEXT NOT NULL,
            user_id TEXT NOT NULL,
            channel_id TEXT NOT NULL,
            reason TEXT NOT NULL,
            status TEXT NOT NULL,
            created_at TEXT NOT NULL
        )
        """)
        conn.execute("""
        CREATE TABLE IF NOT EXISTS server_notes (
            guild_id TEXT NOT NULL,
            key TEXT NOT NULL,
            value TEXT NOT NULL,
            updated_at TEXT NOT NULL,
            PRIMARY KEY (guild_id, key)
        )
        """)
        conn.commit()


def now_iso():
    return datetime.now(timezone.utc).isoformat()


def add_conversation(user_id, guild_id, channel_id, role, content):
    content = (content or "").strip()
    if not content:
        return
    with db_connect() as conn:
        conn.execute(
            "INSERT INTO conversations (user_id, guild_id, channel_id, role, content, created_at) VALUES (?, ?, ?, ?, ?, ?)",
            (str(user_id), str(guild_id), str(channel_id), role, content[:3000], now_iso()),
        )
        conn.commit()


def get_recent_context(user_id, guild_id, limit=12):
    with db_connect() as conn:
        rows = conn.execute(
            "SELECT role, content FROM conversations WHERE user_id=? AND guild_id=? ORDER BY id DESC LIMIT ?",
            (str(user_id), str(guild_id), limit),
        ).fetchall()
    return list(reversed(rows))


def set_memory(user_id, guild_id, key, value):
    with db_connect() as conn:
        conn.execute(
            "INSERT OR REPLACE INTO user_memory (user_id, guild_id, key, value, created_at) VALUES (?, ?, ?, ?, ?)",
            (str(user_id), str(guild_id), key.lower().strip(), value.strip(), now_iso()),
        )
        conn.commit()


def get_memory(user_id, guild_id):
    with db_connect() as conn:
        rows = conn.execute(
            "SELECT key, value FROM user_memory WHERE user_id=? AND guild_id=? ORDER BY key ASC",
            (str(user_id), str(guild_id)),
        ).fetchall()
    return {row["key"]: row["value"] for row in rows}


def delete_memory(user_id, guild_id, key=None):
    with db_connect() as conn:
        if key:
            conn.execute(
                "DELETE FROM user_memory WHERE user_id=? AND guild_id=? AND key=?",
                (str(user_id), str(guild_id), key.lower().strip()),
            )
        else:
            conn.execute(
                "DELETE FROM user_memory WHERE user_id=? AND guild_id=?",
                (str(user_id), str(guild_id)),
            )
        conn.commit()


def format_uptime():
    delta = datetime.now(timezone.utc) - START_TIME
    total = int(delta.total_seconds())
    days, rem = divmod(total, 86400)
    hours, rem = divmod(rem, 3600)
    minutes, seconds = divmod(rem, 60)
    return f"{days}d {hours}h {minutes}m {seconds}s"


def chunk_text(text, size=1800):
    return [text[i:i + size] for i in range(0, len(text), size)] or [""]


async def ai_response(user_message, user_id, guild_id):
    memory = get_memory(user_id, guild_id)
    history = get_recent_context(user_id, guild_id)

    memory_text = "\n".join([f"- {k}: {v}" for k, v in memory.items()]) or "No saved memory yet."

    messages = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "system", "content": f"Saved user memory for this server:\n{memory_text}"},
    ]

    for row in history:
        role = "assistant" if row["role"] == "assistant" else "user"
        messages.append({"role": role, "content": row["content"]})

    messages.append({"role": "user", "content": user_message})

    if not client:
        return "AI is not connected. Add your `OPENAI_API_KEY` environment variable, then restart SpringBot."

    try:
        result = await asyncio.to_thread(
            client.chat.completions.create,
            model=OPENAI_MODEL,
            messages=messages,
            temperature=0.7,
        )
        return result.choices[0].message.content.strip()
    except Exception as e:
        return f"AI error: {e}"


@bot.event
async def on_ready():
    setup_database()
    print(f"SpringBot V2 online as {bot.user}")
    await bot.change_presence(activity=discord.Game(name="SpringBot V2 | !v2help"))


@bot.command(name="v2help")
async def v2help(ctx):
    embed = discord.Embed(
        title="🌸 SpringBot V2 Upgrade",
        description="AI memory, AI actions, tickets, server health, study tools, and smarter chat.",
        color=discord.Color.green(),
    )
    embed.add_field(name="AI", value="`!springai <message>`\n`!summarize [amount]`", inline=False)
    embed.add_field(name="Memory", value="`!remember <key> = <value>`\n`!memory`\n`!forget <key>`\n`!forgetme`", inline=False)
    embed.add_field(name="Actions", value="`!actions`\n`!do create_ticket <reason>`\n`!do server_health`\n`!do study_quiz <topic>`\n`!do make_announcement <topic>`", inline=False)
    embed.add_field(name="Admin / Server", value="`!serverhealth`\n`!ticket <reason>`\n`!uptime2`", inline=False)
    await ctx.send(embed=embed)


@bot.command(name="springai")
async def springai(ctx, *, message: str):
    add_conversation(ctx.author.id, ctx.guild.id if ctx.guild else 0, ctx.channel.id, "user", message)
    async with ctx.typing():
        reply = await ai_response(message, ctx.author.id, ctx.guild.id if ctx.guild else 0)
    add_conversation(ctx.author.id, ctx.guild.id if ctx.guild else 0, ctx.channel.id, "assistant", reply)
    for part in chunk_text(reply):
        await ctx.send(part)


@bot.command(name="remember")
async def remember(ctx, *, text: str):
    if "=" not in text:
        await ctx.send("Use it like this: `!remember favorite_topic = cybersecurity`")
        return
    key, value = text.split("=", 1)
    set_memory(ctx.author.id, ctx.guild.id if ctx.guild else 0, key, value)
    await ctx.send(f"Saved memory: `{key.strip().lower()}`")


@bot.command(name="memory")
async def memory(ctx):
    memory_data = get_memory(ctx.author.id, ctx.guild.id if ctx.guild else 0)
    if not memory_data:
        await ctx.send("No memory saved for you yet. Use `!remember key = value`.")
        return
    lines = [f"**{k}:** {v}" for k, v in memory_data.items()]
    await ctx.send("🌿 **Your SpringBot Memory**\n" + "\n".join(lines))


@bot.command(name="forget")
async def forget(ctx, *, key: str):
    delete_memory(ctx.author.id, ctx.guild.id if ctx.guild else 0, key)
    await ctx.send(f"Forgot memory key: `{key.lower().strip()}`")


@bot.command(name="forgetme")
async def forgetme(ctx):
    delete_memory(ctx.author.id, ctx.guild.id if ctx.guild else 0)
    await ctx.send("I deleted your saved SpringBot memory for this server.")


@bot.command(name="actions")
async def actions(ctx):
    await ctx.send("⚙️ **SpringBot AI Actions**\n" + ACTIONS_HELP + "\n\nUse: `!do <action> <details>`")


@bot.command(name="do")
async def do_action(ctx, action: str = None, *, details: str = ""):
    if not action:
        await ctx.send("Use `!actions` to see what I can do.")
        return

    action = action.lower().strip()

    if action == "create_ticket":
        await create_ticket(ctx, reason=details or "No reason provided")
    elif action == "server_health":
        await serverhealth(ctx)
    elif action == "study_quiz":
        await study_quiz(ctx, topic=details or "CompTIA A+ networking")
    elif action == "summarize_channel":
        await summarize(ctx, amount=50)
    elif action == "make_announcement":
        topic = details or "server update"
        prompt = f"Create a professional Discord announcement about: {topic}. Make it clear, polished, and useful."
        reply = await ai_response(prompt, ctx.author.id, ctx.guild.id if ctx.guild else 0)
        await ctx.send("📢 **Draft Announcement**\n" + reply)
    else:
        await ctx.send("Unknown action. Use `!actions` to see available actions.")


@bot.command(name="ticket")
async def ticket(ctx, *, reason: str = "Support request"):
    await create_ticket(ctx, reason)


async def create_ticket(ctx, reason: str):
    guild = ctx.guild
    if not guild:
        await ctx.send("Tickets only work inside a server.")
        return

    overwrites = {
        guild.default_role: discord.PermissionOverwrite(read_messages=False),
        ctx.author: discord.PermissionOverwrite(read_messages=True, send_messages=True),
        guild.me: discord.PermissionOverwrite(read_messages=True, send_messages=True),
    }

    channel_name = f"ticket-{ctx.author.name}".lower().replace(" ", "-")[:90]
    channel = await guild.create_text_channel(channel_name, overwrites=overwrites, reason="SpringBot ticket created")

    with db_connect() as conn:
        conn.execute(
            "INSERT INTO tickets (guild_id, user_id, channel_id, reason, status, created_at) VALUES (?, ?, ?, ?, ?, ?)",
            (str(guild.id), str(ctx.author.id), str(channel.id), reason, "open", now_iso()),
        )
        conn.commit()

    await channel.send(f"🌸 Ticket created for {ctx.author.mention}\n**Reason:** {reason}\nA staff member can help here.")
    await ctx.send(f"Ticket created: {channel.mention}")


@bot.command(name="serverhealth")
async def serverhealth(ctx):
    guild = ctx.guild
    if not guild:
        await ctx.send("Server health only works inside a server.")
        return

    text_channels = len(guild.text_channels)
    voice_channels = len(guild.voice_channels)
    members = guild.member_count or len(guild.members)
    bots = len([m for m in guild.members if m.bot])
    humans = max(members - bots, 0)
    roles = len(guild.roles)

    recommendations = []
    if text_channels > 25:
        recommendations.append("You may have too many text channels. Consider merging inactive channels.")
    if bots > humans * 0.3 and humans > 0:
        recommendations.append("Bot count is high compared to human members. Review bot permissions.")
    if roles > 30:
        recommendations.append("Role count is high. Clean up unused roles to reduce permission mistakes.")
    if not recommendations:
        recommendations.append("Server structure looks clean. Keep improving onboarding, rules, and engagement.")

    embed = discord.Embed(title="📊 SpringBot Server Health", color=discord.Color.green())
    embed.add_field(name="Members", value=f"{members} total\n{humans} humans\n{bots} bots", inline=True)
    embed.add_field(name="Channels", value=f"{text_channels} text\n{voice_channels} voice", inline=True)
    embed.add_field(name="Roles", value=str(roles), inline=True)
    embed.add_field(name="Recommendations", value="\n".join([f"• {r}" for r in recommendations]), inline=False)
    await ctx.send(embed=embed)


@bot.command(name="summarize")
async def summarize(ctx, amount: int = 50):
    amount = max(5, min(amount, 100))
    messages = []
    async for msg in ctx.channel.history(limit=amount):
        if msg.author.bot:
            continue
        messages.append(f"{msg.author.display_name}: {msg.content}")

    messages = list(reversed(messages))
    if not messages:
        await ctx.send("No user messages found to summarize.")
        return

    prompt = "Summarize this Discord conversation. Include key points, decisions, action items, and any unresolved questions.\n\n" + "\n".join(messages[-amount:])
    async with ctx.typing():
        reply = await ai_response(prompt, ctx.author.id, ctx.guild.id if ctx.guild else 0)
    for part in chunk_text("🧠 **Channel Summary**\n" + reply):
        await ctx.send(part)


@bot.command(name="study")
async def study(ctx, *, topic: str = "CompTIA A+ networking"):
    prompt = f"Create a focused study guide for {topic}. Include key terms, simple explanations, and 5 practice questions with answers."
    async with ctx.typing():
        reply = await ai_response(prompt, ctx.author.id, ctx.guild.id if ctx.guild else 0)
    for part in chunk_text(reply):
        await ctx.send(part)


async def study_quiz(ctx, topic: str):
    prompt = f"Create a 5-question multiple-choice quiz about {topic}. Include answer key and short explanations."
    async with ctx.typing():
        reply = await ai_response(prompt, ctx.author.id, ctx.guild.id if ctx.guild else 0)
    for part in chunk_text("📝 **SpringBot Study Quiz**\n" + reply):
        await ctx.send(part)


@bot.command(name="uptime2")
async def uptime2(ctx):
    await ctx.send(f"SpringBot V2 uptime: `{format_uptime()}`")


@bot.event
async def on_message(message):
    if message.author.bot:
        return

    await bot.process_commands(message)

    if not message.guild:
        return

    # Lightweight conversation logging only when users mention SpringBot.
    if bot.user and bot.user.mentioned_in(message):
        cleaned = message.content.replace(f"<@{bot.user.id}>", "").replace(f"<@!{bot.user.id}>", "").strip()
        if cleaned:
            add_conversation(message.author.id, message.guild.id, message.channel.id, "user", cleaned)
            async with message.channel.typing():
                reply = await ai_response(cleaned, message.author.id, message.guild.id)
            add_conversation(message.author.id, message.guild.id, message.channel.id, "assistant", reply)
            for part in chunk_text(reply):
                await message.channel.send(part)


if __name__ == "__main__":
    if not TOKEN:
        raise RuntimeError("Missing DISCORD_TOKEN environment variable.")
    setup_database()
    bot.run(TOKEN)
