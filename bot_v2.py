import os
import re
import sqlite3
import asyncio
from datetime import datetime, timezone, timedelta

import discord
from discord.ext import commands, tasks

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
You are SpringBot, an advanced AI assistant for Discord communities, IT support, cybersecurity study,
server management, automation, and Spring Virtual Office.

Your style:
- Useful, direct, professional, and practical.
- Give steps people can actually follow.
- Help with IT support, Discord community operations, business workflows, studying, and AI automation.
- Never expose API keys, Discord tokens, passwords, private environment variables, or secrets.
- Never claim you completed actions that were not actually executed.
"""

SAFE_ACTIONS = {
    "create_ticket": "Create a private support ticket channel.",
    "server_health": "Analyze server activity and give admin recommendations.",
    "study_quiz": "Generate a study quiz.",
    "summarize_channel": "Summarize recent channel messages.",
    "make_announcement": "Draft a server announcement.",
    "onboarding": "Create a polished onboarding message for new members.",
    "mod_scan": "Review recent messages for moderation concerns.",
    "daily_brief": "Create a daily server/business brief.",
    "project_plan": "Create a project plan from an idea.",
}

SCAM_PATTERNS = [
    r"free\s+nitro",
    r"steam\s+gift",
    r"claim\s+your\s+prize",
    r"airdrop",
    r"wallet\s+connect",
    r"verify\s+your\s+account",
    r"discord\s+staff",
    r"click\s+this\s+link",
    r"limited\s+time\s+offer",
]

TOXIC_WORDS = [
    "kys",
    "kill yourself",
]

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
        conn.execute("""
        CREATE TABLE IF NOT EXISTS knowledge_base (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            guild_id TEXT NOT NULL,
            title TEXT NOT NULL,
            body TEXT NOT NULL,
            created_by TEXT NOT NULL,
            created_at TEXT NOT NULL
        )
        """)
        conn.execute("""
        CREATE TABLE IF NOT EXISTS reminders (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            guild_id TEXT NOT NULL,
            channel_id TEXT NOT NULL,
            user_id TEXT NOT NULL,
            remind_at TEXT NOT NULL,
            message TEXT NOT NULL,
            status TEXT NOT NULL,
            created_at TEXT NOT NULL
        )
        """)
        conn.execute("""
        CREATE TABLE IF NOT EXISTS incidents (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            guild_id TEXT NOT NULL,
            channel_id TEXT NOT NULL,
            user_id TEXT NOT NULL,
            message TEXT NOT NULL,
            reason TEXT NOT NULL,
            severity TEXT NOT NULL,
            created_at TEXT NOT NULL
        )
        """)
        conn.execute("""
        CREATE TABLE IF NOT EXISTS guild_settings (
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


def parse_iso(value):
    return datetime.fromisoformat(value)


def set_guild_setting(guild_id, key, value):
    with db_connect() as conn:
        conn.execute(
            "INSERT OR REPLACE INTO guild_settings (guild_id, key, value, updated_at) VALUES (?, ?, ?, ?)",
            (str(guild_id), key, str(value), now_iso()),
        )
        conn.commit()


def get_guild_setting(guild_id, key, default=None):
    with db_connect() as conn:
        row = conn.execute(
            "SELECT value FROM guild_settings WHERE guild_id=? AND key=?",
            (str(guild_id), key),
        ).fetchone()
    return row["value"] if row else default


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


def log_incident(guild_id, channel_id, user_id, message, reason, severity="medium"):
    with db_connect() as conn:
        conn.execute(
            "INSERT INTO incidents (guild_id, channel_id, user_id, message, reason, severity, created_at) VALUES (?, ?, ?, ?, ?, ?, ?)",
            (str(guild_id), str(channel_id), str(user_id), message[:1000], reason, severity, now_iso()),
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


def parse_reminder_time(value):
    value = value.strip().lower()
    match = re.fullmatch(r"(\d+)(s|m|h|d)", value)
    if not match:
        return None

    amount = int(match.group(1))
    unit = match.group(2)

    if unit == "s":
        return timedelta(seconds=amount)
    if unit == "m":
        return timedelta(minutes=amount)
    if unit == "h":
        return timedelta(hours=amount)
    if unit == "d":
        return timedelta(days=amount)
    return None


def detect_risky_message(content):
    lowered = content.lower()

    for word in TOXIC_WORDS:
        if word in lowered:
            return "high", f"Toxic phrase detected: {word}"

    for pattern in SCAM_PATTERNS:
        if re.search(pattern, lowered):
            return "high", f"Possible scam/phishing pattern: {pattern}"

    if lowered.count("http://") + lowered.count("https://") >= 3:
        return "medium", "Multiple links in one message"

    if "@everyone" in lowered or "@here" in lowered:
        return "medium", "Mass mention detected"

    return None, None


async def ai_response(user_message, user_id, guild_id):
    memory = get_memory(user_id, guild_id)
    history = get_recent_context(user_id, guild_id)
    kb_context = get_knowledge_context(guild_id, user_message)

    memory_text = "\n".join([f"- {k}: {v}" for k, v in memory.items()]) or "No saved memory yet."
    kb_text = kb_context or "No matching knowledge-base notes."

    messages = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "system", "content": f"Saved user memory for this server:\n{memory_text}"},
        {"role": "system", "content": f"Relevant SpringBot knowledge-base notes:\n{kb_text}"},
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


def get_knowledge_context(guild_id, query, limit=5):
    terms = [t.lower() for t in re.findall(r"[a-zA-Z0-9+#.-]{3,}", query or "")]
    if not terms:
        return ""

    with db_connect() as conn:
        rows = conn.execute(
            "SELECT title, body FROM knowledge_base WHERE guild_id=? ORDER BY id DESC LIMIT 50",
            (str(guild_id),),
        ).fetchall()

    scored = []
    for row in rows:
        text = f"{row['title']} {row['body']}".lower()
        score = sum(1 for term in terms if term in text)
        if score:
            scored.append((score, row["title"], row["body"]))

    scored.sort(reverse=True, key=lambda x: x[0])
    return "\n\n".join([f"Title: {title}\n{body[:900]}" for _, title, body in scored[:limit]])


@tasks.loop(seconds=30)
async def reminder_loop():
    await bot.wait_until_ready()
    setup_database()

    now = datetime.now(timezone.utc)
    with db_connect() as conn:
        rows = conn.execute(
            "SELECT * FROM reminders WHERE status='open' ORDER BY remind_at ASC LIMIT 10"
        ).fetchall()

    for row in rows:
        try:
            remind_at = parse_iso(row["remind_at"])
        except Exception:
            continue

        if remind_at > now:
            continue

        channel = bot.get_channel(int(row["channel_id"]))
        if channel:
            await channel.send(f"⏰ <@{row['user_id']}> reminder: {row['message']}")

        with db_connect() as conn:
            conn.execute("UPDATE reminders SET status='sent' WHERE id=?", (row["id"],))
            conn.commit()


@bot.event
async def on_ready():
    setup_database()
    if not reminder_loop.is_running():
        reminder_loop.start()
    print(f"SpringBot V2 online as {bot.user}")
    await bot.change_presence(activity=discord.Game(name="SpringBot V2 | !v2help"))


@bot.command(name="v2help")
async def v2help(ctx):
    embed = discord.Embed(
        title="🌸 SpringBot V2 Premium",
        description="AI memory, AI actions, tickets, moderation, knowledge base, reminders, server health, study tools, and smarter chat.",
        color=discord.Color.green(),
    )
    embed.add_field(name="AI", value="`!springai <message>`\n`!summarize [amount]`\n`!brainstorm <idea>`\n`!fixidea <problem>`", inline=False)
    embed.add_field(name="Memory", value="`!remember <key> = <value>`\n`!memory`\n`!forget <key>`\n`!forgetme`", inline=False)
    embed.add_field(name="AI Actions", value="`!actions`\n`!do create_ticket <reason>`\n`!do server_health`\n`!do study_quiz <topic>`\n`!do make_announcement <topic>`\n`!do daily_brief`\n`!do onboarding`", inline=False)
    embed.add_field(name="Knowledge Base", value="`!kbadd <title> | <note>`\n`!kbsearch <term>`\n`!kblist`", inline=False)
    embed.add_field(name="Admin / Server", value="`!serverhealth`\n`!automod on/off/status`\n`!modscan [amount]`\n`!incidents`\n`!ticket <reason>`", inline=False)
    embed.add_field(name="Productivity", value="`!remind 10m check logs`\n`!dailybrief`\n`!onboard`\n`!projectplan <idea>`", inline=False)
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
    elif action == "onboarding":
        await onboard(ctx, target=None)
    elif action == "mod_scan":
        await modscan(ctx, amount=50)
    elif action == "daily_brief":
        await dailybrief(ctx)
    elif action == "project_plan":
        await projectplan(ctx, idea=details or "SpringBot AI platform")
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
    automod = get_guild_setting(guild.id, "automod", "off")

    recommendations = []
    if text_channels > 25:
        recommendations.append("You may have too many text channels. Consider merging inactive channels.")
    if bots > humans * 0.3 and humans > 0:
        recommendations.append("Bot count is high compared to human members. Review bot permissions.")
    if roles > 30:
        recommendations.append("Role count is high. Clean up unused roles to reduce permission mistakes.")
    if automod != "on":
        recommendations.append("Turn on SpringBot automod with `!automod on` for scam and toxic phrase detection.")
    if not recommendations:
        recommendations.append("Server structure looks clean. Keep improving onboarding, rules, and engagement.")

    embed = discord.Embed(title="📊 SpringBot Server Health", color=discord.Color.green())
    embed.add_field(name="Members", value=f"{members} total\n{humans} humans\n{bots} bots", inline=True)
    embed.add_field(name="Channels", value=f"{text_channels} text\n{voice_channels} voice", inline=True)
    embed.add_field(name="Roles", value=str(roles), inline=True)
    embed.add_field(name="Automod", value=automod.upper(), inline=True)
    embed.add_field(name="Recommendations", value="\n".join([f"• {r}" for r in recommendations]), inline=False)
    await ctx.send(embed=embed)


@bot.command(name="automod")
@commands.has_permissions(manage_guild=True)
async def automod(ctx, mode: str = "status"):
    mode = mode.lower().strip()
    if mode not in {"on", "off", "status"}:
        await ctx.send("Use `!automod on`, `!automod off`, or `!automod status`.")
        return

    if mode in {"on", "off"}:
        set_guild_setting(ctx.guild.id, "automod", mode)
        await ctx.send(f"SpringBot automod is now **{mode.upper()}**.")
        return

    status = get_guild_setting(ctx.guild.id, "automod", "off")
    await ctx.send(f"SpringBot automod status: **{status.upper()}**")


@bot.command(name="incidents")
@commands.has_permissions(manage_messages=True)
async def incidents(ctx):
    with db_connect() as conn:
        rows = conn.execute(
            "SELECT * FROM incidents WHERE guild_id=? ORDER BY id DESC LIMIT 10",
            (str(ctx.guild.id),),
        ).fetchall()

    if not rows:
        await ctx.send("No moderation incidents logged yet.")
        return

    lines = []
    for row in rows:
        lines.append(f"**{row['severity'].upper()}** <@{row['user_id']}> — {row['reason']}")

    await ctx.send("🛡️ **Recent SpringBot Incidents**\n" + "\n".join(lines))


@bot.command(name="modscan")
@commands.has_permissions(manage_messages=True)
async def modscan(ctx, amount: int = 50):
    amount = max(5, min(amount, 100))
    flagged = []

    async for msg in ctx.channel.history(limit=amount):
        if msg.author.bot:
            continue
        severity, reason = detect_risky_message(msg.content)
        if severity:
            flagged.append((severity, reason, msg.author.mention, msg.content[:100]))

    if not flagged:
        await ctx.send("🛡️ No obvious scam/toxic patterns found in recent messages.")
        return

    lines = [f"**{sev.upper()}** {user} — {reason} — `{content}`" for sev, reason, user, content in flagged[:10]]
    await ctx.send("🛡️ **SpringBot Mod Scan Results**\n" + "\n".join(lines))


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

    prompt = "Summarize this Discord conversation. Include key points, decisions, action items, and unresolved questions.\n\n" + "\n".join(messages[-amount:])
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


@bot.command(name="kbadd")
@commands.has_permissions(manage_guild=True)
async def kbadd(ctx, *, text: str):
    if "|" not in text:
        await ctx.send("Use: `!kbadd Title | Note body`")
        return

    title, body = text.split("|", 1)
    with db_connect() as conn:
        conn.execute(
            "INSERT INTO knowledge_base (guild_id, title, body, created_by, created_at) VALUES (?, ?, ?, ?, ?)",
            (str(ctx.guild.id), title.strip()[:120], body.strip()[:3000], str(ctx.author.id), now_iso()),
        )
        conn.commit()

    await ctx.send(f"📚 Added to SpringBot knowledge base: **{title.strip()}**")


@bot.command(name="kbsearch")
async def kbsearch(ctx, *, query: str):
    context = get_knowledge_context(ctx.guild.id if ctx.guild else 0, query, limit=5)
    if not context:
        await ctx.send("No matching knowledge-base notes found.")
        return

    for part in chunk_text("📚 **Knowledge Base Results**\n" + context):
        await ctx.send(part)


@bot.command(name="kblist")
async def kblist(ctx):
    with db_connect() as conn:
        rows = conn.execute(
            "SELECT id, title, created_at FROM knowledge_base WHERE guild_id=? ORDER BY id DESC LIMIT 20",
            (str(ctx.guild.id if ctx.guild else 0),),
        ).fetchall()

    if not rows:
        await ctx.send("No knowledge-base notes yet. Add one with `!kbadd Title | Note body`.")
        return

    lines = [f"`{row['id']}` — **{row['title']}**" for row in rows]
    await ctx.send("📚 **SpringBot Knowledge Base**\n" + "\n".join(lines))


@bot.command(name="remind")
async def remind(ctx, time_value: str = None, *, message: str = None):
    if not time_value or not message:
        await ctx.send("Use: `!remind 10m check logs` or `!remind 2h study Security+`")
        return

    delta = parse_reminder_time(time_value)
    if not delta:
        await ctx.send("Use time like `30s`, `10m`, `2h`, or `1d`.")
        return

    remind_at = datetime.now(timezone.utc) + delta

    with db_connect() as conn:
        conn.execute(
            "INSERT INTO reminders (guild_id, channel_id, user_id, remind_at, message, status, created_at) VALUES (?, ?, ?, ?, ?, ?, ?)",
            (str(ctx.guild.id if ctx.guild else 0), str(ctx.channel.id), str(ctx.author.id), remind_at.isoformat(), message, "open", now_iso()),
        )
        conn.commit()

    await ctx.send(f"⏰ Reminder set for <@{ctx.author.id}> in `{time_value}`.")


@bot.command(name="dailybrief")
async def dailybrief(ctx):
    messages = []
    async for msg in ctx.channel.history(limit=100):
        if not msg.author.bot and msg.content:
            messages.append(f"{msg.author.display_name}: {msg.content}")

    prompt = (
        "Create a clean daily brief from these recent Discord messages. "
        "Include wins, problems, action items, and recommended next steps.\n\n"
        + "\n".join(reversed(messages))
    )
    async with ctx.typing():
        reply = await ai_response(prompt, ctx.author.id, ctx.guild.id if ctx.guild else 0)
    for part in chunk_text("🗓️ **SpringBot Daily Brief**\n" + reply):
        await ctx.send(part)


@bot.command(name="onboard")
async def onboard(ctx, target: discord.Member = None):
    target_text = target.mention if target else "new members"
    prompt = (
        f"Create a warm, premium Discord onboarding message for {target_text}. "
        "Include welcome, how to get help, rules reminder, and first 3 things to do."
    )
    async with ctx.typing():
        reply = await ai_response(prompt, ctx.author.id, ctx.guild.id if ctx.guild else 0)
    await ctx.send("🌸 **SpringBot Onboarding Draft**\n" + reply)


@bot.command(name="projectplan")
async def projectplan(ctx, *, idea: str):
    prompt = (
        f"Turn this idea into a serious build plan: {idea}\n"
        "Include phases, features, tech stack, commands/endpoints, database tables, deployment steps, and what to build first."
    )
    async with ctx.typing():
        reply = await ai_response(prompt, ctx.author.id, ctx.guild.id if ctx.guild else 0)
    for part in chunk_text("🚀 **SpringBot Project Plan**\n" + reply):
        await ctx.send(part)


@bot.command(name="brainstorm")
async def brainstorm(ctx, *, idea: str):
    prompt = f"Brainstorm 15 strong feature ideas for this project: {idea}. Rank them by impact, difficulty, and monetization potential."
    async with ctx.typing():
        reply = await ai_response(prompt, ctx.author.id, ctx.guild.id if ctx.guild else 0)
    for part in chunk_text("💡 **SpringBot Brainstorm**\n" + reply):
        await ctx.send(part)


@bot.command(name="fixidea")
async def fixidea(ctx, *, problem: str):
    prompt = f"Diagnose this problem and give a practical fix plan: {problem}. Include likely causes, checks, commands, and safest next step."
    async with ctx.typing():
        reply = await ai_response(prompt, ctx.author.id, ctx.guild.id if ctx.guild else 0)
    for part in chunk_text("🛠️ **SpringBot Fix Plan**\n" + reply):
        await ctx.send(part)


@bot.command(name="uptime2")
async def uptime2(ctx):
    await ctx.send(f"SpringBot V2 uptime: `{format_uptime()}`")


@bot.event
async def on_message(message):
    if message.author.bot:
        return

    if message.guild:
        automod_status = get_guild_setting(message.guild.id, "automod", "off")
        if automod_status == "on":
            severity, reason = detect_risky_message(message.content)
            if severity:
                log_incident(message.guild.id, message.channel.id, message.author.id, message.content, reason, severity)
                try:
                    if severity == "high":
                        await message.delete()
                        await message.channel.send(
                            f"🛡️ {message.author.mention}, SpringBot removed a risky message: **{reason}**",
                            delete_after=10,
                        )
                except discord.Forbidden:
                    await message.channel.send("SpringBot detected a risky message but does not have permission to delete it.")

    await bot.process_commands(message)

    if not message.guild:
        return

    if bot.user and bot.user.mentioned_in(message):
        cleaned = message.content.replace(f"<@{bot.user.id}>", "").replace(f"<@!{bot.user.id}>", "").strip()
        if cleaned:
            add_conversation(message.author.id, message.guild.id, message.channel.id, "user", cleaned)
            async with message.channel.typing():
                reply = await ai_response(cleaned, message.author.id, message.guild.id)
            add_conversation(message.author.id, message.guild.id, message.channel.id, "assistant", reply)
            for part in chunk_text(reply):
                await message.channel.send(part)


@bot.event
async def on_command_error(ctx, error):
    if isinstance(error, commands.MissingPermissions):
        await ctx.send("You do not have permission to use that command.")
    elif isinstance(error, commands.MissingRequiredArgument):
        await ctx.send("Missing required information. Try `!v2help`.")
    elif isinstance(error, commands.CommandNotFound):
        return
    else:
        await ctx.send(f"SpringBot error: `{error}`")


if __name__ == "__main__":
    if not TOKEN:
        raise RuntimeError("Missing DISCORD_TOKEN environment variable.")
    setup_database()
    bot.run(TOKEN)
