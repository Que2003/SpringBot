import os
import json
import random
import re
from pathlib import Path
from datetime import datetime, timedelta, timezone

import discord
from discord.ext import commands

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass


TOKEN = os.getenv("DISCORD_TOKEN")
PREFIX = "!"

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
    "{target.mention}, you look like you say 'let me cook' and then burn cereal.",
    "{target.mention}, you move like a loading bar stuck at 99%.",
    "{target.mention}, you are built like a Terms and Conditions page.",
    "{target.mention}, even NPCs have better dialogue than you.",
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
    "It is what it is.",
    "Not looking good.",
]

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
    if not channel_id:
        return None
    return guild.get_channel(channel_id)


def get_goodbye_channel(guild: discord.Guild):
    channel_id = config.get("goodbye_channel")
    if not channel_id:
        return None
    return guild.get_channel(channel_id)


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
        value=(
            "`!help`\n"
            "`!about`\n"
            "`!ping`\n"
            "`!uptime`\n"
            "`!prefix`"
        ),
        inline=False
    )

    embed.add_field(
        name="Server",
        value=(
            "`!rules`\n"
            "`!welcome`\n"
            "`!goodbye`\n"
            "`!setwelcome`\n"
            "`!setgoodbye`\n"
            "`!testwelcome`\n"
            "`!testgoodbye`"
        ),
        inline=False
    )

    embed.add_field(
        name="Utility",
        value=(
            "`!userinfo`\n"
            "`!serverinfo`\n"
            "`!membercount`\n"
            "`!avatar`"
        ),
        inline=False
    )

    embed.add_field(
        name="Fun",
        value=(
            "`!roast`\n"
            "`!8ball`\n"
            "`!coinflip`\n"
            "`!roll`"
        ),
        inline=False
    )

    embed.add_field(
        name="Economy",
        value=(
            "`!balance`\n"
            "`!daily`"
        ),
        inline=False
    )

    embed.add_field(
        name="Voice",
        value=(
            "`!join`\n"
            "`!leave`"
        ),
        inline=False
    )

    embed.add_field(
        name="Moderation",
        value=(
            "`!ban`\n"
            "`!kick`\n"
            "`!purge`"
        ),
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
    save_config(config)
    await ctx.send(f"✅ Welcome channel set to {channel.mention}")


async def set_goodbye_channel_logic(ctx, channel: discord.TextChannel) -> None:
    config["goodbye_channel"] = channel.id
    save_config(config)
    await ctx.send(f"✅ Goodbye channel set to {channel.mention}")


@bot.event
async def on_ready():
    print(f"LOGGED IN AS: {bot.user}")
    await bot.change_presence(activity=discord.Game(name="SpringBot | !help"))


@bot.event
async def on_member_join(member: discord.Member):
    channel = get_welcome_channel(member.guild)
    if not channel:
        return

    messages = config.get("welcome_messages", DEFAULT_WELCOME_MESSAGES)
    message = random.choice(messages).format(member=member)
    await channel.send(message)


@bot.event
async def on_member_remove(member: discord.Member):
    channel = get_goodbye_channel(member.guild)
    if not channel:
        return

    messages = config.get("goodbye_messages", DEFAULT_GOODBYE_MESSAGES)
    message = random.choice(messages).format(member=member)
    await channel.send(message)


@bot.command(name="help")
async def help_command(ctx):
    await ctx.send(embed=build_help_embed())


@bot.command(name="about")
async def about_command(ctx):
    embed = discord.Embed(
        title="About SpringBot",
        description=(
            "SpringBot is a multi-purpose Discord bot with moderation, "
            "welcome/goodbye, utility, fun, economy, and voice join features."
        ),
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
    embed = discord.Embed(
        title="📜 Server Rules",
        description=rules_text,
        color=discord.Color.green()
    )
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
    if current_channel:
        await ctx.send(f"🌸 Welcome channel is currently set to {current_channel.mention}")
    else:
        await ctx.send(f"No welcome channel is set yet. Use `{PREFIX}welcome #channel`.")


@bot.command(name="goodbye")
async def goodbye_command(ctx, channel: discord.TextChannel = None):
    if channel is not None:
        if not ctx.author.guild_permissions.administrator:
            await ctx.send("You need administrator permission to set the goodbye channel.")
            return
        await set_goodbye_channel_logic(ctx, channel)
        return

    current_channel = get_goodbye_channel(ctx.guild)
    if current_channel:
        await ctx.send(f"🍃 Goodbye channel is currently set to {current_channel.mention}")
    else:
        await ctx.send(f"No goodbye channel is set yet. Use `{PREFIX}goodbye #channel`.")


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
    messages = config.get("welcome_messages", DEFAULT_WELCOME_MESSAGES)
    message = random.choice(messages).format(member=ctx.author)
    await ctx.send(message)


@bot.command(name="testgoodbye")
@commands.has_permissions(administrator=True)
async def testgoodbye_command(ctx):
    messages = config.get("goodbye_messages", DEFAULT_GOODBYE_MESSAGES)
    message = random.choice(messages).format(member=ctx.author)
    await ctx.send(message)


@bot.command(name="userinfo")
async def userinfo_command(ctx, member: discord.Member = None):
    member = member or ctx.author

    embed = discord.Embed(
        title=f"User Info - {member}",
        color=discord.Color.green()
    )
    embed.set_thumbnail(url=member.display_avatar.url)
    embed.add_field(name="Username", value=str(member), inline=True)
    embed.add_field(name="Display Name", value=member.display_name, inline=True)
    embed.add_field(name="ID", value=member.id, inline=False)
    embed.add_field(
        name="Joined Server",
        value=member.joined_at.strftime("%Y-%m-%d %H:%M:%S") if member.joined_at else "Unknown",
        inline=False
    )
    embed.add_field(
        name="Account Created",
        value=member.created_at.strftime("%Y-%m-%d %H:%M:%S"),
        inline=False
    )

    roles = [role.mention for role in member.roles if role.name != "@everyone"]
    embed.add_field(
        name="Roles",
        value=", ".join(roles[:15]) if roles else "No roles",
        inline=False
    )

    await ctx.send(embed=embed)


@bot.command(name="serverinfo")
async def serverinfo_command(ctx):
    guild = ctx.guild

    embed = discord.Embed(
        title=f"Server Info - {guild.name}",
        color=discord.Color.green()
    )

    if guild.icon:
        embed.set_thumbnail(url=guild.icon.url)

    embed.add_field(name="Server Name", value=guild.name, inline=True)
    embed.add_field(name="Server ID", value=guild.id, inline=True)
    embed.add_field(name="Owner", value=str(guild.owner), inline=False)
    embed.add_field(name="Members", value=guild.member_count, inline=True)
    embed.add_field(name="Roles", value=len(guild.roles), inline=True)
    embed.add_field(name="Channels", value=len(guild.channels), inline=True)
    embed.add_field(name="Created", value=guild.created_at.strftime("%Y-%m-%d %H:%M:%S"), inline=False)

    await ctx.send(embed=embed)


@bot.command(name="membercount")
async def membercount_command(ctx):
    await ctx.send(f"👥 Member count: **{ctx.guild.member_count}**")


@bot.command(name="avatar")
async def avatar_command(ctx, member: discord.Member = None):
    member = member or ctx.author
    embed = discord.Embed(
        title=f"{member.display_name}'s Avatar",
        color=discord.Color.green()
    )
    embed.set_image(url=member.display_avatar.url)
    await ctx.send(embed=embed)


@bot.command(name="ask")
async def ask_command(ctx, *, question: str):
    await ctx.send(
        f"🤖 AI system not connected yet.\n"
        f"You asked: `{question}`"
    )


@bot.command(name="roast")
async def roast_command(ctx, member: discord.Member = None):
    target = member or ctx.author
    if target == bot.user:
        await ctx.send("Nice try. I am not roasting myself.")
        return

    line = random.choice(ROAST_LINES).format(target=target)
    await ctx.send(line)


@bot.command(name="8ball")
async def eightball_command(ctx, *, question: str):
    answer = random.choice(EIGHT_BALL_ANSWERS)
    embed = discord.Embed(
        title="🎱 Magic 8-Ball",
        color=discord.Color.green()
    )
    embed.add_field(name="Question", value=question, inline=False)
    embed.add_field(name="Answer", value=answer, inline=False)
    await ctx.send(embed=embed)


@bot.command(name="coinflip")
async def coinflip_command(ctx):
    result = random.choice(["Heads", "Tails"])
    await ctx.send(f"🪙 Coinflip result: **{result}**")


@bot.command(name="roll")
async def roll_command(ctx, dice: str = "1d6"):
    dice = dice.lower().strip()

    if re.fullmatch(r"\d+", dice):
        sides = int(dice)
        if sides < 2 or sides > 1000:
            await ctx.send("Use a number between 2 and 1000.")
            return
        result = random.randint(1, sides)
        await ctx.send(f"🎲 You rolled **{result}** on a **1d{sides}**.")
        return

    match = re.fullmatch(r"(\d+)d(\d+)", dice)
    if not match:
        await ctx.send("Use `!roll 1d6`, `!roll 2d20`, or `!roll 100`.")
        return

    count = int(match.group(1))
    sides = int(match.group(2))

    if count < 1 or count > 20:
        await ctx.send("Number of dice must be between 1 and 20.")
        return

    if sides < 2 or sides > 1000:
        await ctx.send("Number of sides must be between 2 and 1000.")
        return

    rolls = [random.randint(1, sides) for _ in range(count)]
    total = sum(rolls)
    await ctx.send(
        f"🎲 Rolled **{count}d{sides}**: {', '.join(map(str, rolls))}\n"
        f"**Total:** {total}"
    )


@bot.command(name="balance")
async def balance_command(ctx, member: discord.Member = None):
    member = member or ctx.author
    user_record = get_user_record(member.id)
    save_economy(economy)

    embed = discord.Embed(
        title="💰 Balance",
        description=f"{member.mention} has **{user_record['wallet']} SpringCoins**.",
        color=discord.Color.green()
    )
    await ctx.send(embed=embed)


@bot.command(name="daily")
async def daily_command(ctx):
    user_record = get_user_record(ctx.author.id)
    now = datetime.now(timezone.utc)
    last_daily_str = user_record.get("last_daily")

    if last_daily_str:
        last_daily = datetime.fromisoformat(last_daily_str)
        next_claim = last_daily + timedelta(hours=24)
        if now < next_claim:
            remaining = next_claim - now
            hours, rem = divmod(int(remaining.total_seconds()), 3600)
            minutes, _ = divmod(rem, 60)
            await ctx.send(f"⏳ You already claimed your daily. Try again in **{hours}h {minutes}m**.")
            return

    reward = random.randint(100, 250)
    user_record["wallet"] += reward
    user_record["last_daily"] = now.isoformat()
    save_economy(economy)

    await ctx.send(
        f"💸 {ctx.author.mention} claimed **{reward} SpringCoins**.\n"
        f"New balance: **{user_record['wallet']} SpringCoins**."
    )


@bot.command(name="join")
async def join_command(ctx):
    if not ctx.author.voice or not ctx.author.voice.channel:
        await ctx.send("Join a voice channel first, then use `!join`.")
        return

    voice_channel = ctx.author.voice.channel
    voice_client = ctx.guild.voice_client

    me = ctx.guild.me or ctx.guild.get_member(bot.user.id)
    permissions = voice_channel.permissions_for(me)

    if not permissions.connect:
        await ctx.send("I do not have permission to connect to that voice channel.")
        return

    if not permissions.speak:
        await ctx.send("I do not have permission to speak in that voice channel.")
        return

    try:
        if voice_client and voice_client.is_connected():
            if voice_client.channel == voice_channel:
                await ctx.send(f"Already in **{voice_channel.name}**.")
                return

            await voice_client.move_to(voice_channel)
            await ctx.send(f"Moved to **{voice_channel.name}**.")
            return

        await voice_channel.connect()
        await ctx.send(f"Joined **{voice_channel.name}**.")
    except discord.ClientException as e:
        await ctx.send(f"Voice error: {e}")
    except discord.Forbidden:
        await ctx.send("Discord blocked the join because my permissions are missing.")
    except Exception as e:
        await ctx.send(f"Could not join voice: {e}")


@bot.command(name="leave")
async def leave_command(ctx):
    voice_client = ctx.guild.voice_client

    if not voice_client or not voice_client.is_connected():
        await ctx.send("I am not in a voice channel.")
        return

    channel_name = voice_client.channel.name
    await voice_client.disconnect()
    await ctx.send(f"Left **{channel_name}**.")


@bot.command(name="ban")
@commands.has_permissions(ban_members=True)
async def ban_command(ctx, member: discord.Member, *, reason: str = "No reason provided."):
    if member == ctx.author:
        await ctx.send("You cannot ban yourself.")
        return

    if member == ctx.guild.owner:
        await ctx.send("You cannot ban the server owner.")
        return

    try:
        await member.ban(reason=f"{reason} | Banned by {ctx.author}")
        await ctx.send(f"🔨 Banned **{member}** | Reason: {reason}")
    except discord.Forbidden:
        await ctx.send("I do not have permission to ban that member.")


@bot.command(name="kick")
@commands.has_permissions(kick_members=True)
async def kick_command(ctx, member: discord.Member, *, reason: str = "No reason provided."):
    if member == ctx.author:
        await ctx.send("You cannot kick yourself.")
        return

    if member == ctx.guild.owner:
        await ctx.send("You cannot kick the server owner.")
        return

    try:
        await member.kick(reason=f"{reason} | Kicked by {ctx.author}")
        await ctx.send(f"👢 Kicked **{member}** | Reason: {reason}")
    except discord.Forbidden:
        await ctx.send("I do not have permission to kick that member.")


@bot.command(name="purge")
@commands.has_permissions(manage_messages=True)
async def purge_command(ctx, amount: int):
    if amount < 1 or amount > 200:
        await ctx.send("Choose a number between 1 and 200.")
        return

    deleted = await ctx.channel.purge(limit=amount + 1)
    msg = await ctx.send(f"🧹 Deleted **{len(deleted) - 1}** messages.", delete_after=5)
    try:
        await msg.delete(delay=5)
    except discord.HTTPException:
        pass


@bot.event
async def on_command_error(ctx, error):
    if isinstance(error, commands.CommandNotFound):
        await ctx.send(f"Unknown command. Use `{PREFIX}help`.")
        return

    if isinstance(error, commands.MissingPermissions):
        await ctx.send("You do not have permission to use that command.")
        return

    if isinstance(error, commands.MissingRequiredArgument):
        await ctx.send("Missing arguments for that command.")
        return

    if isinstance(error, commands.BadArgument):
        await ctx.send("Invalid argument for that command.")
        return

    raise error


if not TOKEN:
    raise ValueError("DISCORD_TOKEN is missing from your environment variables.")

bot.run(TOKEN)
