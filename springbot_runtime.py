import asyncio
import logging
import os
from datetime import datetime, timezone

import discord
from aiohttp import web
from discord.ext import commands

import bot_v2 as core

VERSION = "2.1.0"
PORT = int(os.getenv("PORT", "8000"))
HOST = os.getenv("HEALTH_HOST", "0.0.0.0")
STARTED_AT = datetime.now(timezone.utc)
LAST_READY_AT = None

bot = core.bot
TOKEN = core.TOKEN

logging.basicConfig(
    level=os.getenv("LOG_LEVEL", "INFO").upper(),
    format="%(asctime)s %(levelname)s %(name)s: %(message)s",
)
logger = logging.getLogger("springbot.runtime")


def uptime_seconds() -> int:
    return max(0, int((datetime.now(timezone.utc) - STARTED_AT).total_seconds()))


def setup_runtime_database() -> None:
    core.setup_database()
    with core.db_connect() as conn:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS feedback (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                guild_id TEXT NOT NULL,
                channel_id TEXT NOT NULL,
                user_id TEXT NOT NULL,
                message TEXT NOT NULL,
                created_at TEXT NOT NULL
            )
            """
        )
        conn.commit()


def database_is_healthy() -> bool:
    try:
        with core.db_connect() as conn:
            conn.execute("SELECT 1").fetchone()
        return True
    except Exception:
        logger.exception("Database health check failed")
        return False


def health_payload() -> dict:
    latency_ms = round(bot.latency * 1000, 1) if bot.is_ready() else None
    return {
        "service": "springbot",
        "version": VERSION,
        "ready": bot.is_ready(),
        "connected": not bot.is_closed(),
        "latency_ms": latency_ms,
        "guilds": len(bot.guilds),
        "users_visible": len(bot.users),
        "database_ok": database_is_healthy(),
        "ai_configured": bool(core.client),
        "uptime_seconds": uptime_seconds(),
        "last_ready_at": LAST_READY_AT.isoformat() if LAST_READY_AT else None,
    }


async def root_handler(_: web.Request) -> web.Response:
    return web.json_response({"service": "SpringBot", "version": VERSION, "health": "/health"})


async def health_handler(_: web.Request) -> web.Response:
    payload = health_payload()
    status = 200 if payload["ready"] and payload["database_ok"] else 503
    return web.json_response(payload, status=status)


async def start_health_server() -> web.AppRunner:
    app = web.Application()
    app.router.add_get("/", root_handler)
    app.router.add_get("/health", health_handler)
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, HOST, PORT)
    await site.start()
    logger.info("Health server listening on %s:%s", HOST, PORT)
    return runner


async def runtime_ready() -> None:
    global LAST_READY_AT
    LAST_READY_AT = datetime.now(timezone.utc)
    logger.info(
        "SpringBot connected as %s in %s guild(s) with %.1fms latency",
        bot.user,
        len(bot.guilds),
        bot.latency * 1000,
    )


async def runtime_disconnect() -> None:
    logger.warning("SpringBot disconnected from Discord; discord.py will attempt to reconnect")


async def runtime_resumed() -> None:
    logger.info("SpringBot Discord session resumed")


async def welcome_member(member: discord.Member) -> None:
    channel_id = core.get_guild_setting(member.guild.id, "welcome_channel_id")
    if not channel_id:
        return

    channel = member.guild.get_channel(int(channel_id))
    if not isinstance(channel, discord.TextChannel):
        return

    embed = discord.Embed(
        title="🌸 Welcome to the server!",
        description=(
            f"Welcome {member.mention}! Please review the rules, introduce yourself, "
            f"and use `{core.PREFIX}v2help` to see what SpringBot can do."
        ),
        color=discord.Color.green(),
        timestamp=datetime.now(timezone.utc),
    )
    embed.set_thumbnail(url=member.display_avatar.url)
    await channel.send(embed=embed)


bot.add_listener(runtime_ready, "on_ready")
bot.add_listener(runtime_disconnect, "on_disconnect")
bot.add_listener(runtime_resumed, "on_resumed")
bot.add_listener(welcome_member, "on_member_join")


@bot.command(name="ping", aliases=["status", "health"])
@commands.cooldown(1, 5, commands.BucketType.user)
async def ping(ctx: commands.Context) -> None:
    payload = health_payload()
    state = "Online" if payload["ready"] else "Connecting"
    embed = discord.Embed(
        title="🌸 SpringBot Status",
        color=discord.Color.green() if payload["ready"] else discord.Color.orange(),
        timestamp=datetime.now(timezone.utc),
    )
    embed.add_field(name="State", value=state, inline=True)
    embed.add_field(name="Latency", value=f"{payload['latency_ms']} ms" if payload["latency_ms"] is not None else "N/A", inline=True)
    embed.add_field(name="Uptime", value=core.format_uptime(), inline=True)
    embed.add_field(name="Servers", value=str(payload["guilds"]), inline=True)
    embed.add_field(name="Database", value="Healthy" if payload["database_ok"] else "Error", inline=True)
    embed.add_field(name="AI", value="Connected" if payload["ai_configured"] else "Not configured", inline=True)
    embed.set_footer(text=f"SpringBot {VERSION}")
    await ctx.send(embed=embed)


@bot.command(name="poll")
@commands.cooldown(1, 15, commands.BucketType.user)
async def poll(ctx: commands.Context, *, text: str) -> None:
    parts = [part.strip() for part in text.split("|") if part.strip()]
    if len(parts) < 3:
        await ctx.send(f"Use: `{core.PREFIX}poll Question | Option 1 | Option 2`")
        return

    question, options = parts[0], parts[1:]
    if len(options) > 10:
        await ctx.send("Polls can have up to 10 options.")
        return

    emoji_numbers = ["1️⃣", "2️⃣", "3️⃣", "4️⃣", "5️⃣", "6️⃣", "7️⃣", "8️⃣", "9️⃣", "🔟"]
    description = "\n".join(f"{emoji_numbers[i]} {option}" for i, option in enumerate(options))
    embed = discord.Embed(title=f"📊 {question[:250]}", description=description, color=discord.Color.blurple())
    embed.set_footer(text=f"Poll by {ctx.author.display_name}")
    message = await ctx.send(embed=embed)

    try:
        for emoji in emoji_numbers[: len(options)]:
            await message.add_reaction(emoji)
    except discord.Forbidden:
        await ctx.send("I created the poll, but I need **Add Reactions** permission to add voting buttons.")


@bot.command(name="setwelcome")
@commands.has_permissions(manage_guild=True)
async def setwelcome(ctx: commands.Context, channel: discord.TextChannel = None) -> None:
    target = channel or ctx.channel
    if not isinstance(target, discord.TextChannel):
        await ctx.send("Choose a text channel for welcome messages.")
        return
    core.set_guild_setting(ctx.guild.id, "welcome_channel_id", target.id)
    await ctx.send(f"Welcome messages will now be sent in {target.mention}.")


@bot.command(name="welcomeoff")
@commands.has_permissions(manage_guild=True)
async def welcomeoff(ctx: commands.Context) -> None:
    core.set_guild_setting(ctx.guild.id, "welcome_channel_id", "")
    await ctx.send("Automatic welcome messages are now off.")


@bot.command(name="feedback")
@commands.cooldown(1, 30, commands.BucketType.user)
async def feedback(ctx: commands.Context, *, message: str) -> None:
    cleaned = message.strip()[:1000]
    if not cleaned:
        await ctx.send("Tell me what you would like improved.")
        return

    with core.db_connect() as conn:
        conn.execute(
            "INSERT INTO feedback (guild_id, channel_id, user_id, message, created_at) VALUES (?, ?, ?, ?, ?)",
            (
                str(ctx.guild.id if ctx.guild else 0),
                str(ctx.channel.id),
                str(ctx.author.id),
                cleaned,
                core.now_iso(),
            ),
        )
        conn.commit()
    await ctx.send("Thanks — your SpringBot feedback was saved.")


@bot.command(name="close")
async def close_ticket(ctx: commands.Context) -> None:
    if not ctx.guild or not isinstance(ctx.channel, discord.TextChannel):
        await ctx.send("This command only works inside a server ticket channel.")
        return

    with core.db_connect() as conn:
        row = conn.execute(
            "SELECT * FROM tickets WHERE guild_id=? AND channel_id=? AND status='open' ORDER BY id DESC LIMIT 1",
            (str(ctx.guild.id), str(ctx.channel.id)),
        ).fetchone()

    if not row:
        await ctx.send("This channel is not an open SpringBot ticket.")
        return

    is_owner = str(ctx.author.id) == row["user_id"]
    can_manage = ctx.author.guild_permissions.manage_channels
    if not is_owner and not can_manage:
        await ctx.send("Only the ticket owner or a moderator can close this ticket.")
        return

    with core.db_connect() as conn:
        conn.execute("UPDATE tickets SET status='closed' WHERE id=?", (row["id"],))
        conn.commit()

    await ctx.send("Closing this ticket in 5 seconds…")
    await asyncio.sleep(5)
    try:
        await ctx.channel.delete(reason=f"SpringBot ticket closed by {ctx.author}")
    except discord.Forbidden:
        await ctx.send("I marked the ticket closed, but I need **Manage Channels** permission to delete it.")


@bot.command(name="diagnose", aliases=["doctor"])
@commands.has_permissions(manage_guild=True)
async def diagnose(ctx: commands.Context) -> None:
    payload = health_payload()
    checks = [
        ("Discord token", bool(TOKEN)),
        ("Discord connection", payload["ready"]),
        ("Database", payload["database_ok"]),
        ("AI key", payload["ai_configured"]),
        ("Message Content intent", bot.intents.message_content),
        ("Members intent", bot.intents.members),
    ]
    lines = [f"{'✅' if ok else '⚠️'} **{name}:** {'OK' if ok else 'Needs attention'}" for name, ok in checks]
    await ctx.send("🩺 **SpringBot Diagnostics**\n" + "\n".join(lines))


async def main() -> None:
    if not TOKEN:
        raise RuntimeError("Missing DISCORD_TOKEN environment variable.")

    setup_runtime_database()
    health_runner = await start_health_server()
    try:
        await bot.start(TOKEN, reconnect=True)
    finally:
        await health_runner.cleanup()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("SpringBot stopped")
