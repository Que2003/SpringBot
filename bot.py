import os
import json
import random
import re
from pathlib import Path

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

DEFAULT_CONFIG = {
    "welcome_channel": None,
    "goodbye_channel": None
}

SPRINGBOT_RULES = [
    "Be respectful to everyone.",
    "No hate speech, racism, or harassment.",
    "No spam or excessive self-promotion.",
    "Keep content in the correct channels.",
    "Use common sense and listen to staff.",
]

WELCOME_MESSAGES = [
    "🌸 Welcome to the server, {member.mention}! SpringBot is glad you're here.",
    "🌿 A new member has joined: {member.mention}. Welcome in.",
    "☀️ Everybody welcome {member.mention} to the server.",
    "🌷 Fresh energy just arrived. Welcome, {member.mention}.",
]

GOODBYE_MESSAGES = [
    "🍃 {member} has left the server.",
    "🌙 Goodbye, {member}.",
    "🌧️ {member} has departed. SpringBot will remember you.",
    "🌸 {member} left the garden.",
]

COMMAND_CATEGORIES = {
    "Core / Help": [
        ("help", "Show the main help menu"),
        ("springhelp", "Show the SpringBot help menu"),
        ("about", "Show what SpringBot does"),
        ("invite", "Show the bot invite link"),
        ("support", "Show support information"),
        ("prefix", "Show the current prefix"),
    ],
    "Welcome / Server": [
        ("setwelcome", "Set the welcome channel"),
        ("setgoodbye", "Set the goodbye channel"),
        ("testwelcome", "Test the welcome message"),
        ("testgoodbye", "Test the goodbye message"),
        ("autorole", "Set an auto-role for new members"),
        ("reactionroles", "Manage reaction roles"),
        ("rules", "Show server rules"),
        ("serverrules", "Show server rules"),
        ("announce", "Send an announcement"),
        ("suggest", "Send a suggestion"),
        ("poll", "Create a poll"),
        ("giveaway", "Start a giveaway"),
    ],
    "Moderation": [
        ("ban", "Ban a member"),
        ("unban", "Unban a member"),
        ("kick", "Kick a member"),
        ("timeout", "Timeout a member"),
        ("untimeout", "Remove timeout from a member"),
        ("mute", "Mute a member"),
        ("unmute", "Unmute a member"),
        ("warn", "Warn a member"),
        ("warnings", "View warnings"),
        ("clearwarns", "Clear a member's warnings"),
        ("purge", "Delete messages"),
        ("slowmode", "Set slowmode"),
        ("lock", "Lock a channel"),
        ("unlock", "Unlock a channel"),
        ("nick", "Change a nickname"),
        ("role", "Add a role"),
        ("removerole", "Remove a role"),
        ("modlogs", "Show moderation logs"),
    ],
    "Utility": [
        ("ping", "Check bot latency"),
        ("uptime", "Show bot uptime"),
        ("userinfo", "Show user information"),
        ("serverinfo", "Show server information"),
        ("membercount", "Show member count"),
        ("avatar", "Show a user's avatar"),
        ("banner", "Show a user's banner"),
        ("afk", "Set AFK status"),
        ("remind", "Create a reminder"),
        ("timezone", "Show or set timezone"),
        ("time", "Show time"),
        ("weather", "Show weather"),
        ("translate", "Translate text"),
        ("define", "Define a word"),
        ("calculate", "Calculate something"),
        ("qr", "Create a QR code"),
        ("shorten", "Shorten a link"),
    ],
    "Fun": [
        ("roast", "Roast someone"),
        ("compliment", "Compliment someone"),
        ("joke", "Tell a joke"),
        ("meme", "Get a meme"),
        ("gif", "Get a gif"),
        ("8ball", "Ask the magic 8-ball"),
        ("coinflip", "Flip a coin"),
        ("roll", "Roll dice"),
        ("rate", "Rate something"),
        ("ship", "Ship two people"),
        ("wyr", "Would you rather"),
        ("truth", "Truth question"),
        ("dare", "Dare challenge"),
        ("trivia", "Trivia question"),
        ("fact", "Random fact"),
    ],
    "Social / Interaction": [
        ("hug", "Hug someone"),
        ("pat", "Pat someone"),
        ("slap", "Slap someone"),
        ("poke", "Poke someone"),
        ("wave", "Wave at someone"),
        ("highfive", "High five someone"),
        ("kiss", "Kiss someone"),
        ("cry", "Show sadness"),
        ("laugh", "Laugh"),
        ("angry", "Show anger"),
    ],
    "Music": [
        ("join", "Join a voice channel"),
        ("leave", "Leave the voice channel"),
        ("play", "Play music"),
        ("pause", "Pause music"),
        ("resume", "Resume music"),
        ("skip", "Skip track"),
        ("stop", "Stop music"),
        ("queue", "Show queue"),
        ("nowplaying", "Show current song"),
        ("loop", "Loop track"),
        ("shuffle", "Shuffle queue"),
        ("remove", "Remove a song from queue"),
        ("seek", "Seek in a track"),
        ("volume", "Set volume"),
        ("lyrics", "Show lyrics"),
        ("replay", "Replay current song"),
        ("247", "Keep SpringBot in VC"),
    ],
    "Economy": [
        ("balance", "Show balance"),
        ("daily", "Claim daily reward"),
        ("weekly", "Claim weekly reward"),
        ("work", "Work for coins"),
        ("beg", "Beg for coins"),
        ("crime", "Risk coins"),
        ("rob", "Rob another member"),
        ("deposit", "Deposit coins"),
        ("withdraw", "Withdraw coins"),
        ("pay", "Pay another member"),
        ("shop", "Open the shop"),
        ("buy", "Buy an item"),
        ("sell", "Sell an item"),
        ("inventory", "View inventory"),
        ("leaderboard", "Economy leaderboard"),
        ("profile", "View profile"),
    ],
    "Casino / Games": [
        ("slots", "Play slots"),
        ("blackjack", "Play blackjack"),
        ("roulette", "Play roulette"),
        ("gamble", "Gamble coins"),
        ("bet", "Place a bet"),
        ("rps", "Rock paper scissors"),
        ("tictactoe", "Play tic tac toe"),
        ("connect4", "Play connect 4"),
        ("hangman", "Play hangman"),
        ("guess", "Guessing game"),
        ("mines", "Play mines"),
        ("dice", "Roll dice"),
    ],
    "Leveling": [
        ("rank", "Show rank"),
        ("level", "Show level"),
        ("leaderboardxp", "XP leaderboard"),
        ("setlevelrole", "Set role rewards"),
        ("removelevelrole", "Remove level role"),
        ("xpboost", "Boost XP"),
    ],
    "AI / Smart": [
        ("ask", "Ask SpringBot anything"),
        ("springai", "SpringBot AI command"),
        ("explain", "Explain a topic"),
        ("summarize", "Summarize text"),
        ("rewrite", "Rewrite text"),
        ("factcheck", "Fact-check something"),
        ("idea", "Generate ideas"),
        ("brainstorm", "Brainstorm ideas"),
        ("techhelp", "Tech support help"),
        ("codehelp", "Coding help"),
        ("historyhelp", "History help"),
        ("sciencehelp", "Science help"),
        ("mathhelp", "Math help"),
        ("bookhelp", "Book help"),
        ("moviehelp", "Movie help"),
        ("religionhelp", "Religion help"),
        ("news", "Latest news"),
    ],
    "Study": [
        ("study", "Study help"),
        ("quizme", "Quiz generator"),
        ("flashcards", "Flashcards"),
        ("notes", "Study notes"),
        ("topic", "Explain a topic"),
        ("examhelp", "Exam help"),
        ("question", "Answer a question"),
        ("studyplan", "Create a study plan"),
        ("term", "Define a term"),
        ("practice", "Practice questions"),
        ("revision", "Review material"),
        ("essayhelp", "Essay help"),
    ],
    "Health / Wellness": [
        ("mood", "Mood check"),
        ("breathe", "Breathing exercise"),
        ("hydrate", "Water reminder"),
        ("sleep", "Sleep tips"),
        ("motivate", "Motivation"),
        ("affirmation", "Positive affirmation"),
        ("journal", "Journal prompt"),
        ("checkin", "Daily check-in"),
        ("break", "Take a break"),
        ("focus", "Focus mode"),
        ("calm", "Calm down help"),
        ("vent", "Vent command"),
    ],
    "Media / Content": [
        ("quote", "Generate a quote"),
        ("caption", "Caption ideas"),
        ("clipidea", "Clip idea generator"),
        ("storyidea", "Story idea generator"),
        ("prompt", "Prompt generator"),
        ("thumbnailidea", "Thumbnail idea"),
        ("bio", "Bio generator"),
        ("tagline", "Tagline generator"),
        ("aesthetic", "Aesthetic ideas"),
        ("intro", "Intro text generator"),
    ],
    "Admin / Owner": [
        ("setstatus", "Set bot status"),
        ("addroast", "Add roast line"),
        ("addwelcome", "Add welcome line"),
        ("addgoodbye", "Add goodbye line"),
        ("reload", "Reload bot parts"),
        ("sync", "Sync commands"),
        ("blacklist", "Blacklist a user"),
        ("whitelist", "Whitelist a user"),
        ("disablecommand", "Disable a command"),
        ("enablecommand", "Enable a command"),
        ("setlogchannel", "Set log channel"),
        ("setmodrole", "Set mod role"),
        ("setdjrole", "Set DJ role"),
        ("shutdown", "Shut down the bot"),
    ],
}

REAL_COMMANDS = {
    "help",
    "springhelp",
    "about",
    "ping",
    "rules",
    "serverrules",
    "setwelcome",
    "setgoodbye",
    "testwelcome",
    "testgoodbye",
    "userinfo",
    "serverinfo",
    "membercount",
    "avatar",
    "ask",
    "support",
    "prefix",
}

MOD_ONLY = {
    "ban", "unban", "kick", "timeout", "untimeout", "mute", "unmute",
    "warn", "warnings", "clearwarns", "purge", "slowmode", "lock",
    "unlock", "nick", "role", "removerole", "modlogs", "announce",
    "poll", "giveaway"
}

ADMIN_ONLY = {
    "setwelcome", "setgoodbye", "autorole", "reactionroles"
}

OWNER_ONLY = {
    "setstatus", "addroast", "addwelcome", "addgoodbye", "reload", "sync",
    "blacklist", "whitelist", "disablecommand", "enablecommand",
    "setlogchannel", "setmodrole", "setdjrole", "shutdown"
}


def load_config():
    if not CONFIG_FILE.exists():
        CONFIG_FILE.write_text(json.dumps(DEFAULT_CONFIG, indent=4))
        return DEFAULT_CONFIG.copy()

    try:
        with open(CONFIG_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
            for key, value in DEFAULT_CONFIG.items():
                data.setdefault(key, value)
            return data
    except Exception:
        return DEFAULT_CONFIG.copy()


def save_config(data):
    with open(CONFIG_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=4)


config = load_config()

intents = discord.Intents.default()
intents.message_content = True
intents.members = True

bot = commands.Bot(command_prefix=PREFIX, intents=intents, help_command=None)


def get_category_embed(category_name: str) -> discord.Embed:
    commands_list = COMMAND_CATEGORIES[category_name]
    embed = discord.Embed(
        title=f"🌸 {category_name}",
        description=f"Use `{PREFIX}help` to return to the main menu.",
        color=discord.Color.green()
    )

    lines = [f"`{PREFIX}{name}` — {desc}" for name, desc in commands_list]
    embed.description += "\n\n" + "\n".join(lines)
    return embed


def get_main_help_embed() -> discord.Embed:
    embed = discord.Embed(
        title="🌸 SpringBot Command Menu",
        description=(
            f"Prefix: `{PREFIX}`\n"
            f"Use `{PREFIX}help <category>` to open a category.\n"
            "Example: `!help moderation`"
        ),
        color=discord.Color.green()
    )

    for category_name, commands_list in COMMAND_CATEGORIES.items():
        preview = ", ".join(f"`{PREFIX}{cmd}`" for cmd, _ in commands_list[:5])
        more_count = max(len(commands_list) - 5, 0)
        if more_count:
            preview += f" + {more_count} more"
        embed.add_field(name=category_name, value=preview, inline=False)

    return embed


def find_category(name: str):
    name = name.strip().lower()

    exact = {cat.lower(): cat for cat in COMMAND_CATEGORIES}
    if name in exact:
        return exact[name]

    for category in COMMAND_CATEGORIES:
        if name in category.lower():
            return category

    return None


@bot.event
async def on_ready():
    print(f"LOGGED IN AS: {bot.user}")
    await bot.change_presence(
        activity=discord.Game(name="SpringBot | !help")
    )


@bot.event
async def on_member_join(member: discord.Member):
    channel_id = config.get("welcome_channel")
    if not channel_id:
        return

    channel = member.guild.get_channel(channel_id)
    if channel:
        message = random.choice(WELCOME_MESSAGES).format(member=member)
        await channel.send(message)


@bot.event
async def on_member_remove(member: discord.Member):
    channel_id = config.get("goodbye_channel")
    if not channel_id:
        return

    channel = member.guild.get_channel(channel_id)
    if channel:
        message = random.choice(GOODBYE_MESSAGES).format(member=member)
        await channel.send(message)


@bot.command(name="help")
async def help_command(ctx, *, category: str = None):
    if category is None:
        await ctx.send(embed=get_main_help_embed())
        return

    matched = find_category(category)
    if not matched:
        await ctx.send(
            f"Category not found. Use `{PREFIX}help` to see all categories."
        )
        return

    await ctx.send(embed=get_category_embed(matched))


@bot.command(name="springhelp")
async def springhelp_command(ctx, *, category: str = None):
    await ctx.invoke(bot.get_command("help"), category=category)


@bot.command(name="about")
async def about_command(ctx):
    embed = discord.Embed(
        title="About SpringBot",
        description=(
            "SpringBot is a multi-purpose Discord bot built for moderation, music, "
            "fun, study help, wellness, economy, and smart assistant features."
        ),
        color=discord.Color.green()
    )
    await ctx.send(embed=embed)


@bot.command(name="support")
async def support_command(ctx):
    await ctx.send("Use `!help` to see every category and command.")


@bot.command(name="prefix")
async def prefix_command(ctx):
    await ctx.send(f"My current prefix is `{PREFIX}`")


@bot.command(name="ping")
async def ping_command(ctx):
    latency = round(bot.latency * 1000)
    await ctx.send(f"🏓 Pong: `{latency}ms`")


@bot.command(name="rules", aliases=["serverrules"])
async def rules_command(ctx):
    rules_text = "\n".join([f"**{i + 1}.** {rule}" for i, rule in enumerate(SPRINGBOT_RULES)])
    embed = discord.Embed(
        title="📜 Server Rules",
        description=rules_text,
        color=discord.Color.green()
    )
    await ctx.send(embed=embed)


@bot.command(name="setwelcome")
@commands.has_permissions(administrator=True)
async def setwelcome_command(ctx, channel: discord.TextChannel = None):
    channel = channel or ctx.channel
    config["welcome_channel"] = channel.id
    save_config(config)
    await ctx.send(f"✅ Welcome channel set to {channel.mention}")


@bot.command(name="setgoodbye")
@commands.has_permissions(administrator=True)
async def setgoodbye_command(ctx, channel: discord.TextChannel = None):
    channel = channel or ctx.channel
    config["goodbye_channel"] = channel.id
    save_config(config)
    await ctx.send(f"✅ Goodbye channel set to {channel.mention}")


@bot.command(name="testwelcome")
@commands.has_permissions(administrator=True)
async def testwelcome_command(ctx):
    message = random.choice(WELCOME_MESSAGES).format(member=ctx.author)
    await ctx.send(message)


@bot.command(name="testgoodbye")
@commands.has_permissions(administrator=True)
async def testgoodbye_command(ctx):
    message = random.choice(GOODBYE_MESSAGES).format(member=ctx.author)
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
    embed.add_field(name="Joined Server", value=member.joined_at.strftime("%Y-%m-%d %H:%M:%S") if member.joined_at else "Unknown", inline=False)
    embed.add_field(name="Account Created", value=member.created_at.strftime("%Y-%m-%d %H:%M:%S"), inline=False)

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
        f"🤖 **SpringBot AI placeholder**\n"
        f"You asked: `{question}`\n\n"
        "This command is ready in the structure. "
        "Next step is wiring it to your AI/API system."
    )


def make_stub_command(cmd_name: str, description: str):
    async def _stub(ctx, *, args: str = None):
        await ctx.send(
            f"`{PREFIX}{cmd_name}` is added to SpringBot's command structure.\n"
            f"Description: {description}\n"
            "The command exists in the menu right now, and its full logic can be built next."
        )

    safe_name = re.sub(r"\W|^(?=\d)", "_", f"stub_{cmd_name}")
    _stub.__name__ = safe_name

    if cmd_name in OWNER_ONLY:
        _stub = commands.is_owner()(_stub)
    elif cmd_name in ADMIN_ONLY:
        _stub = commands.has_permissions(administrator=True)(_stub)
    elif cmd_name in MOD_ONLY:
        _stub = commands.has_permissions(manage_messages=True)(_stub)

    return commands.command(name=cmd_name, help=description)(_stub)


for category_name, command_items in COMMAND_CATEGORIES.items():
    for cmd_name, cmd_desc in command_items:
        if cmd_name not in REAL_COMMANDS:
            bot.add_command(make_stub_command(cmd_name, cmd_desc))


@bot.event
async def on_command_error(ctx, error):
    if isinstance(error, commands.CommandNotFound):
        await ctx.send(f"Unknown command. Use `{PREFIX}help`.")
        return

    if isinstance(error, commands.MissingPermissions):
        await ctx.send("You do not have permission to use that command.")
        return

    if isinstance(error, commands.NotOwner):
        await ctx.send("Only the bot owner can use that command.")
        return

    if isinstance(error, commands.MissingRequiredArgument):
        await ctx.send("Missing arguments for that command.")
        return

    raise error


if not TOKEN:
    raise ValueError("DISCORD_TOKEN is missing from your environment variables.")

bot.run(TOKEN)
