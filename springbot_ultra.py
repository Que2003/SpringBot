import asyncio
import logging
import os

import discord
from discord.ext import commands

import springbot_runtime as runtime

VERSION = "3.0.0"
DEFAULT_EXTENSIONS = ("cogs.music", "cogs.entertainment")
EXTENSION_ERRORS: dict[str, str] = {}

bot = runtime.bot
TOKEN = runtime.TOKEN
runtime.VERSION = VERSION
logger = logging.getLogger("springbot.ultra")


def configured_extensions() -> list[str]:
    raw = os.getenv("SPRINGBOT_EXTENSIONS", "")
    if not raw.strip():
        return list(DEFAULT_EXTENSIONS)
    return [item.strip() for item in raw.split(",") if item.strip()]


async def load_features(*, reload_existing: bool = False) -> None:
    EXTENSION_ERRORS.clear()
    for extension in configured_extensions():
        try:
            if extension in bot.extensions:
                if reload_existing:
                    await bot.reload_extension(extension)
                continue
            await bot.load_extension(extension)
            logger.info("Loaded feature extension %s", extension)
        except Exception as exc:
            EXTENSION_ERRORS[extension] = f"{type(exc).__name__}: {exc}"
            logger.exception("Could not load feature extension %s", extension)


async def ultra_ready() -> None:
    await bot.change_presence(
        activity=discord.Game(name=f"{runtime.core.PREFIX}ultrahelp | music + games")
    )
    logger.info(
        "SpringBot Ultra %s ready with extensions: %s",
        VERSION,
        ", ".join(sorted(bot.extensions)) or "none",
    )


bot.add_listener(ultra_ready, "on_ready")


@bot.command(name="ultrahelp", aliases=["springhelp"])
async def ultrahelp(ctx: commands.Context) -> None:
    prefix = runtime.core.PREFIX
    embed = discord.Embed(
        title="🌸 SpringBot Ultra 3.0",
        description="AI assistance, server tools, music playback, and built-in entertainment.",
        color=discord.Color.green(),
    )
    embed.add_field(
        name="AI & Productivity",
        value=(
            f"`{prefix}springai <message>` · `{prefix}study <topic>` · `{prefix}summarize [amount]`\n"
            f"`{prefix}remind 10m <message>` · `{prefix}projectplan <idea>` · `{prefix}dailybrief`"
        ),
        inline=False,
    )
    embed.add_field(
        name="Music",
        value=(
            f"`{prefix}play <song/link>` · `{prefix}pause` · `{prefix}resume` · `{prefix}skip`\n"
            f"`{prefix}queue` · `{prefix}stop` · `{prefix}leave` · `{prefix}musichelp`"
        ),
        inline=False,
    )
    embed.add_field(
        name="Entertainment",
        value=(
            f"`{prefix}trivia` · `{prefix}rps` · `{prefix}guess` · `{prefix}slots` · `{prefix}8ball`\n"
            f"`{prefix}wyr` · `{prefix}joke` · `{prefix}truth` · `{prefix}dare` · `{prefix}entertainment`"
        ),
        inline=False,
    )
    embed.add_field(
        name="Server Tools",
        value=(
            f"`{prefix}ticket` · `{prefix}automod on/off` · `{prefix}serverhealth` · `{prefix}poll`\n"
            f"`{prefix}setwelcome` · `{prefix}diagnose` · `{prefix}featurestatus`"
        ),
        inline=False,
    )
    embed.set_footer(text=f"SpringBot {VERSION} | Prefix: {prefix}")
    await ctx.send(embed=embed)


@bot.command(name="featurestatus", aliases=["modules"])
async def featurestatus(ctx: commands.Context) -> None:
    loaded = sorted(bot.extensions)
    lines = [f"✅ `{name}`" for name in loaded]
    lines.extend(f"❌ `{name}` — {error[:180]}" for name, error in EXTENSION_ERRORS.items())
    if not lines:
        lines = ["No feature modules are loaded."]
    await ctx.send("🧩 **SpringBot Feature Modules**\n" + "\n".join(lines))


@bot.command(name="reloadfeatures")
@commands.has_permissions(manage_guild=True)
async def reloadfeatures(ctx: commands.Context) -> None:
    await load_features(reload_existing=True)
    if EXTENSION_ERRORS:
        details = "\n".join(
            f"• `{name}`: {error[:180]}" for name, error in EXTENSION_ERRORS.items()
        )
        await ctx.send("Feature reload completed with errors:\n" + details)
    else:
        await ctx.send("✅ Music and entertainment features reloaded successfully.")


async def main() -> None:
    if not TOKEN:
        raise RuntimeError("Missing DISCORD_TOKEN environment variable.")

    runtime.setup_runtime_database()
    await load_features()
    health_runner = await runtime.start_health_server()
    try:
        await bot.start(TOKEN, reconnect=True)
    finally:
        await health_runner.cleanup()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("SpringBot Ultra stopped")
