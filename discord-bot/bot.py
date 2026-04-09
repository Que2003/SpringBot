import os
import re
import json
import time
import random
import asyncio
import signal
import shutil
import sys
from datetime import timedelta
from collections import Counter, defaultdict, deque

import discord
from discord.ext import commands
from discord import app_commands
import yt_dlp
import requests

if sys.version_info < (3, 14):
    raise RuntimeError("This legacy SpringBot file requires Python 3.14+. Use start_springbot.cmd or run_bot.ps1.")

# =========================
# CONFIG
# =========================
def _load_discord_token() -> str:
    token = os.getenv("DISCORD_TOKEN", "").replace("\ufeff", "").strip()
    if token:
        if token.lower().startswith("bot "):
            token = token[4:].strip()
        return token

    base_dir = os.path.dirname(__file__)
    fallback_paths = [
        os.path.join(base_dir, "discord_token.txt"),
        os.path.join(os.path.dirname(base_dir), "Spring Bot  Token.txt"),
    ]

    for path in fallback_paths:
        if os.path.exists(path):
            with open(path, "r", encoding="utf-8-sig") as handle:
                token = handle.read().replace("\ufeff", "").strip()
            if token.lower().startswith("bot "):
                token = token[4:].strip()
            if (token.startswith('"') and token.endswith('"')) or (token.startswith("'") and token.endswith("'")):
                token = token[1:-1].strip()
            if token:
                return token

    return ""


DISCORD_TOKEN = _load_discord_token()

_owner_id_env = os.getenv("DISCORD_OWNER_ID", "")
OWNER_IDS = {int(_owner_id_env)} if _owner_id_env.isdigit() else set()

ADMIN_ROLE_NAMES = {"Admin", "Moderator", "Owner"}

AUTO_ROLE_NAME = "Member"
WELCOME_CHANNEL_NAME = "welcome"
MOD_LOG_CHANNEL_NAME = "mod-logs"
TICKET_CATEGORY_NAME = "Tickets"

BOT_PREFIX = "!"
MAX_QUEUE_SIZE = 25
SPAM_WINDOW_SECONDS = 8
SPAM_MESSAGE_THRESHOLD = 6

DATA_DIR = os.path.join(os.path.dirname(__file__), "data")
os.makedirs(DATA_DIR, exist_ok=True)

WARNINGS_FILE       = os.path.join(DATA_DIR, "warnings.json")
SETTINGS_FILE       = os.path.join(DATA_DIR, "settings.json")
REACTION_ROLES_FILE = os.path.join(DATA_DIR, "reaction_roles.json")
ECONOMY_FILE        = os.path.join(DATA_DIR, "economy.json")
XP_FILE             = os.path.join(DATA_DIR, "xp.json")
CUSTOM_CMDS_FILE    = os.path.join(DATA_DIR, "custom_commands.json")
WORD_FILTER_FILE    = os.path.join(DATA_DIR, "word_filter.json")
AFK_FILE            = os.path.join(DATA_DIR, "afk.json")
GIVEAWAY_FILE       = os.path.join(DATA_DIR, "giveaways.json")
STARBOARD_FILE      = os.path.join(DATA_DIR, "starboard.json")
CHAT_MEMORY_FILE    = os.path.join(DATA_DIR, "chat_memory.json")
USER_PREFS_FILE     = os.path.join(DATA_DIR, "user_prefs.json")
SERVER_CONFIG_FILE  = os.path.join(DATA_DIR, "server_config.json")

STARBOARD_CHANNEL_NAME  = "starboard"
STARBOARD_THRESHOLD     = 3       # ⭐ reactions needed to pin
DAILY_AMOUNT            = 250     # coins per !daily
WORK_MIN, WORK_MAX      = 50, 200 # coins per !work
WORK_COOLDOWN           = 3600    # 1 hour
XP_PER_MSG_MIN          = 10
XP_PER_MSG_MAX          = 25
XP_COOLDOWN             = 60      # seconds between XP grants per user

TRIVIA_API  = "https://opentdb.com/api.php"
REDDIT_MEME = "https://www.reddit.com/r/ProgrammerHumor/random.json"

LINK_REGEX = re.compile(r"(https?://\S+|discord\.gg/\S+)", re.IGNORECASE)
WIKI_SEARCH_URL = "https://en.wikipedia.org/w/api.php"

# Replit blocks outbound UDP, which Discord voice requires for audio streaming.
# When running on Replit we skip voice entirely and always show the YouTube link.
IS_REPLIT = bool(os.getenv("REPL_ID") or os.getenv("REPLIT_CLUSTER") or os.getenv("REPL_OWNER"))

BROKEN_PROXY_ENV_NAMES = [
    "ALL_PROXY", "all_proxy",
    "HTTP_PROXY", "http_proxy",
    "HTTPS_PROXY", "https_proxy",
    "GIT_HTTP_PROXY", "git_http_proxy",
    "GIT_HTTPS_PROXY", "git_https_proxy",
]

def clear_broken_proxy_env() -> list[str]:
    removed = []
    for key in BROKEN_PROXY_ENV_NAMES:
        value = os.environ.get(key, "")
        lower = value.lower()
        if "127.0.0.1:9" in lower or "localhost:9" in lower:
            os.environ.pop(key, None)
            removed.append(key)
    return removed

CLEARED_PROXY_VARS = clear_broken_proxy_env()

# =========================
# FUNNY / PERSONALITY
# =========================
FUNNY_ACKS = [
    "Handled.",
    "Done. Efficiently too.",
    "Easy work.",
    "Finished. Server maintenance by greatness.",
    "Taken care of.",
    "Done. I continue to carry."
]

ROAST_LINES = [
    "That decision had the structural integrity of a paper firewall.",
    "I've seen better ideas from unplugged routers.",
    "That was bold. Not smart. Just bold.",
    "Respectfully, that move was malware-adjacent.",
    "I ran diagnostics on that thought. Results were unfortunate."
]

MENTION_REPLIES = [
    "You summoned greatness?",
    "I'm here. Make it worth my bandwidth.",
    "Yes? Try asking something intelligent.",
    "Present. Smart, funny, and underpaid."
]

WELCOME_MESSAGE = "Welcome to the server {mention}, glad to have you! 🎉"

# =========================
# KNOWLEDGE BASE
# =========================
TECH_KB = {
    "comptia a+": "CompTIA A+ covers hardware, operating systems, printers, mobile devices, basic networking, troubleshooting, and security fundamentals for entry-level IT support.",
    "a+": "CompTIA A+ is an entry-level IT certification focused on support, troubleshooting, hardware, software, networking basics, and security.",
    "network+": "CompTIA Network+ focuses on networking concepts like TCP/IP, DNS, DHCP, routing, switching, ports, wireless, troubleshooting, and network security.",
    "security+": "CompTIA Security+ covers threats, vulnerabilities, IAM, cryptography, incident response, risk management, and security architecture.",
    "tcp": "TCP is a connection-oriented protocol designed for reliable data delivery.",
    "udp": "UDP is a connectionless protocol that is faster but does not guarantee delivery.",
    "dns": "DNS translates domain names into IP addresses.",
    "dhcp": "DHCP automatically assigns IP addresses and network settings to devices.",
    "vpn": "A VPN creates an encrypted tunnel between your device and another network.",
    "firewall": "A firewall filters inbound and outbound traffic based on rules.",
    "cpu": "The CPU handles general processing and executes instructions.",
    "gpu": "The GPU handles graphics rendering and parallel workloads.",
    "ram": "RAM is temporary working memory used by active processes.",
    "ssd": "An SSD is fast solid-state storage with no moving parts.",
    "osi model": "The OSI model has 7 layers: Physical, Data Link, Network, Transport, Session, Presentation, Application.",
    "cia triad": "The CIA triad stands for Confidentiality, Integrity, and Availability.",
    "router": "A router connects different networks and forwards traffic between them.",
    "switch": "A switch connects devices inside the same local network using MAC addresses.",
    "sql": "SQL is a language used to query and manage relational databases.",
    "linux": "Linux is an open-source operating system used in servers, desktops, networking, and security labs.",
    "windows": "Windows is Microsoft's operating system family used widely on personal and business computers.",
    "firewall": "A firewall limits network traffic in or out of a system. It can be hardware-only, software-only, or included in routers and servers. Its role is to filter traffic based on defined rules.",
    "malware": "Malware is a broad term covering attacks on computer systems — including viruses, exploits, worms, ransomware, adware, keyloggers, and rootkits.",
    "ransomware": "Ransomware is malware that locks or encrypts your files and demands payment to restore access.",
    "adware": "Adware is malware that records your activities to target you with pop-up advertisements.",
    "keylogger": "A keylogger is malware that records all keystrokes and sends that data to an attacker.",
    "rootkit": "A rootkit is software that gains root-level (administrative) access and hides itself from the operating system.",
    "encryption": "Encryption scrambles file contents so they are unreadable without the correct key. AES (Advanced Encryption Standard) is currently the most secure standard available.",
    "bsod": "BSOD (Blue Screen of Death) is a fatal Windows error — a blue screen showing a STOP code that helps diagnose hardware or driver failures.",
    "blue screen of death": "The Blue Screen of Death (BSOD) is a fatal Windows error displayed as a blue screen with a STOP code to help troubleshoot the issue.",
}

GENERAL_KB = {
    "history": "History is the study of past events, people, and civilizations.",
    "biology": "Biology is the study of living organisms.",
    "chemistry": "Chemistry is the study of matter, substances, and how they change.",
    "physics": "Physics is the study of matter, energy, motion, and forces.",
    "math": "Mathematics is the study of numbers, patterns, structure, and quantity.",
    "geography": "Geography is the study of places, environments, and how humans interact with them.",
    "python": "Python is a high-level programming language known for readability and strong library support.",
    "discord": "Discord is a communication platform built around servers, text channels, voice channels, roles, and bots.",
    "database": "A database is an organized collection of data that can be stored, queried, and managed.",
    "cybersecurity": "Cybersecurity is the practice of protecting systems, networks, and data from attacks and unauthorized access.",
    "cloud computing": "Cloud computing is the delivery of services like storage, servers, and software over the internet."
}

COMMON_PORTS = {
    "ftp": "21",
    "ssh": "22",
    "telnet": "23",
    "smtp": "25",
    "dns": "53",
    "dhcp": "67/68",
    "tftp": "69",
    "http": "80",
    "pop3": "110",
    "imap": "143",
    "snmp": "161/162",
    "ldap": "389",
    "https": "443",
    "smb": "445",
    "rdp": "3389",
    "imaps": "993",
    "pop3s": "995",
}

CHAT_MEMORY_LIMIT = 10
SUPPORTED_MODES = {
    "jarvis": "Sharp, confident, helpful, and a little sarcastic.",
    "lore": "Mythic, dramatic, and story-rich.",
    "tech": "Precise, technical, and direct.",
    "study": "Structured, patient, and step-by-step.",
    "chat": "Relaxed, friendly, and conversational.",
    "brief": "Fast, compact, and minimal.",
}

SUPPORTED_LANGUAGES = {
    "english": "en",
    "spanish": "es",
    "french": "fr",
    "german": "de",
    "italian": "it",
    "portuguese": "pt",
    "russian": "ru",
    "ukrainian": "uk",
    "polish": "pl",
    "dutch": "nl",
    "swedish": "sv",
    "norwegian": "no",
    "danish": "da",
    "finnish": "fi",
    "czech": "cs",
    "romanian": "ro",
    "greek": "el",
    "turkish": "tr",
    "arabic": "ar",
    "hebrew": "he",
    "hindi": "hi",
    "bengali": "bn",
    "urdu": "ur",
    "tamil": "ta",
    "chinese": "zh-CN",
    "japanese": "ja",
    "korean": "ko",
    "thai": "th",
    "vietnamese": "vi",
    "indonesian": "id",
}

LANGUAGE_ALIASES = {
    "en": "english",
    "eng": "english",
    "es": "spanish",
    "spa": "spanish",
    "fr": "french",
    "de": "german",
    "it": "italian",
    "pt": "portuguese",
    "ru": "russian",
    "uk": "ukrainian",
    "pl": "polish",
    "nl": "dutch",
    "sv": "swedish",
    "no": "norwegian",
    "da": "danish",
    "fi": "finnish",
    "cs": "czech",
    "ro": "romanian",
    "el": "greek",
    "tr": "turkish",
    "ar": "arabic",
    "he": "hebrew",
    "hi": "hindi",
    "bn": "bengali",
    "ur": "urdu",
    "ta": "tamil",
    "zh": "chinese",
    "zh-cn": "chinese",
    "ja": "japanese",
    "ko": "korean",
    "th": "thai",
    "vi": "vietnamese",
    "id": "indonesian",
    "filipino": "english",
    "malay": "indonesian",
}

TRANSLATE_API_URL = "https://translate.googleapis.com/translate_a/single"
DICTIONARY_API_URL = "https://api.dictionaryapi.dev/api/v2/entries/en/"

FUN_FACTS = {
    "space": "A day on Venus is longer than a Venus year. It rotates so slowly that one full spin takes longer than one trip around the Sun.",
    "history": "Oxford University is older than the Aztec Empire.",
    "science": "Bananas are slightly radioactive because they contain potassium.",
    "math": "Zero was invented independently in multiple civilizations, but its formal use as a number transformed algebra and computing.",
    "python": "Python was named after Monty Python, not the snake.",
    "discord": "Discord started as a communication tool for gamers, then expanded into communities for study, work, and fandoms.",
    "cybersecurity": "The first computer worm to spread widely on the internet was the Morris Worm in 1988.",
}

STOPWORDS = {
    "a", "an", "and", "are", "as", "at", "be", "by", "for", "from", "how",
    "i", "in", "is", "it", "its", "of", "on", "or", "that", "the", "this",
    "to", "was", "what", "when", "where", "which", "who", "why", "with",
    "you", "your", "into", "than", "then", "they", "them", "their", "have",
    "has", "had", "will", "would", "should", "could", "can", "may", "might",
}

# =========================
# BOT SETUP
# =========================
intents = discord.Intents.default()
intents.guilds = True
intents.members = True
intents.voice_states = True
intents.message_content = True
intents.messages = True

bot = commands.Bot(command_prefix=BOT_PREFIX, intents=intents)

music_queues = defaultdict(lambda: deque(maxlen=MAX_QUEUE_SIZE))
music_now_playing: dict[int, dict] = {}
spam_tracker = defaultdict(list)
processed_message_ids = set()

# =========================
# FILE HELPERS
# =========================
def load_json_file(path, default):
    if not os.path.exists(path):
        return default
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return default

def save_json_file(path, data):
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=4)

warnings_data      = load_json_file(WARNINGS_FILE, {})
settings_data      = load_json_file(SETTINGS_FILE, {"anti_link": True, "anti_spam": True})
reaction_roles_data = load_json_file(REACTION_ROLES_FILE, {})
economy_data       = load_json_file(ECONOMY_FILE, {})
xp_data            = load_json_file(XP_FILE, {})
custom_cmds_data   = load_json_file(CUSTOM_CMDS_FILE, {})
word_filter_data   = load_json_file(WORD_FILTER_FILE, {})
afk_data           = load_json_file(AFK_FILE, {})
giveaway_data      = load_json_file(GIVEAWAY_FILE, {})
starboard_data     = load_json_file(STARBOARD_FILE, {})
chat_memory_data   = load_json_file(CHAT_MEMORY_FILE, {})
user_prefs_data    = load_json_file(USER_PREFS_FILE, {})
server_config_data = load_json_file(SERVER_CONFIG_FILE, {})

# Runtime cooldown trackers (not persisted)
xp_cooldowns: dict[tuple, float]       = {}
work_cooldowns: dict[str, float]       = {}
remind_cooldowns: dict[str, float]     = {}
trivia_sessions: dict[int, dict]       = {}   # channel_id -> question data

# =========================
# HELPERS
# =========================
def get_channel_by_name(guild: discord.Guild, name: str):
    return discord.utils.get(guild.text_channels, name=name)

def get_role_by_name(guild: discord.Guild, name: str):
    return discord.utils.get(guild.roles, name=name)

def save_server_config():
    save_json_file(SERVER_CONFIG_FILE, server_config_data)

def get_guild_config(guild_id: int) -> dict:
    gid = str(guild_id)
    config = server_config_data.get(gid)
    if not isinstance(config, dict):
        config = {}
    config.setdefault("welcome_channel_id", None)
    config.setdefault("mod_log_channel_id", None)
    config.setdefault("auto_role_id", None)
    config.setdefault("ticket_category_id", None)
    config.setdefault("lockdown_state", {})
    server_config_data[gid] = config
    return config

def get_configured_text_channel(guild: discord.Guild, key: str, fallback_name: str | None = None):
    config = get_guild_config(guild.id)
    channel_id = config.get(key)
    if channel_id:
        channel = guild.get_channel(channel_id)
        if isinstance(channel, discord.TextChannel):
            return channel
    if fallback_name:
        return get_channel_by_name(guild, fallback_name)
    return None

def get_configured_role(guild: discord.Guild, key: str, fallback_name: str | None = None):
    config = get_guild_config(guild.id)
    role_id = config.get(key)
    if role_id:
        role = guild.get_role(role_id)
        if isinstance(role, discord.Role):
            return role
    if fallback_name:
        return get_role_by_name(guild, fallback_name)
    return None

def get_ticket_category(guild: discord.Guild):
    config = get_guild_config(guild.id)
    category_id = config.get("ticket_category_id")
    if category_id:
        category = guild.get_channel(category_id)
        if isinstance(category, discord.CategoryChannel):
            return category
    return discord.utils.get(guild.categories, name=TICKET_CATEGORY_NAME)

def set_guild_config_value(guild_id: int, key: str, value):
    config = get_guild_config(guild_id)
    config[key] = value
    save_server_config()

def serialize_perm_value(value) -> str:
    if value is True:
        return "allow"
    if value is False:
        return "deny"
    return "inherit"

def deserialize_perm_value(value: str):
    if value == "allow":
        return True
    if value == "deny":
        return False
    return None

def get_bot_permission_snapshot(guild: discord.Guild) -> tuple[discord.Permissions, list[str]]:
    me = guild.me or guild.get_member(bot.user.id if bot.user else 0)
    perms = guild.me.guild_permissions if guild.me else discord.Permissions.none()
    needed = [
        "administrator",
        "manage_guild",
        "manage_roles",
        "manage_channels",
        "manage_messages",
        "kick_members",
        "ban_members",
        "moderate_members",
        "move_members",
        "connect",
        "speak",
    ]
    missing = [perm for perm in needed if not getattr(perms, perm, False)]
    return perms, missing

def get_or_create_guild_warning_store(guild_id: int):
    gid = str(guild_id)
    if gid not in warnings_data:
        warnings_data[gid] = {}
    return warnings_data[gid]

# ---- Economy helpers ----
def get_economy(user_id: int) -> dict:
    uid = str(user_id)
    if uid not in economy_data:
        economy_data[uid] = {"coins": 0, "daily_ts": 0, "work_ts": 0}
    return economy_data[uid]

def add_coins(user_id: int, amount: int) -> int:
    rec = get_economy(user_id)
    rec["coins"] = max(0, rec["coins"] + amount)
    save_json_file(ECONOMY_FILE, economy_data)
    return rec["coins"]

# ---- XP / Level helpers ----
def xp_for_level(level: int) -> int:
    return 100 * (level ** 2)

def get_xp_record(guild_id: int, user_id: int) -> dict:
    gid, uid = str(guild_id), str(user_id)
    if gid not in xp_data:
        xp_data[gid] = {}
    if uid not in xp_data[gid]:
        xp_data[gid][uid] = {"xp": 0, "level": 1}
    return xp_data[gid][uid]

async def grant_xp(message: discord.Message):
    key = (message.guild.id, message.author.id)
    now = time.time()
    if now - xp_cooldowns.get(key, 0) < XP_COOLDOWN:
        return None   # on cooldown

    xp_cooldowns[key] = now
    rec = get_xp_record(message.guild.id, message.author.id)
    earned = random.randint(XP_PER_MSG_MIN, XP_PER_MSG_MAX)
    rec["xp"] += earned

    leveled_up = False
    while rec["xp"] >= xp_for_level(rec["level"]):
        rec["xp"] -= xp_for_level(rec["level"])
        rec["level"] += 1
        leveled_up = True

    save_json_file(XP_FILE, xp_data)
    return rec["level"] if leveled_up else None

def make_xp_bar(xp: int, level: int, width: int = 12) -> str:
    needed = xp_for_level(level)
    filled = int((xp / needed) * width) if needed else 0
    return "█" * filled + "░" * (width - filled)

# ---- Word filter helpers ----
def get_word_filter(guild_id: int) -> list:
    return word_filter_data.get(str(guild_id), [])

def message_hits_filter(content: str, guild_id: int) -> str | None:
    words = get_word_filter(guild_id)
    low = content.lower()
    for w in words:
        if w.lower() in low:
            return w
    return None

# ---- AFK helpers ----
def get_afk_key(guild_id: int, user_id: int) -> str:
    return f"{guild_id}:{user_id}"

def set_afk(guild_id: int, user_id: int, reason: str):
    afk_data[get_afk_key(guild_id, user_id)] = {"reason": reason, "ts": time.time()}
    save_json_file(AFK_FILE, afk_data)

def clear_afk(guild_id: int, user_id: int):
    key = get_afk_key(guild_id, user_id)
    if key in afk_data:
        del afk_data[key]
        save_json_file(AFK_FILE, afk_data)

def get_afk(guild_id: int, user_id: int) -> dict | None:
    return afk_data.get(get_afk_key(guild_id, user_id))

# ---- External data fetchers ----
def fetch_trivia() -> dict | None:
    try:
        r = requests.get(TRIVIA_API, params={"amount": 1, "type": "multiple"}, timeout=6)
        r.raise_for_status()
        results = r.json().get("results", [])
        if not results:
            return None
        q = results[0]
        import html
        correct    = html.unescape(q["correct_answer"])
        incorrect  = [html.unescape(a) for a in q["incorrect_answers"]]
        options    = incorrect + [correct]
        random.shuffle(options)
        return {
            "question":  html.unescape(q["question"]),
            "options":   options,
            "answer":    correct,
            "category":  html.unescape(q.get("category", "")),
            "difficulty": q.get("difficulty", ""),
        }
    except Exception:
        return None

def fetch_meme() -> dict | None:
    try:
        headers = {"User-Agent": "SpringBot/1.0"}
        r = requests.get(REDDIT_MEME, headers=headers, timeout=6)
        r.raise_for_status()
        data = r.json()
        post = data[0]["data"]["children"][0]["data"]
        if post.get("over_18") or not post.get("url", "").endswith((".jpg", ".png", ".gif")):
            return None
        return {
            "title":  post.get("title", ""),
            "url":    post.get("url", ""),
            "ups":    post.get("ups", 0),
            "link":   f"https://reddit.com{post.get('permalink', '')}",
        }
    except Exception:
        return None

def safe_eval(expr: str) -> str:
    """Evaluate a math expression safely."""
    import ast, operator
    allowed_ops = {
        ast.Add: operator.add, ast.Sub: operator.sub,
        ast.Mult: operator.mul, ast.Div: operator.truediv,
        ast.Pow: operator.pow, ast.Mod: operator.mod,
        ast.FloorDiv: operator.floordiv, ast.USub: operator.neg,
    }
    def _eval(node):
        if isinstance(node, ast.Constant) and isinstance(node.value, (int, float)):
            return node.value
        elif isinstance(node, ast.BinOp):
            op = allowed_ops.get(type(node.op))
            if op is None:
                raise ValueError("Unsupported operation")
            return op(_eval(node.left), _eval(node.right))
        elif isinstance(node, ast.UnaryOp) and isinstance(node.op, ast.USub):
            return -_eval(node.operand)
        else:
            raise ValueError("Unsupported expression")
    try:
        tree = ast.parse(expr.strip(), mode="eval")
        result = _eval(tree.body)
        if isinstance(result, float):
            return f"{result:.6g}"
        return str(result)
    except ZeroDivisionError:
        return "Error: division by zero"
    except Exception:
        return "Invalid expression"

def ack_line():
    return random.choice(FUNNY_ACKS)

def roast_line():
    return random.choice(ROAST_LINES)

async def log_mod_action(guild: discord.Guild, message: str):
    channel = get_configured_text_channel(guild, "mod_log_channel_id", MOD_LOG_CHANNEL_NAME)
    if channel:
        try:
            await channel.send(message)
        except Exception:
            pass

def user_is_admin(member: discord.Member) -> bool:
    if member.id in OWNER_IDS:
        return True
    if member.guild_permissions.administrator:
        return True
    user_role_names = {role.name for role in member.roles}
    return bool(user_role_names & ADMIN_ROLE_NAMES)

def clean_summary(text: str, max_len: int = 900) -> str:
    text = re.sub(r"\s+", " ", text).strip()
    if len(text) > max_len:
        return text[:max_len - 3] + "..."
    return text

DDG_API_URL = "https://api.duckduckgo.com/"

def get_ddg_answer(query: str) -> dict | None:
    """
    Query the DuckDuckGo Instant Answer API (no key required).
    Returns a dict with keys: answer, abstract, url, source, image, related
    or None if nothing useful was found.
    """
    try:
        params = {
            "q": query,
            "format": "json",
            "no_html": "1",
            "skip_disambig": "1",
            "t": "SpringBot",
        }
        r = requests.get(DDG_API_URL, params=params, timeout=8)
        r.raise_for_status()
        data = r.json()

        answer   = data.get("Answer", "").strip()
        abstract = data.get("AbstractText", "").strip()
        url      = data.get("AbstractURL", "").strip()
        source   = data.get("AbstractSource", "").strip()
        image    = data.get("Image", "").strip()
        defn     = data.get("Definition", "").strip()
        defn_url = data.get("DefinitionURL", "").strip()

        related = []
        for t in data.get("RelatedTopics", [])[:4]:
            text = t.get("Text", "").strip()
            link = t.get("FirstURL", "").strip()
            if text and link:
                # Truncate long related topic text
                short = text if len(text) <= 120 else text[:117] + "..."
                related.append({"text": short, "url": link})

        # Prefer direct answer > abstract > definition
        if not answer and not abstract and not defn:
            return None

        return {
            "answer":   answer,
            "abstract": abstract or defn,
            "url":      url or defn_url,
            "source":   source or ("Dictionary" if defn else ""),
            "image":    image if image.startswith("http") else "",
            "related":  related,
        }
    except Exception:
        return None

def get_wikipedia_summary(query: str):
    try:
        search_params = {
            "action": "opensearch",
            "search": query,
            "limit": 1,
            "namespace": 0,
            "format": "json"
        }
        search_res = requests.get(WIKI_SEARCH_URL, params=search_params, timeout=10)
        search_res.raise_for_status()
        search_data = search_res.json()

        if not search_data or len(search_data) < 2 or not search_data[1]:
            return None

        title = search_data[1][0]

        extract_params = {
            "action": "query",
            "prop": "extracts",
            "exintro": True,
            "explaintext": True,
            "titles": title,
            "format": "json"
        }
        extract_res = requests.get(WIKI_SEARCH_URL, params=extract_params, timeout=10)
        extract_res.raise_for_status()
        extract_data = extract_res.json()

        pages = extract_data.get("query", {}).get("pages", {})
        if not pages:
            return None

        page = next(iter(pages.values()))
        extract = page.get("extract", "").strip()
        if not extract:
            return f"I found **{title}**, but there wasn't a clean summary available."

        return f"**{title}** — {clean_summary(extract)}"
    except Exception:
        return None

GLOSSARY_FLAT_FILE = os.path.join(DATA_DIR, "glossary_flat.txt")
_glossary_text: str = ""

def _load_glossary() -> str:
    global _glossary_text
    if not _glossary_text and os.path.isfile(GLOSSARY_FLAT_FILE):
        with open(GLOSSARY_FLAT_FILE, encoding="utf-8", errors="replace") as f:
            _glossary_text = f.read()
    return _glossary_text

def search_glossary(query: str) -> str | None:
    """Search the IT glossary flat text for a term. Returns a clean snippet or None."""
    text = _load_glossary()
    if not text:
        return None

    q = query.strip()
    words = q.split()
    candidates = []
    for n in range(min(6, len(words)), 0, -1):
        candidates.append(" ".join(words[:n]))

    text_lower = text.lower()

    def _extract(start: int) -> str:
        snippet = text[start : start + 550].strip()
        sentences = re.split(r'(?<=[.!?])\s+', snippet)
        result = ""
        for sent in sentences:
            if len(result) + len(sent) > 380:
                break
            result += sent + " "
        result = result.strip()
        return result if len(result) >= 20 else snippet[:380].strip()

    for phrase in candidates:
        ph = phrase.lower()
        # Priority 1: phrase appears right after a sentence boundary (start of an entry)
        # Pattern: ". phrase <optional (ABBREV)> UppercaseLetter"
        entry_re = r'(?:\.\s+)' + re.escape(ph) + r'(?:\s+\([^)]+\))?\s+[A-Z]'
        m = re.search(entry_re, text_lower)
        if m:
            # Start from just after the ". "
            start = m.start() + 2
            return _extract(start)

        # Priority 2: phrase at very start of the flat text
        if text_lower.startswith(ph):
            return _extract(0)

        # Priority 3: any word-boundary match — still useful
        any_re = r'(?<![A-Za-z0-9])' + re.escape(ph) + r'(?![A-Za-z0-9])'
        m = re.search(any_re, text_lower)
        if not m:
            continue
        idx = m.start()
        look_back = text_lower.rfind(". ", max(0, idx - 600), idx)
        start = (look_back + 2) if look_back != -1 else max(0, idx - 30)
        return _extract(start)

    return None

def broad_knowledge_answer(question: str) -> str:
    q = question.lower().strip()

    for service, port in COMMON_PORTS.items():
        if service in q and ("port" in q or "ports" in q):
            return f"{service.upper()} uses port {port}."

    for key, value in TECH_KB.items():
        if key in q:
            return value

    for key, value in GENERAL_KB.items():
        if key in q:
            return value

    if "difference between tcp and udp" in q:
        return "TCP is reliable and connection-oriented. UDP is faster and connectionless."

    if "difference between router and switch" in q:
        return "A router connects different networks. A switch connects devices inside the same local network."

    if "what is comptia" in q:
        return "CompTIA is a vendor-neutral certification organization known for A+, Network+, and Security+."

    if "best cert" in q or "which certification" in q:
        return "For entry-level IT, A+ is usually the safest start. For networking, Network+. For security foundations, Security+."

    # Search the IT glossary
    glossary_hit = search_glossary(q)
    if glossary_hit:
        return f"📖 **From the IT glossary:**\n{glossary_hit}"

    # DuckDuckGo Instant Answer
    ddg = get_ddg_answer(question)
    if ddg:
        if ddg["answer"]:
            return f"🔍 {ddg['answer']}"
        if ddg["abstract"]:
            text = clean_summary(ddg["abstract"], 400)
            src  = f" ([{ddg['source']}]({ddg['url']}))" if ddg["url"] else ""
            return f"🔍 {text}{src}"

    wiki = get_wikipedia_summary(question)
    if wiki:
        return wiki

    return "I don't have a solid answer for that yet. Try `!search <topic>` for a full web search."

def normalize_text(text: str) -> str:
    return re.sub(r"\s+", " ", text).strip()

def split_sentences(text: str) -> list[str]:
    return [s.strip() for s in re.split(r"(?<=[.!?])\s+", normalize_text(text)) if s.strip()]

def shorten(text: str, limit: int = 1800) -> str:
    text = normalize_text(text)
    if len(text) <= limit:
        return text
    return text[: limit - 3].rstrip() + "..."

def strip_formatting(text: str) -> str:
    return normalize_text(re.sub(r"[*_`>#-]", " ", text))

def get_user_prefs(user_id: int) -> dict:
    uid = str(user_id)
    prefs = user_prefs_data.get(uid)
    if not isinstance(prefs, dict):
        prefs = {}
    prefs.setdefault("mode", "jarvis")
    prefs.setdefault("language", "english")
    user_prefs_data[uid] = prefs
    return prefs

def save_user_prefs():
    save_json_file(USER_PREFS_FILE, user_prefs_data)

def get_user_mode(user_id: int) -> str:
    return get_user_prefs(user_id)["mode"]

def set_user_mode(user_id: int, mode: str):
    get_user_prefs(user_id)["mode"] = mode
    save_user_prefs()

def get_user_language(user_id: int) -> str:
    return get_user_prefs(user_id)["language"]

def set_user_language(user_id: int, language: str):
    get_user_prefs(user_id)["language"] = language
    save_user_prefs()

def get_chat_history(user_id: int) -> list[dict]:
    uid = str(user_id)
    history = chat_memory_data.get(uid, [])
    if not isinstance(history, list):
        history = []
    chat_memory_data[uid] = history
    return history

def save_chat_memory():
    save_json_file(CHAT_MEMORY_FILE, chat_memory_data)

def remember_chat_turn(user_id: int, role: str, text: str):
    history = get_chat_history(user_id)
    history.append({"role": role, "text": shorten(text, 350)})
    chat_memory_data[str(user_id)] = history[-CHAT_MEMORY_LIMIT:]
    save_chat_memory()

def clear_chat_history(user_id: int):
    chat_memory_data[str(user_id)] = []
    save_chat_memory()

def resolve_language_name(language: str) -> str | None:
    key = normalize_text(language).lower()
    if not key:
        return None
    if key in SUPPORTED_LANGUAGES:
        return key
    return LANGUAGE_ALIASES.get(key)

def translate_text(text: str, target_language: str, source_language: str = "auto") -> str | None:
    language_code = SUPPORTED_LANGUAGES.get(target_language)
    if not language_code:
        return None
    try:
        params = {
            "client": "gtx",
            "sl": source_language,
            "tl": language_code,
            "dt": "t",
            "q": text,
        }
        response = requests.get(TRANSLATE_API_URL, params=params, timeout=10)
        response.raise_for_status()
        payload = response.json()
        pieces = payload[0] if payload else []
        translated = "".join(part[0] for part in pieces if part and part[0])
        return normalize_text(translated) if translated else None
    except Exception:
        return None

def maybe_translate_for_user(user_id: int, text: str) -> str:
    language = get_user_language(user_id)
    if language == "english":
        return text
    translated = translate_text(text, language)
    if translated:
        return translated
    return text + f"\n\nTranslation note: I could not translate that to {language.title()} right now."

def extract_keywords(text: str, limit: int = 5) -> list[str]:
    words = re.findall(r"[A-Za-z][A-Za-z0-9+/#.-]{2,}", text.lower())
    counts = Counter(word for word in words if word not in STOPWORDS)
    return [word for word, _ in counts.most_common(limit)]

def summarize_text_block(text: str, max_sentences: int = 3) -> str:
    sentences = split_sentences(text)
    if not sentences:
        return "I need more text before I can summarize it."
    if len(sentences) <= max_sentences:
        return " ".join(sentences)

    freq = Counter(
        word for word in re.findall(r"[A-Za-z][A-Za-z0-9'-]{2,}", text.lower())
        if word not in STOPWORDS
    )
    if not freq:
        return " ".join(sentences[:max_sentences])

    scored = []
    for idx, sentence in enumerate(sentences):
        words = re.findall(r"[A-Za-z][A-Za-z0-9'-]{2,}", sentence.lower())
        score = sum(freq[word] for word in words if word in freq)
        scored.append((score, idx, sentence))

    best = sorted(scored, key=lambda item: item[0], reverse=True)[:max_sentences]
    ordered = [sentence for _, _, sentence in sorted(best, key=lambda item: item[1])]
    return " ".join(ordered)

def knowledge_snapshot(topic: str, limit: int = 420) -> str:
    answer = broad_knowledge_answer(topic)
    answer = strip_formatting(answer)
    return shorten(answer, limit)

def fetch_dictionary_entry(word: str) -> dict | None:
    token = normalize_text(word).split()[0].lower()
    if not token:
        return None
    try:
        response = requests.get(DICTIONARY_API_URL + token, timeout=10)
        response.raise_for_status()
        payload = response.json()
        if not isinstance(payload, list) or not payload:
            return None
        entry = payload[0]
        meaning = ""
        example = ""
        part_of_speech = ""
        for meaning_block in entry.get("meanings", []):
            part_of_speech = meaning_block.get("partOfSpeech", "") or part_of_speech
            definitions = meaning_block.get("definitions", [])
            if definitions:
                meaning = definitions[0].get("definition", "")
                example = definitions[0].get("example", "")
                break
        phonetic = entry.get("phonetic", "")
        origin = entry.get("origin", "")
        if not meaning:
            return None
        return {
            "word": entry.get("word", token),
            "phonetic": phonetic,
            "part_of_speech": part_of_speech,
            "meaning": meaning,
            "example": example,
            "origin": origin,
        }
    except Exception:
        return None

def apply_mode_style(text: str, mode: str, prompt: str = "") -> str:
    clean = shorten(text, 1700)
    if mode == "brief":
        sentences = split_sentences(clean)
        return shorten(" ".join(sentences[:1]) or clean, 500)
    if mode == "tech":
        return f"Technical readout:\n{clean}"
    if mode == "study":
        sentences = split_sentences(clean)
        concept = sentences[0] if sentences else clean
        support = " ".join(sentences[1:3]) if len(sentences) > 1 else "Focus on the core idea, the reason it matters, and one example."
        return f"Study mode:\nCore idea: {concept}\nWhy it matters: {support}"
    if mode == "chat":
        return f"Short version: {clean}"
    if mode == "lore":
        return f"Archive entry:\n{clean}"
    return clean

def build_fallback_chat_response(prompt: str) -> str:
    short = shorten(prompt, 140)
    return (
        f"My take: {short}. Break it into the goal, the risk, and the next move. "
        "If you want something more structured, try `!explain`, `!compare`, or `!studyguide`."
    )

def build_smart_reply(user_id: int, prompt: str, use_memory: bool = True, forced_mode: str | None = None) -> str:
    prompt = normalize_text(prompt)
    if not prompt:
        return "Say the word. I am listening."

    mode = forced_mode or get_user_mode(user_id)
    history = get_chat_history(user_id) if use_memory else []
    lowered = prompt.lower()

    if re.fullmatch(r"[0-9\s+\-*/().%]+", prompt):
        result = safe_eval(prompt)
        if result != "Invalid expression":
            base = (
                f"Step 1: Read the expression `{prompt}`.\n"
                f"Step 2: Apply order of operations carefully.\n"
                f"Answer: {result}"
            )
        else:
            base = build_fallback_chat_response(prompt)
    elif lowered.startswith(("hi", "hello", "hey")) and len(prompt.split()) <= 5:
        base = "Ready when you are. Ask for moderation help, study help, tech help, or general conversation."
    else:
        base = broad_knowledge_answer(prompt)
        if "I don't have a solid answer for that yet" in base:
            base = build_fallback_chat_response(prompt)

    if use_memory and history and any(word in lowered for word in {"it", "that", "same", "again", "continue"}):
        recent_user_turns = [entry["text"] for entry in history if entry.get("role") == "user"]
        if recent_user_turns:
            base = f"Picking up from your earlier topic, `{shorten(recent_user_turns[-1], 80)}`.\n{base}"

    styled = apply_mode_style(base, mode, prompt)

    if use_memory:
        remember_chat_turn(user_id, "user", prompt)
        remember_chat_turn(user_id, "assistant", styled)

    return maybe_translate_for_user(user_id, styled)

def build_explanation(topic: str, user_id: int) -> str:
    answer = knowledge_snapshot(topic, 700)
    keywords = extract_keywords(answer, 4)
    lines = [
        f"Topic: {normalize_text(topic)}",
        f"Simple explanation: {answer}",
    ]
    if keywords:
        lines.append("Key ideas: " + ", ".join(keywords))
    return maybe_translate_for_user(user_id, "\n".join(lines))

def build_definition(word: str, user_id: int) -> str:
    entry = fetch_dictionary_entry(word)
    if entry:
        lines = [f"{entry['word'].title()}"]
        if entry["phonetic"]:
            lines.append(f"Pronunciation: {entry['phonetic']}")
        if entry["part_of_speech"]:
            lines.append(f"Part of speech: {entry['part_of_speech']}")
        lines.append(f"Meaning: {entry['meaning']}")
        if entry["origin"]:
            lines.append(f"Etymology: {entry['origin']}")
        if entry["example"]:
            lines.append(f"Example: {entry['example']}")
        return maybe_translate_for_user(user_id, "\n".join(lines))

    answer = knowledge_snapshot(word, 500)
    example = f"Example: `{word}` matters when the conversation is about {extract_keywords(answer, 1)[0] if extract_keywords(answer, 1) else 'the topic at hand'}."
    return maybe_translate_for_user(user_id, f"Definition: {answer}\n{example}")

def build_comparison(topic_a: str, topic_b: str, user_id: int) -> str:
    left = knowledge_snapshot(topic_a, 280)
    right = knowledge_snapshot(topic_b, 280)
    lines = [
        f"{topic_a.strip()} vs {topic_b.strip()}",
        f"{topic_a.strip()}: {left}",
        f"{topic_b.strip()}: {right}",
        "Quick take: choose based on the job, the tradeoffs, and the level of control you need.",
    ]
    return maybe_translate_for_user(user_id, "\n".join(lines))

def build_rewrite(style: str, text: str) -> str:
    style_key = style.lower().strip()
    base = normalize_text(text)
    if style_key == "professional":
        return f"Professional rewrite: {base[0:1].upper() + base[1:]}"
    if style_key == "casual":
        return f"Casual rewrite: {base} Keep it clear and relaxed."
    if style_key == "persuasive":
        return f"Persuasive rewrite: {base} This matters because it creates a stronger result with less confusion."
    if style_key == "formal":
        return f"Formal rewrite: It is important to note that {base[0:1].lower() + base[1:]}"
    if style_key == "simple":
        summary = summarize_text_block(base, 2)
        return f"Simple rewrite: {summary}"
    return "Use one of these styles: professional, casual, persuasive, formal, simple."

def build_flashcards(topic: str, user_id: int) -> str:
    source = knowledge_snapshot(topic, 700)
    keywords = extract_keywords(source, 5)
    answers = split_sentences(source)
    cards = [
        (f"What is {topic}?", answers[0] if answers else source),
        (f"Why does {topic} matter?", answers[1] if len(answers) > 1 else "It matters because it affects how the topic works in practice."),
        ("Name one key term connected to it.", keywords[0] if keywords else "Start with the main concept."),
        ("What is a simple way to remember it?", f"Link {topic} to `{keywords[1]}`." if len(keywords) > 1 else f"Tie {topic} to its main purpose."),
        ("What should you study next?", f"Review: {', '.join(keywords[1:4])}" if len(keywords) > 2 else "Review examples, use cases, and common mistakes."),
    ]
    lines = [f"Flashcards for {topic}"]
    for idx, (question, answer) in enumerate(cards, 1):
        lines.append(f"{idx}. Q: {question}")
        lines.append(f"   A: {answer}")
    return maybe_translate_for_user(user_id, "\n".join(lines))

def build_studyguide(topic: str, user_id: int) -> str:
    source = knowledge_snapshot(topic, 900)
    summary = summarize_text_block(source, 3)
    keywords = extract_keywords(source, 6)
    lines = [
        f"Study Guide: {topic}",
        f"Overview: {summary}",
        "Core points:",
    ]
    for idx, keyword in enumerate(keywords[:4], 1):
        lines.append(f"{idx}. Understand how `{keyword}` connects to {topic}.")
    lines.append("Quick review question: What problem does this topic solve, and what tradeoff comes with it?")
    return maybe_translate_for_user(user_id, "\n".join(lines))

def build_fun_fact(topic: str, user_id: int) -> str:
    normalized_topic = normalize_text(topic).lower() if topic else ""
    if normalized_topic in FUN_FACTS:
        fact = FUN_FACTS[normalized_topic]
    elif not normalized_topic:
        fact = random.choice(list(FUN_FACTS.values()))
    else:
        fact = knowledge_snapshot(topic, 350)
    return maybe_translate_for_user(user_id, f"Fun fact: {fact}")

def build_solver(problem: str, user_id: int) -> str:
    cleaned = normalize_text(problem)
    if re.fullmatch(r"[0-9\s+\-*/().%]+", cleaned):
        result = safe_eval(cleaned)
        if result != "Invalid expression":
            return maybe_translate_for_user(
                user_id,
                f"Problem: {cleaned}\n1. Read the expression.\n2. Apply order of operations.\n3. Compute the result.\nAnswer: {result}"
            )
    explanation = knowledge_snapshot(problem, 650)
    return maybe_translate_for_user(
        user_id,
        f"Problem: {cleaned}\n1. Identify the concept or formula involved.\n2. Break the problem into smaller parts.\n3. Check units, assumptions, or definitions.\nWorking answer: {explanation}"
    )

def build_language_list() -> str:
    names = sorted(name.title() for name in SUPPORTED_LANGUAGES)
    return ", ".join(names)

def strip_bot_mention(content: str) -> str:
    if not bot.user:
        return normalize_text(content)
    cleaned = re.sub(rf"<@!?{bot.user.id}>", " ", content)
    return normalize_text(cleaned)

# =========================
# MUSIC HELPERS
# =========================
COOKIES_FILE = os.path.join(DATA_DIR, "cookies.txt")
LOCAL_FFMPEG_CANDIDATES = [
    os.path.join(os.path.dirname(__file__), "ffmpeg", "bin", "ffmpeg.exe"),
    os.path.join(os.path.dirname(__file__), "..", "ffmpeg", "bin", "ffmpeg.exe"),
    os.path.join(os.path.dirname(__file__), "ffmpeg.exe"),
    os.path.join(os.path.dirname(__file__), "..", "ffmpeg.exe"),
]

def resolve_ffmpeg_executable() -> str:
    env_path = os.getenv("FFMPEG_PATH", "").strip()
    candidates = [env_path] + LOCAL_FFMPEG_CANDIDATES

    for candidate in candidates:
        if candidate and os.path.isfile(candidate):
            return os.path.abspath(candidate)

    found = shutil.which("ffmpeg")
    return found or ""

def ffmpeg_install_hint() -> str:
    return (
        "FFmpeg is required for voice playback. Put `ffmpeg.exe` in "
        "`SpringBot\\ffmpeg\\bin\\ffmpeg.exe` or set the `FFMPEG_PATH` environment variable."
    )

def build_ydl_options() -> dict:
    opts = {
        # Use the Android client — no JS runtime or signature solving needed
        "format": "bestaudio[ext=webm]/bestaudio[ext=m4a]/bestaudio/best",
        "noplaylist": True,
        "quiet": True,
        "no_warnings": True,
        "proxy": "",
        "default_search": "ytsearch",
        "extract_flat": False,
        "extractor_args": {
            "youtube": {
                "player_client": ["android", "web"],
                "player_skip": ["webpage"],
            }
        },
        # Suppress yt-dlp's own post-processors that may fail
        "postprocessors": [],
    }
    if os.path.isfile(COOKIES_FILE):
        opts["cookiefile"] = COOKIES_FILE
    return opts

FFMPEG_OPTIONS = {
    "before_options": "-reconnect 1 -reconnect_streamed 1 -reconnect_delay_max 5",
    "options": "-vn",
}

def build_ffmpeg_before_options(track: dict | None = None) -> str:
    parts = []
    base = FFMPEG_OPTIONS.get("before_options", "").strip()
    if base:
        parts.append(base)

    headers = (track or {}).get("http_headers", {})
    header_lines = []
    for key, value in headers.items():
        clean_key = str(key).replace("\r", "").replace("\n", "").strip()
        clean_value = str(value).replace("\r", "").replace("\n", "").strip()
        if clean_key and clean_value:
            header_lines.append(f"{clean_key}: {clean_value}")

    if header_lines:
        escaped = "\\r\\n".join(header_lines) + "\\r\\n"
        parts.append(f'-headers "{escaped}"')

    return " ".join(parts).strip()

def create_ffmpeg_source(track: dict | str):
    ffmpeg_executable = resolve_ffmpeg_executable()
    if not ffmpeg_executable:
        raise RuntimeError(ffmpeg_install_hint())
    track_url = track["url"] if isinstance(track, dict) else track
    return discord.FFmpegOpusAudio(
        track_url,
        executable=ffmpeg_executable,
        codec="libopus",
        bitrate=128,
        before_options=build_ffmpeg_before_options(track if isinstance(track, dict) else None),
        options=FFMPEG_OPTIONS.get("options"),
    )

async def get_audio_source(query: str):
    loop = asyncio.get_event_loop()

    def extract():
        with yt_dlp.YoutubeDL(build_ydl_options()) as ydl:
            info = ydl.extract_info(query, download=False)
            if not info:
                raise ValueError("No results found.")
            if "entries" in info:
                entry = info["entries"][0] if info["entries"] else None
                if not entry:
                    raise ValueError("No results found.")
                info = entry

            # Find the best audio URL from formats if top-level URL is missing
            audio_url = info.get("url")
            if not audio_url and info.get("formats"):
                for fmt in reversed(info["formats"]):
                    if fmt.get("acodec") != "none" and fmt.get("url"):
                        audio_url = fmt["url"]
                        break

            if not audio_url:
                raise ValueError("Could not extract a playable audio stream for this track.")

            return {
                "title":       info.get("title", "Unknown title"),
                "url":         audio_url,
                "webpage_url": info.get("webpage_url", query),
                "thumbnail":   info.get("thumbnail"),
                "duration":    info.get("duration", 0),
                "uploader":    info.get("uploader", "Unknown"),
                "http_headers": info.get("http_headers", {}),
            }

    return await loop.run_in_executor(None, extract)

def format_duration(seconds: int) -> str:
    if not seconds:
        return "Unknown"
    m, s = divmod(int(seconds), 60)
    h, m = divmod(m, 60)
    return f"{h}:{m:02d}:{s:02d}" if h else f"{m}:{s:02d}"

def build_track_embed(track: dict, status: str = "Now playing") -> discord.Embed:
    embed = discord.Embed(
        title=f"🎵 {status}",
        description=f"**[{track['title']}]({track['webpage_url']})**",
        color=discord.Color.blurple()
    )
    embed.add_field(name="Channel", value=track.get("uploader", "Unknown"), inline=True)
    embed.add_field(name="Duration", value=format_duration(track.get("duration", 0)), inline=True)
    if track.get("thumbnail"):
        embed.set_thumbnail(url=track["thumbnail"])
    return embed

async def ensure_voice_ctx(ctx: commands.Context, timeout: float = 10.0):
    if not ctx.author.voice or not ctx.author.voice.channel:
        await ctx.send("You need to be in a voice channel first.")
        return None

    channel = ctx.author.voice.channel
    vc = ctx.guild.voice_client

    # Already connected and healthy — move if in wrong channel
    if vc and vc.is_connected():
        if vc.channel != channel:
            await vc.move_to(channel)
        return vc

    # Stale voice client exists but is not connected — disconnect it cleanly first
    if vc:
        try:
            await vc.disconnect(force=True)
        except Exception:
            pass

    try:
        return await asyncio.wait_for(channel.connect(), timeout=timeout)
    except discord.ClientException:
        # Discord still thinks we're connected (stale gateway state after restart).
        # Force-cleanup via the guild's voice client list and retry once.
        try:
            existing = ctx.guild.voice_client
            if existing:
                await existing.disconnect(force=True)
            await asyncio.sleep(0.5)
            return await asyncio.wait_for(channel.connect(), timeout=timeout)
        except Exception:
            return None
    except asyncio.TimeoutError:
        return None
    except Exception:
        return None

async def play_next(guild: discord.Guild):
    vc = guild.voice_client
    if not vc:
        return

    if not music_queues[guild.id]:
        music_now_playing.pop(guild.id, None)
        return  # Stay in channel — wait for more songs or explicit !leave

    next_track = music_queues[guild.id].popleft()
    music_now_playing[guild.id] = next_track

    def after_playing(error):
        if error:
            print(f"Playback error: {error}")
        future = asyncio.run_coroutine_threadsafe(play_next(guild), bot.loop)
        try:
            future.result()
        except Exception as e:
            print(f"Queue continuation error: {e}")

    try:
        source = create_ffmpeg_source(next_track)
        vc.play(source, after=after_playing)
    except Exception as e:
        music_now_playing.pop(guild.id, None)
        print(f"Queue playback error: {e}")

# =========================
# PERMISSION CHECK
# =========================
def admin_only():
    async def predicate(ctx: commands.Context):
        if not isinstance(ctx.author, discord.Member):
            return False
        return user_is_admin(ctx.author)
    return commands.check(predicate)

# =========================
# TICKET VIEW
# =========================
class TicketView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(label="Create Ticket", style=discord.ButtonStyle.green, custom_id="create_ticket_button")
    async def create_ticket(self, interaction: discord.Interaction, button: discord.ui.Button):
        guild = interaction.guild
        member = interaction.user

        existing = discord.utils.get(guild.text_channels, name=f"ticket-{member.name.lower()}".replace(" ", "-"))
        if existing:
            await interaction.response.send_message(f"You already have a ticket: {existing.mention}", ephemeral=True)
            return

        category = get_ticket_category(guild)
        if category is None:
            category = await guild.create_category(TICKET_CATEGORY_NAME)
            set_guild_config_value(guild.id, "ticket_category_id", category.id)

        overwrites = {
            guild.default_role: discord.PermissionOverwrite(read_messages=False),
            member: discord.PermissionOverwrite(read_messages=True, send_messages=True),
            guild.me: discord.PermissionOverwrite(read_messages=True, send_messages=True, manage_channels=True)
        }

        for role_name in ADMIN_ROLE_NAMES:
            role = get_role_by_name(guild, role_name)
            if role:
                overwrites[role] = discord.PermissionOverwrite(read_messages=True, send_messages=True)

        channel_name = f"ticket-{member.name.lower()}".replace(" ", "-")
        channel = await guild.create_text_channel(channel_name, category=category, overwrites=overwrites)

        embed = discord.Embed(
            title="Support Ticket",
            description=f"{member.mention}, staff will be with you shortly.\nUse `!closeticket` when finished.",
            color=discord.Color.blurple()
        )
        await channel.send(embed=embed)
        await interaction.response.send_message(f"Ticket created: {channel.mention}", ephemeral=True)

# =========================
# EVENTS
# =========================
@bot.event
async def on_ready():
    # Clear all slash commands from Discord so old ones don't conflict
    bot.tree.clear_commands(guild=None)
    await bot.tree.sync()
    print(f"Logged in as {bot.user} | Prefix: {BOT_PREFIX} | Slash commands cleared.")
    if CLEARED_PROXY_VARS:
        print(f"[Startup] Cleared broken proxy variables: {', '.join(CLEARED_PROXY_VARS)}")

    bot.add_view(TicketView())
    await bot.change_presence(
        activity=discord.Activity(
            type=discord.ActivityType.watching,
            name="the server like unpaid management"
        )
    )

@bot.event
async def on_member_join(member: discord.Member):
    guild = member.guild

    # Auto-assign Member role
    role = get_configured_role(guild, "auto_role_id", AUTO_ROLE_NAME)
    if role:
        try:
            await member.add_roles(role, reason="Auto role on join")
        except Exception as e:
            print(f"Could not assign role to {member}: {e}")

    # Find welcome channel — fall back to system channel, then first writable text channel
    channel = (
        get_configured_text_channel(guild, "welcome_channel_id", WELCOME_CHANNEL_NAME)
        or guild.system_channel
        or next(
            (c for c in guild.text_channels if c.permissions_for(guild.me).send_messages),
            None
        )
    )

    if channel:
        msg = WELCOME_MESSAGE.format(mention=member.mention, guild=guild.name)
        embed = discord.Embed(
            description=msg,
            color=discord.Color.green()
        )
        embed.set_thumbnail(url=member.display_avatar.url)
        embed.set_footer(text=f"{guild.name} • Member #{guild.member_count}")
        await channel.send(embed=embed)

    await log_mod_action(guild, f"📥 {member} joined the server.")

@bot.event
async def on_raw_reaction_add(payload: discord.RawReactionActionEvent):
    if payload.guild_id is None or payload.user_id == bot.user.id:
        return

    guild = bot.get_guild(payload.guild_id)
    if guild is None:
        return

    # ── Reaction roles ──
    rr_data = reaction_roles_data.get(str(payload.message_id))
    if rr_data:
        emoji_str = str(payload.emoji)
        role_id = rr_data.get(emoji_str)
        if role_id:
            member = guild.get_member(payload.user_id)
            role = guild.get_role(role_id)
            if member and role:
                try:
                    await member.add_roles(role, reason="Reaction role added")
                except Exception:
                    pass

    # ── Starboard ──
    if str(payload.emoji) != "⭐":
        return

    sb_channel = get_channel_by_name(guild, STARBOARD_CHANNEL_NAME)
    if not sb_channel:
        return

    channel = guild.get_channel(payload.channel_id)
    if not channel or channel.id == sb_channel.id:
        return

    try:
        message = await channel.fetch_message(payload.message_id)
    except Exception:
        return

    star_reaction = discord.utils.get(message.reactions, emoji="⭐")
    star_count = star_reaction.count if star_reaction else 0

    if star_count < STARBOARD_THRESHOLD:
        return

    msg_key = str(payload.message_id)
    existing_sb_id = starboard_data.get(msg_key)

    if existing_sb_id:
        # Update the star count on the existing starboard post
        try:
            sb_msg = await sb_channel.fetch_message(existing_sb_id)
            embed = sb_msg.embeds[0] if sb_msg.embeds else None
            if embed:
                embed.set_footer(text=f"⭐ {star_count} | #{channel.name}")
                await sb_msg.edit(embed=embed)
        except Exception:
            pass
        return

    # First time hitting threshold — post to starboard
    embed = discord.Embed(
        description=message.content or "*[no text content]*",
        color=discord.Color.gold(),
        timestamp=message.created_at
    )
    embed.set_author(
        name=message.author.display_name,
        icon_url=message.author.display_avatar.url
    )
    if message.attachments:
        embed.set_image(url=message.attachments[0].url)
    embed.add_field(name="Original", value=f"[Jump to message]({message.jump_url})", inline=True)
    embed.set_footer(text=f"⭐ {star_count} | #{channel.name}")

    sb_post = await sb_channel.send(embed=embed)
    starboard_data[msg_key] = sb_post.id
    save_json_file(STARBOARD_FILE, starboard_data)

@bot.event
async def on_raw_reaction_remove(payload: discord.RawReactionActionEvent):
    if payload.guild_id is None:
        return

    data = reaction_roles_data.get(str(payload.message_id))
    if not data:
        return

    emoji_str = str(payload.emoji)
    role_id = data.get(emoji_str)
    if not role_id:
        return

    guild = bot.get_guild(payload.guild_id)
    if guild is None:
        return

    member = guild.get_member(payload.user_id)
    role = guild.get_role(role_id)

    if member and role:
        try:
            await member.remove_roles(role, reason="Reaction role removed")
        except Exception:
            pass

@bot.event
async def on_message(message: discord.Message):
    if message.author.bot or not message.guild:
        return

    # Deduplicate — ignore if we've already handled this message
    if message.id in processed_message_ids:
        return
    processed_message_ids.add(message.id)
    if len(processed_message_ids) > 1000:
        processed_message_ids.clear()

    member = message.author
    mention_prompt = None
    if bot.user in message.mentions and not message.content.startswith(BOT_PREFIX):
        mention_prompt = strip_bot_mention(message.content)

    # ── Clear AFK if the user who was AFK sends a message ──
    if get_afk(message.guild.id, message.author.id):
        clear_afk(message.guild.id, message.author.id)
        await message.channel.send(
            f"Welcome back {message.author.mention}! Your AFK status has been cleared.",
            delete_after=6
        )

    # ── Notify when an AFK user is mentioned ──
    for mentioned in message.mentions:
        if mentioned.bot:
            continue
        afk_rec = get_afk(message.guild.id, mentioned.id)
        if afk_rec:
            elapsed = int(time.time() - afk_rec["ts"])
            m, s = divmod(elapsed, 60)
            h, m = divmod(m, 60)
            ago = f"{h}h {m}m" if h else f"{m}m {s}s"
            reason = afk_rec["reason"] or "No reason set"
            await message.channel.send(
                f"💤 **{mentioned.display_name}** is AFK ({ago} ago): *{reason}*",
                delete_after=10
            )

    # ── Only reply to bot mentions outside of commands ──
    if False:
        pass

    # ── Word filter ──
    if not user_is_admin(member):
        hit = message_hits_filter(message.content, message.guild.id)
        if hit:
            try:
                await message.delete()
                await message.channel.send(
                    f"{member.mention} watch your language. That word is filtered here.",
                    delete_after=5
                )
                await log_mod_action(message.guild, f"🤬 Word filter triggered by {member}: `{hit}`")
            except Exception:
                pass
            return

    # ── Anti-link ──
    if settings_data.get("anti_link", True):
        if LINK_REGEX.search(message.content) and not user_is_admin(member):
            try:
                await message.delete()
                await message.channel.send(f"{member.mention} links are blocked here.", delete_after=5)
                await log_mod_action(message.guild, f"🔗 Deleted link from {member}.")
            except Exception:
                pass
            return

    # ── Anti-spam ──
    if settings_data.get("anti_spam", True) and not user_is_admin(member):
        key = (message.guild.id, message.author.id)
        now = asyncio.get_event_loop().time()
        spam_tracker[key].append(now)
        spam_tracker[key] = [t for t in spam_tracker[key] if now - t <= SPAM_WINDOW_SECONDS]

        if len(spam_tracker[key]) >= SPAM_MESSAGE_THRESHOLD:
            try:
                await message.author.timeout(timedelta(minutes=5), reason="Spam detected")
                await message.channel.send(f"{member.mention} got timed out for spamming. {roast_line()}")
                await log_mod_action(message.guild, f"🚫 Auto-timeout: {member} for spam.")
                spam_tracker[key].clear()
            except Exception:
                pass

    # ── Grant XP ──
    leveled_up = await grant_xp(message)
    if leveled_up:
        rec = get_xp_record(message.guild.id, message.author.id)
        embed = discord.Embed(
            description=f"🎉 {message.author.mention} leveled up to **Level {leveled_up}**!",
            color=discord.Color.gold()
        )
        await message.channel.send(embed=embed, delete_after=10)

    # ── Custom commands ──
    guild_cmds = custom_cmds_data.get(str(message.guild.id), {})
    content_lower = message.content.lower().strip()
    for trigger, response in guild_cmds.items():
        if content_lower == trigger.lower() or content_lower == f"{BOT_PREFIX}{trigger.lower()}":
            await message.channel.send(response)
            return

    # ── Trivia answer check ──
    session = trivia_sessions.get(message.channel.id)
    if session and message.author.id != bot.user.id:
        letters = {"a": 0, "b": 1, "c": 2, "d": 3}
        guess_letter = content_lower.strip()
        if guess_letter in letters:
            idx = letters[guess_letter]
            if 0 <= idx < len(session["options"]):
                chosen = session["options"][idx]
                if chosen == session["answer"]:
                    reward = 50
                    add_coins(message.author.id, reward)
                    embed = discord.Embed(
                        description=f"✅ {message.author.mention} got it! The answer was **{session['answer']}**. +{reward} coins!",
                        color=discord.Color.green()
                    )
                else:
                    embed = discord.Embed(
                        description=f"❌ Wrong! The correct answer was **{session['answer']}**.",
                        color=discord.Color.red()
                    )
                del trivia_sessions[message.channel.id]
                await message.channel.send(embed=embed)
                return

    if mention_prompt is not None:
        if mention_prompt:
            async with message.channel.typing():
                reply = build_smart_reply(message.author.id, mention_prompt, use_memory=True)
            await message.channel.send(reply)
        else:
            await message.channel.send(
                f"{random.choice(MENTION_REPLIES)} Try `!chat <message>` or `!mode tech`."
            )
        return

    await bot.process_commands(message)

@bot.event
async def on_command_error(ctx: commands.Context, error):
    # Unwrap CommandInvokeError to get the real cause
    if isinstance(error, commands.CommandInvokeError):
        error = error.original

    if isinstance(error, commands.CheckFailure):
        await ctx.send("You don't have permission to use that command.")
    elif isinstance(error, commands.MissingRequiredArgument):
        await ctx.send(f"Missing argument: `{error.param.name}`. Use `!help {ctx.command}` for usage.")
    elif isinstance(error, commands.BadArgument):
        await ctx.send(f"Invalid argument: {error}")
    elif isinstance(error, commands.CommandNotFound):
        pass  # Ignore unknown commands silently
    elif isinstance(error, discord.ClientException):
        # Voice-related ClientException (e.g. stale connection) — already handled inside command
        pass
    else:
        print(f"[Error] {ctx.command}: {error}")
        await ctx.send(f"Something went wrong: {error}")

# =========================
# HELP COMMAND
# =========================
def build_command_guide_embed() -> discord.Embed:
    embed = discord.Embed(
        title="SpringBot Command Guide",
        description="Prefix: `!` | Use `!help <command>` for details",
        color=discord.Color.blurple()
    )
    sections = [
        ("Moderation", "`!ban` `!kick` `!timeout` `!untimeout` `!warn` `!warnings` `!clearwarnings` `!purge` `!move` `!disconnect` `!lock` `!unlock` `!slowmode` `!announce` `!nick`"),
        ("Music", "`!join` `!play` `!pause` `!resume` `!skip` `!queue` `!leave`"),
        ("Economy", "`!balance` `!daily` `!work` `!pay` `!richest`"),
        ("XP & Levels", "`!rank` `!leaderboard`"),
        ("Fun", "`!8ball` `!coinflip` `!dice` `!rps` `!trivia` `!choose` `!meme` `!joke` `!poll` `!roast`"),
        ("AI Chat (JARVIS Elite Brain)", "`!chat <message>` `!ask <question>` `!mode [name]` `!resetchat` or just mention the bot"),
        ("Knowledge & Learning", "`!solve` `!explain` `!define` `!compare` `!summarize` `!rewrite` `!flashcard` `!studyguide` `!funfact` `!tech` `!search`"),
        ("Languages & Translation", "`!translate <lang> <text>` `!tr <lang> <text>` `!lang <language>` `!languages`"),
        ("Utility", "`!avatar` `!userinfo` `!serverinfo` `!calc` `!remind` `!afk`"),
        ("Server (Admin)", "`!serveraudit` `!setupserver` `!setwelcome` `!setmodlog` `!setautorole` `!setticketcategory` `!lockdownall` `!unlockdownall` `!createchannel` `!deletechannel` `!createrole` `!deleterole` `!ticketpanel` `!closeticket` `!reactionrole` `!settings` `!filter` `!addcmd` `!delcmd` `!listcmds` `!giveaway` `!greroll` `!setcookies` `!cookiestatus` `!clearcookies`"),
    ]
    for name, value in sections:
        embed.add_field(name=name, value=value, inline=False)
    embed.set_footer(text="SpringBot • Intelligent. Fast. A little sarcastic.")
    return embed

class SpringHelpCommand(commands.HelpCommand):
    async def send_bot_help(self, mapping):
        await self.get_destination().send(embed=build_command_guide_embed())

    async def send_command_help(self, command):
        prefix = self.context.clean_prefix
        signature = f"{prefix}{command.qualified_name}"
        if command.signature:
            signature += f" {command.signature}"

        embed = discord.Embed(
            title=f"Help: {command.qualified_name}",
            description=command.help or "No description available.",
            color=discord.Color.blurple()
        )
        embed.add_field(name="Usage", value=f"`{signature}`", inline=False)
        if command.aliases:
            embed.add_field(name="Aliases", value=", ".join(f"`{alias}`" for alias in command.aliases), inline=False)
        embed.set_footer(text="SpringBot • Use !help for the full guide.")
        await self.get_destination().send(embed=embed)

    async def send_group_help(self, group):
        await self.send_command_help(group)

    async def send_cog_help(self, cog):
        await self.send_bot_help({})

    async def send_error_message(self, error):
        await self.get_destination().send(error)

bot.help_command = SpringHelpCommand()
bot.help_command.cog = None

# =========================
# COMMANDS - GENERAL
# =========================
@bot.command(name="springhelp")
async def springhelp(ctx: commands.Context):
    """Show the full SpringBot command guide."""
    await ctx.send_help()

@bot.command(name="ask")
async def ask_anything(ctx: commands.Context, *, question: str):
    """Ask SpringBot about almost anything."""
    async with ctx.typing():
        reply = build_smart_reply(ctx.author.id, question, use_memory=False)
    await ctx.send(reply)

@bot.command(name="tech")
async def ask_tech(ctx: commands.Context, *, question: str):
    """Ask SpringBot a tech or certification question."""
    async with ctx.typing():
        reply = build_smart_reply(ctx.author.id, question, use_memory=False, forced_mode="tech")
    await ctx.send(reply)

@bot.command(name="search")
async def ddg_search(ctx: commands.Context, *, query: str):
    """Search DuckDuckGo and return an instant answer. Example: !search what is TCP/IP"""
    async with ctx.typing():
        result = get_ddg_answer(query)

    if not result:
        await ctx.send(
            f"🔍 No instant answer found for **{query}**.\n"
            f"Try: <https://duckduckgo.com/?q={query.replace(' ', '+')}>"
        )
        return

    embed = discord.Embed(
        title=f"🔍 {query}",
        color=discord.Color.orange()
    )

    if result["answer"]:
        embed.add_field(name="Answer", value=result["answer"], inline=False)

    if result["abstract"]:
        text = result["abstract"]
        if len(text) > 900:
            text = text[:897] + "..."
        embed.add_field(
            name=f"Summary{' — ' + result['source'] if result['source'] else ''}",
            value=text,
            inline=False
        )

    if result["related"]:
        related_lines = "\n".join(
            f"• [{r['text'][:80]}]({r['url']})" for r in result["related"]
        )
        embed.add_field(name="Related", value=related_lines, inline=False)

    if result["url"]:
        embed.add_field(name="Source", value=result["url"], inline=False)

    if result["image"]:
        embed.set_thumbnail(url=result["image"])

    embed.set_footer(text="Powered by DuckDuckGo Instant Answers")
    await ctx.send(embed=embed)

@bot.command(name="chat")
async def chat_with_memory(ctx: commands.Context, *, message: str):
    """Full conversation with memory."""
    async with ctx.typing():
        reply = build_smart_reply(ctx.author.id, message, use_memory=True)
    await ctx.send(reply)

@bot.command(name="mode")
async def change_mode(ctx: commands.Context, mode_name: str = None):
    """Switch style: jarvis / lore / tech / study / chat / brief."""
    if not mode_name:
        current = get_user_mode(ctx.author.id)
        available = ", ".join(SUPPORTED_MODES.keys())
        await ctx.send(f"Current mode: `{current}`\nAvailable modes: {available}")
        return

    mode_key = mode_name.lower().strip()
    if mode_key not in SUPPORTED_MODES:
        await ctx.send(f"Unknown mode. Choose one of: {', '.join(SUPPORTED_MODES.keys())}")
        return

    set_user_mode(ctx.author.id, mode_key)
    await ctx.send(f"Mode set to `{mode_key}`. {SUPPORTED_MODES[mode_key]}")

@bot.command(name="resetchat")
async def reset_chat(ctx: commands.Context):
    """Clear conversation history."""
    clear_chat_history(ctx.author.id)
    await ctx.send("Conversation memory cleared.")

@bot.command(name="solve")
async def solve_problem(ctx: commands.Context, *, problem: str):
    """Step-by-step math or science solver."""
    async with ctx.typing():
        reply = build_solver(problem, ctx.author.id)
    await ctx.send(reply)

@bot.command(name="explain")
async def explain_topic(ctx: commands.Context, *, topic: str):
    """Explain anything simply."""
    async with ctx.typing():
        reply = build_explanation(topic, ctx.author.id)
    await ctx.send(reply)

@bot.command(name="define")
async def define_word(ctx: commands.Context, *, word: str):
    """Definition, etymology, and example usage."""
    async with ctx.typing():
        reply = build_definition(word, ctx.author.id)
    await ctx.send(reply)

@bot.command(name="compare")
async def compare_topics(ctx: commands.Context, *, comparison: str):
    """Side-by-side comparison. Example: !compare TCP vs UDP"""
    if " vs " in comparison.lower():
        left, right = re.split(r"\s+vs\s+", comparison, maxsplit=1, flags=re.IGNORECASE)
    elif " versus " in comparison.lower():
        left, right = re.split(r"\s+versus\s+", comparison, maxsplit=1, flags=re.IGNORECASE)
    else:
        await ctx.send("Use the format `!compare A vs B`.")
        return

    async with ctx.typing():
        reply = build_comparison(left, right, ctx.author.id)
    await ctx.send(reply)

@bot.command(name="summarize")
async def summarize_passage(ctx: commands.Context, *, text: str):
    """Summarize any passage."""
    summary = summarize_text_block(text, 3)
    await ctx.send(maybe_translate_for_user(ctx.author.id, f"Summary: {summary}"))

@bot.command(name="rewrite")
async def rewrite_text(ctx: commands.Context, style: str, *, text: str):
    """Rewrite text in a chosen style: professional / casual / persuasive / formal / simple."""
    reply = build_rewrite(style, text)
    await ctx.send(maybe_translate_for_user(ctx.author.id, reply))

@bot.command(name="flashcard")
async def flashcard_topic(ctx: commands.Context, *, topic: str):
    """Create 5 study flashcards for a topic."""
    async with ctx.typing():
        reply = build_flashcards(topic, ctx.author.id)
    await ctx.send(reply)

@bot.command(name="studyguide")
async def study_guide(ctx: commands.Context, *, topic: str):
    """Build a structured study guide."""
    async with ctx.typing():
        reply = build_studyguide(topic, ctx.author.id)
    await ctx.send(reply)

@bot.command(name="funfact")
async def fun_fact(ctx: commands.Context, *, topic: str = ""):
    """Random or topic-specific fun fact."""
    async with ctx.typing():
        reply = build_fun_fact(topic, ctx.author.id)
    await ctx.send(reply)

@bot.command(name="translate", aliases=["tr"])
async def translate_command(ctx: commands.Context, language: str, *, text: str):
    """Translate text to one of the supported languages."""
    resolved = resolve_language_name(language)
    if not resolved:
        await ctx.send("Unsupported language. Use `!languages` to see the supported list.")
        return

    async with ctx.typing():
        translated = translate_text(text, resolved)

    if not translated:
        await ctx.send("Translation failed right now. Try again in a moment.")
        return

    await ctx.send(f"{resolved.title()}: {translated}")

@bot.command(name="lang")
async def set_language_command(ctx: commands.Context, *, language: str):
    """Set your preferred language for smart-command replies."""
    resolved = resolve_language_name(language)
    if not resolved:
        await ctx.send("Unsupported language. Use `!languages` to see the supported list.")
        return

    set_user_language(ctx.author.id, resolved)
    if resolved == "english":
        await ctx.send("Language preference reset to English.")
    else:
        await ctx.send(f"Language preference set to `{resolved}`.")

@bot.command(name="languages")
async def list_languages(ctx: commands.Context):
    """List the supported languages."""
    await ctx.send("Supported languages: " + build_language_list())

@bot.command(name="roast")
async def roast(ctx: commands.Context, member: discord.Member):
    """Roast someone lightly."""
    await ctx.send(f"{member.mention} — {roast_line()}")

# =========================
# COMMANDS - MODERATION
# =========================
@bot.command(name="ban")
@admin_only()
async def ban_member(ctx: commands.Context, member: discord.Member, *, reason: str = "No reason provided"):
    """Ban a member."""
    try:
        await member.ban(reason=reason, delete_message_seconds=0)
        await ctx.send(f"{member.mention} got banned. Reason: {reason}. {ack_line()}")
        await log_mod_action(ctx.guild, f"🔨 {ctx.author} banned {member}. Reason: {reason}")
    except Exception as e:
        await ctx.send(f"Ban failed: {e}")

@bot.command(name="kick")
@admin_only()
async def kick_member(ctx: commands.Context, member: discord.Member, *, reason: str = "No reason provided"):
    """Kick a member."""
    try:
        await member.kick(reason=reason)
        await ctx.send(f"{member.mention} got kicked. Reason: {reason}. {ack_line()}")
        await log_mod_action(ctx.guild, f"👢 {ctx.author} kicked {member}. Reason: {reason}")
    except Exception as e:
        await ctx.send(f"Kick failed: {e}")

@bot.command(name="timeout")
@admin_only()
async def timeout_member(ctx: commands.Context, member: discord.Member, minutes: int, *, reason: str = "Cooling off"):
    """Timeout a member for a given number of minutes."""
    try:
        await member.timeout(timedelta(minutes=minutes), reason=reason)
        await ctx.send(f"{member.mention} timed out for {minutes} minute(s). Reason: {reason}.")
        await log_mod_action(ctx.guild, f"⏳ {ctx.author} timed out {member} for {minutes} minute(s). Reason: {reason}")
    except Exception as e:
        await ctx.send(f"Timeout failed: {e}")

@bot.command(name="untimeout")
@admin_only()
async def untimeout_member(ctx: commands.Context, member: discord.Member):
    """Remove a member's timeout."""
    try:
        await member.timeout(None)
        await ctx.send(f"Timeout removed for {member.mention}. {ack_line()}")
        await log_mod_action(ctx.guild, f"✅ {ctx.author} removed timeout for {member}.")
    except Exception as e:
        await ctx.send(f"Removing timeout failed: {e}")

@bot.command(name="purge")
@admin_only()
async def purge_messages(ctx: commands.Context, amount: int):
    """Delete a number of recent messages (1–100)."""
    amount = max(1, min(amount, 100))
    try:
        deleted = await ctx.channel.purge(limit=amount + 1)
        await ctx.send(f"Deleted {len(deleted) - 1} message(s).", delete_after=5)
        await log_mod_action(ctx.guild, f"🧹 {ctx.author} purged {len(deleted) - 1} message(s) in #{ctx.channel}.")
    except Exception as e:
        await ctx.send(f"Purge failed: {e}")

@bot.command(name="move")
@admin_only()
async def move_member(ctx: commands.Context, member: discord.Member, channel: discord.VoiceChannel):
    """Move a member to another voice channel."""
    try:
        await member.move_to(channel)
        await ctx.send(f"Moved {member.mention} to **{channel.name}**. {ack_line()}")
        await log_mod_action(ctx.guild, f"🎙️ {ctx.author} moved {member} to {channel.name}.")
    except Exception as e:
        await ctx.send(f"Move failed: {e}")

@bot.command(name="disconnect")
@admin_only()
async def disconnect_member(ctx: commands.Context, member: discord.Member):
    """Disconnect a member from voice."""
    try:
        await member.move_to(None)
        await ctx.send(f"Disconnected {member.mention} from voice.")
        await log_mod_action(ctx.guild, f"🔌 {ctx.author} disconnected {member} from voice.")
    except Exception as e:
        await ctx.send(f"Disconnect failed: {e}")

# =========================
# COMMANDS - WARN SYSTEM
# =========================
@bot.command(name="warn")
@admin_only()
async def warn_member(ctx: commands.Context, member: discord.Member, *, reason: str = "No reason provided"):
    """Warn a member."""
    guild_store = get_or_create_guild_warning_store(ctx.guild.id)
    uid = str(member.id)

    if uid not in guild_store:
        guild_store[uid] = []

    guild_store[uid].append({
        "reason": reason,
        "moderator": str(ctx.author),
    })
    save_json_file(WARNINGS_FILE, warnings_data)

    count = len(guild_store[uid])
    await ctx.send(f"{member.mention} has been warned. Total warnings: {count}.")
    await log_mod_action(ctx.guild, f"⚠️ {ctx.author} warned {member}. Reason: {reason}. Total: {count}")

@bot.command(name="warnings")
@admin_only()
async def view_warnings(ctx: commands.Context, member: discord.Member):
    """View warnings for a member."""
    guild_store = get_or_create_guild_warning_store(ctx.guild.id)
    user_warnings = guild_store.get(str(member.id), [])

    if not user_warnings:
        await ctx.send(f"{member.mention} has no warnings.")
        return

    lines = [f"{i}. {w['reason']} — by {w['moderator']}" for i, w in enumerate(user_warnings, 1)]
    await ctx.send(f"Warnings for {member.mention}:\n" + "\n".join(lines[:20]))

@bot.command(name="clearwarnings")
@admin_only()
async def clear_warnings(ctx: commands.Context, member: discord.Member):
    """Clear all warnings for a member."""
    guild_store = get_or_create_guild_warning_store(ctx.guild.id)
    guild_store[str(member.id)] = []
    save_json_file(WARNINGS_FILE, warnings_data)

    await ctx.send(f"Cleared warnings for {member.mention}.")
    await log_mod_action(ctx.guild, f"🗑️ {ctx.author} cleared warnings for {member}.")

# =========================
# COMMANDS - SETTINGS
# =========================
@bot.command(name="settings")
@admin_only()
async def settings_cmd(ctx: commands.Context, setting_name: str, enabled: str):
    """Toggle anti_link or anti_spam. Usage: !settings anti_link on/off"""
    if setting_name not in {"anti_link", "anti_spam"}:
        await ctx.send("Valid settings: `anti_link`, `anti_spam`")
        return

    value = enabled.lower() in {"on", "true", "yes", "1"}
    settings_data[setting_name] = value
    save_json_file(SETTINGS_FILE, settings_data)
    await ctx.send(f"Set `{setting_name}` to `{'on' if value else 'off'}`.")
    await log_mod_action(ctx.guild, f"⚙️ {ctx.author} set {setting_name} to {value}.")

@bot.command(name="serveraudit")
@admin_only()
async def server_audit(ctx: commands.Context):
    """Audit SpringBot's control over the current server."""
    perms, missing = get_bot_permission_snapshot(ctx.guild)
    config = get_guild_config(ctx.guild.id)
    me = ctx.guild.me or ctx.guild.get_member(bot.user.id if bot.user else 0)

    embed = discord.Embed(
        title="SpringBot Server Audit",
        description="This is how much control the bot currently has in this server.",
        color=discord.Color.blurple()
    )
    embed.add_field(name="Administrator", value="Yes" if perms.administrator else "No", inline=True)
    embed.add_field(name="Top Role", value=me.top_role.mention if me and me.top_role else "Unknown", inline=True)
    embed.add_field(name="Role Position", value=str(me.top_role.position if me and me.top_role else 0), inline=True)
    embed.add_field(
        name="Configured Welcome",
        value=f"<#{config['welcome_channel_id']}>" if config.get("welcome_channel_id") else "Fallback by name",
        inline=False
    )
    embed.add_field(
        name="Configured Mod Log",
        value=f"<#{config['mod_log_channel_id']}>" if config.get("mod_log_channel_id") else "Fallback by name",
        inline=False
    )
    embed.add_field(
        name="Configured Auto Role",
        value=f"<@&{config['auto_role_id']}>" if config.get("auto_role_id") else "Fallback by name",
        inline=False
    )
    embed.add_field(
        name="Protections",
        value=f"anti_link=`{settings_data.get('anti_link', True)}` | anti_spam=`{settings_data.get('anti_spam', True)}`",
        inline=False
    )
    embed.add_field(
        name="Missing Permissions",
        value=", ".join(missing) if missing else "None. SpringBot has the important server-management permissions.",
        inline=False
    )
    embed.set_footer(text="For full control, give the bot role Administrator and move it above the roles/channels it manages.")
    await ctx.send(embed=embed)

@bot.command(name="setupserver")
@admin_only()
async def setup_server(ctx: commands.Context):
    """Create and configure the core channels, category, and autorole SpringBot uses."""
    created = []
    configured = []

    try:
        role = get_role_by_name(ctx.guild, AUTO_ROLE_NAME)
        if role is None and ctx.guild.me.guild_permissions.manage_roles:
            role = await ctx.guild.create_role(name=AUTO_ROLE_NAME, reason="SpringBot server setup")
            created.append(f"Role: {role.name}")
        if role:
            set_guild_config_value(ctx.guild.id, "auto_role_id", role.id)
            configured.append(f"Auto role -> {role.mention}")

        welcome = get_channel_by_name(ctx.guild, WELCOME_CHANNEL_NAME)
        if welcome is None and ctx.guild.me.guild_permissions.manage_channels:
            welcome = await ctx.guild.create_text_channel(WELCOME_CHANNEL_NAME, reason="SpringBot server setup")
            created.append(f"Channel: #{welcome.name}")
        if welcome:
            set_guild_config_value(ctx.guild.id, "welcome_channel_id", welcome.id)
            configured.append(f"Welcome -> {welcome.mention}")

        mod_logs = get_channel_by_name(ctx.guild, MOD_LOG_CHANNEL_NAME)
        if mod_logs is None and ctx.guild.me.guild_permissions.manage_channels:
            mod_logs = await ctx.guild.create_text_channel(MOD_LOG_CHANNEL_NAME, reason="SpringBot server setup")
            created.append(f"Channel: #{mod_logs.name}")
        if mod_logs:
            set_guild_config_value(ctx.guild.id, "mod_log_channel_id", mod_logs.id)
            configured.append(f"Mod logs -> {mod_logs.mention}")

        tickets = get_ticket_category(ctx.guild)
        if tickets is None and ctx.guild.me.guild_permissions.manage_channels:
            tickets = await ctx.guild.create_category(TICKET_CATEGORY_NAME, reason="SpringBot server setup")
            created.append(f"Category: {tickets.name}")
        if tickets:
            set_guild_config_value(ctx.guild.id, "ticket_category_id", tickets.id)
            configured.append(f"Ticket category -> {tickets.name}")

        await ctx.send(
            "Server setup complete.\n"
            + ("Created: " + ", ".join(created) + "\n" if created else "")
            + ("Configured: " + ", ".join(configured) if configured else "Nothing changed.")
        )
        await log_mod_action(ctx.guild, f"🧠 {ctx.author} ran setupserver.")
    except Exception as e:
        await ctx.send(f"Setup failed: {e}")

@bot.command(name="setwelcome")
@admin_only()
async def set_welcome_channel(ctx: commands.Context, channel: discord.TextChannel = None):
    """Set the welcome channel. If omitted, uses the current channel."""
    channel = channel or ctx.channel
    set_guild_config_value(ctx.guild.id, "welcome_channel_id", channel.id)
    await ctx.send(f"Welcome channel set to {channel.mention}.")

@bot.command(name="setmodlog")
@admin_only()
async def set_mod_log_channel(ctx: commands.Context, channel: discord.TextChannel = None):
    """Set the moderation log channel. If omitted, uses the current channel."""
    channel = channel or ctx.channel
    set_guild_config_value(ctx.guild.id, "mod_log_channel_id", channel.id)
    await ctx.send(f"Mod log channel set to {channel.mention}.")

@bot.command(name="setautorole")
@admin_only()
async def set_auto_role(ctx: commands.Context, role: discord.Role = None):
    """Set the autorole assigned to new members. Omit the role to clear it."""
    if role is None:
        set_guild_config_value(ctx.guild.id, "auto_role_id", None)
        await ctx.send("Auto role cleared.")
        return
    set_guild_config_value(ctx.guild.id, "auto_role_id", role.id)
    await ctx.send(f"Auto role set to {role.mention}.")

@bot.command(name="setticketcategory")
@admin_only()
async def set_ticket_category(ctx: commands.Context, category: discord.CategoryChannel = None):
    """Set the ticket category. Uses the current channel's category if omitted."""
    category = category or ctx.channel.category
    if category is None:
        await ctx.send("Mention a category or run this command inside a category.")
        return
    set_guild_config_value(ctx.guild.id, "ticket_category_id", category.id)
    await ctx.send(f"Ticket category set to **{category.name}**.")

@bot.command(name="lockdownall")
@admin_only()
async def lockdown_all(ctx: commands.Context, *, reason: str = "Server lockdown"):
    """Lock all text channels for @everyone."""
    config = get_guild_config(ctx.guild.id)
    state = {}
    changed = 0

    for channel in ctx.guild.text_channels:
        overwrite = channel.overwrites_for(ctx.guild.default_role)
        state[str(channel.id)] = serialize_perm_value(overwrite.send_messages)
        overwrite.send_messages = False
        try:
            await channel.set_permissions(ctx.guild.default_role, overwrite=overwrite, reason=reason)
            changed += 1
        except Exception:
            continue

    config["lockdown_state"] = state
    save_server_config()
    await ctx.send(f"Locked down {changed} text channel(s).")
    await log_mod_action(ctx.guild, f"🔒 {ctx.author} locked down the server. Reason: {reason}")

@bot.command(name="unlockdownall")
@admin_only()
async def unlockdown_all(ctx: commands.Context):
    """Restore channel send permissions after a lockdown."""
    config = get_guild_config(ctx.guild.id)
    state = config.get("lockdown_state", {})
    changed = 0

    for channel in ctx.guild.text_channels:
        key = str(channel.id)
        if key not in state:
            continue
        overwrite = channel.overwrites_for(ctx.guild.default_role)
        overwrite.send_messages = deserialize_perm_value(state[key])
        try:
            await channel.set_permissions(ctx.guild.default_role, overwrite=overwrite, reason="Server unlockdown")
            changed += 1
        except Exception:
            continue

    config["lockdown_state"] = {}
    save_server_config()
    await ctx.send(f"Restored {changed} text channel(s).")
    await log_mod_action(ctx.guild, f"🔓 {ctx.author} removed the server lockdown.")

@bot.command(name="createchannel")
@admin_only()
async def create_channel(ctx: commands.Context, channel_type: str, *, name: str):
    """Create a text or voice channel. Usage: !createchannel text staff-room"""
    clean_name = re.sub(r"[^a-zA-Z0-9 _-]", "", name).strip()
    if not clean_name:
        await ctx.send("Give the new channel a valid name.")
        return

    slug = clean_name.replace(" ", "-").lower()
    kind = channel_type.lower().strip()
    try:
        if kind in {"text", "txt"}:
            channel = await ctx.guild.create_text_channel(slug, reason=f"Created by {ctx.author}")
        elif kind in {"voice", "vc"}:
            channel = await ctx.guild.create_voice_channel(clean_name, reason=f"Created by {ctx.author}")
        else:
            await ctx.send("Channel type must be `text` or `voice`.")
            return
        await ctx.send(f"Created {channel.mention if hasattr(channel, 'mention') else channel.name}.")
        await log_mod_action(ctx.guild, f"🧱 {ctx.author} created channel {channel.name}.")
    except Exception as e:
        await ctx.send(f"Create channel failed: {e}")

@bot.command(name="deletechannel")
@admin_only()
async def delete_channel(ctx: commands.Context, *, target: str = ""):
    """Delete a channel by mention or name. If omitted, deletes the current channel."""
    channel = None
    if ctx.message.channel_mentions:
        channel = ctx.message.channel_mentions[0]
    elif target.strip():
        lookup = target.strip().lower().lstrip("#")
        channel = discord.utils.find(lambda c: c.name.lower() == lookup, ctx.guild.channels)
    else:
        channel = ctx.channel

    if channel is None:
        await ctx.send("I couldn't find that channel.")
        return

    name = channel.name
    try:
        await channel.delete(reason=f"Deleted by {ctx.author}")
        await log_mod_action(ctx.guild, f"🗑️ {ctx.author} deleted channel {name}.")
    except Exception as e:
        await ctx.send(f"Delete channel failed: {e}")

@bot.command(name="createrole")
@admin_only()
async def create_role_cmd(ctx: commands.Context, *, name: str):
    """Create a new role."""
    clean_name = normalize_text(name)
    if not clean_name:
        await ctx.send("Role name cannot be empty.")
        return
    try:
        role = await ctx.guild.create_role(name=clean_name, reason=f"Created by {ctx.author}")
        await ctx.send(f"Created role {role.mention}.")
        await log_mod_action(ctx.guild, f"🏷️ {ctx.author} created role {role.name}.")
    except Exception as e:
        await ctx.send(f"Create role failed: {e}")

@bot.command(name="deleterole")
@admin_only()
async def delete_role_cmd(ctx: commands.Context, role: discord.Role):
    """Delete a role."""
    try:
        role_name = role.name
        await role.delete(reason=f"Deleted by {ctx.author}")
        await ctx.send(f"Deleted role **{role_name}**.")
        await log_mod_action(ctx.guild, f"🗑️ {ctx.author} deleted role {role_name}.")
    except Exception as e:
        await ctx.send(f"Delete role failed: {e}")

# =========================
# COMMANDS - TICKETS
# =========================
@bot.command(name="ticketpanel")
@admin_only()
async def ticketpanel(ctx: commands.Context):
    """Post the ticket creation panel."""
    embed = discord.Embed(
        title="Support Tickets",
        description="Press the button below to create a private ticket.",
        color=discord.Color.blurple()
    )
    await ctx.send(embed=embed, view=TicketView())

@bot.command(name="closeticket")
@admin_only()
async def closeticket(ctx: commands.Context):
    """Close the current ticket channel."""
    if ctx.channel.name.startswith("ticket-"):
        await ctx.send("Closing ticket...")
        await asyncio.sleep(2)
        await ctx.channel.delete(reason="Ticket closed")
    else:
        await ctx.send("This is not a ticket channel.")

# =========================
# COMMANDS - REACTION ROLES
# =========================
@bot.command(name="reactionrole")
@admin_only()
async def reactionrole(ctx: commands.Context, role: discord.Role, emoji: str, *, message_text: str):
    """Create a reaction role message. Usage: !reactionrole @Role 🎮 React for gaming role"""
    embed = discord.Embed(
        title="Reaction Role",
        description=message_text,
        color=discord.Color.gold()
    )
    msg = await ctx.send(embed=embed)
    await msg.add_reaction(emoji)

    reaction_roles_data[str(msg.id)] = {emoji: role.id}
    save_json_file(REACTION_ROLES_FILE, reaction_roles_data)
    await ctx.send(f"Reaction role set for {role.mention} using {emoji}.", delete_after=5)

# =========================
# COMMANDS - MUSIC
# =========================
@bot.command(name="join")
async def join_voice(ctx: commands.Context):
    """Join your voice channel."""
    if IS_REPLIT:
        await ctx.send(
            "🎵 Voice audio isn't available on this host — Replit blocks the UDP ports Discord needs.\n"
            "Use `!play <song>` to get a YouTube link you can open directly instead."
        )
        return
    if not ctx.author.voice or not ctx.author.voice.channel:
        await ctx.send("You need to be in a voice channel first.")
        return
    vc = await ensure_voice_ctx(ctx)
    if vc:
        await ctx.send(f"Joined **{vc.channel.name}**.")
    else:
        await ctx.send("Could not connect to voice.")

@bot.command(name="leave")
async def leave_voice(ctx: commands.Context):
    """Leave the voice channel."""
    vc = ctx.guild.voice_client
    if not vc:
        await ctx.send("I'm not in a voice channel.")
        return

    await vc.disconnect()
    music_queues[ctx.guild.id].clear()
    music_now_playing.pop(ctx.guild.id, None)
    await ctx.send("Left voice. Stage cleared.")

@bot.command(name="play")
async def play_music(ctx: commands.Context, *, query: str):
    """Play a song by name or URL. Example: !play never gonna give you up"""
    status_msg = await ctx.send("Searching...")
    try:
        track = await get_audio_source(query)
    except Exception as e:
        err = str(e)
        if any(k in err.lower() for k in ("sign in", "cookie", "bot", "unavailable")):
            err = "YouTube blocked this request. Try a different song or URL."
        await status_msg.edit(content=f"Could not find a playable track: *{err}*")
        return

    # On Replit, UDP is blocked — voice audio is impossible.
    # Skip the voice attempt entirely and deliver the YouTube link.
    if IS_REPLIT:
        embed = build_track_embed(track, status="Track found")
        embed.set_footer(text="Click the song title above to open it on YouTube.")
        await status_msg.edit(content=None, embed=embed)
        return

    # Non-Replit path — attempt real voice playback
    if not resolve_ffmpeg_executable():
        embed = build_track_embed(track, status="Found - FFmpeg setup needed")
        embed.set_footer(text=ffmpeg_install_hint())
        await status_msg.edit(content=None, embed=embed)
        return

    if not ctx.author.voice or not ctx.author.voice.channel:
        embed = build_track_embed(track, status="Found - join a voice channel then run !play again")
        embed.set_footer(text="Or click the title above to listen on YouTube.")
        await status_msg.edit(content=None, embed=embed)
        return

    vc = await ensure_voice_ctx(ctx)
    if not vc:
        embed = build_track_embed(track, status="Found - could not connect to voice")
        embed.set_footer(text="Click the title above to listen on YouTube.")
        await status_msg.edit(content=None, embed=embed)
        return

    if vc.is_playing() or vc.is_paused():
        music_queues[ctx.guild.id].append(track)
        embed = build_track_embed(track, status="Added to queue")
        await status_msg.edit(content=None, embed=embed)
        return

    try:
        source = create_ffmpeg_source(track)
        music_now_playing[ctx.guild.id] = track

        def after_playing(error):
            if error:
                print(f"[Music] Playback error: {error}")
            future = asyncio.run_coroutine_threadsafe(play_next(ctx.guild), bot.loop)
            try:
                future.result()
            except Exception as ex:
                print(f"[Music] Queue error: {ex}")

        vc.play(source, after=after_playing)
        embed = build_track_embed(track, status="Now playing")
        embed.set_footer(text="Use !queue to see what is coming next.")
        await status_msg.edit(content=None, embed=embed)
    except Exception as e:
        print(f"[Music] FFmpeg start error: {e}")
        embed = build_track_embed(track, status="Found - playback error")
        embed.set_footer(text=shorten(str(e), 180))
        await status_msg.edit(content=None, embed=embed)

@bot.command(name="skip")
async def skip_music(ctx: commands.Context):
    """Skip the current song."""
    vc = ctx.guild.voice_client
    if not vc or (not vc.is_playing() and not vc.is_paused()):
        await ctx.send("Nothing is playing.")
        return

    vc.stop()
    await ctx.send("Skipped.")

@bot.command(name="pause")
async def pause_music(ctx: commands.Context):
    """Pause the current song."""
    vc = ctx.guild.voice_client
    if vc and vc.is_playing():
        vc.pause()
        await ctx.send("Paused.")
    else:
        await ctx.send("Nothing is playing.")

@bot.command(name="resume")
async def resume_music(ctx: commands.Context):
    """Resume the current song."""
    vc = ctx.guild.voice_client
    if vc and vc.is_paused():
        vc.resume()
        await ctx.send("Resumed.")
    else:
        await ctx.send("Nothing is paused.")

@bot.command(name="queue")
async def show_queue(ctx: commands.Context):
    """Show the current music queue."""
    queue = music_queues[ctx.guild.id]
    current = music_now_playing.get(ctx.guild.id)
    if not queue and not current:
        await ctx.send("Queue is empty.")
        return

    lines = []
    if current:
        lines.append(f"Now playing: {current['title']}")
    lines.extend(f"{idx}. {song['title']}" for idx, song in enumerate(queue, start=1))
    await ctx.send("**Current Queue:**\n" + "\n".join(lines[:10]))

# =========================
# COMMANDS - COOKIES (admin)
# =========================
@bot.command(name="setcookies")
async def set_cookies(ctx: commands.Context):
    """Upload a YouTube cookies.txt file so yt-dlp can bypass bot detection.
    Usage: attach a cookies.txt file to your message and type !setcookies"""
    if not user_is_admin(ctx.author):
        await ctx.send("Only admins can set cookies.")
        return

    if not ctx.message.attachments:
        embed = discord.Embed(
            title="📄 How to set up YouTube cookies",
            color=discord.Color.blurple(),
            description=(
                "YouTube requires cookies to confirm you're not a bot.\n\n"
                "**Steps:**\n"
                "1. Install **[Get cookies.txt LOCALLY](https://chrome.google.com/webstore/detail/get-cookiestxt-locally/cclelndahbckbenkjhflpdbgdldlbecc)** "
                "(Chrome) or **[cookies.txt](https://addons.mozilla.org/firefox/addon/cookies-txt/)** (Firefox)\n"
                "2. Go to **[youtube.com](https://youtube.com)** and make sure you're signed in\n"
                "3. Click the extension and export cookies for `youtube.com` as `cookies.txt`\n"
                "4. Come back here and type `!setcookies` with the file **attached** to your message\n\n"
                "*The file must be in Netscape/Mozilla format (the extensions above produce the correct format).*"
            )
        )
        await ctx.send(embed=embed)
        return

    attachment = ctx.message.attachments[0]
    if not attachment.filename.endswith(".txt"):
        await ctx.send("Please attach a `.txt` cookies file.")
        return

    if attachment.size > 2 * 1024 * 1024:  # 2 MB limit
        await ctx.send("File is too large (max 2 MB).")
        return

    data = await attachment.read()

    # Basic validation — must start with correct Netscape header
    text = data.decode("utf-8", errors="replace")
    if not text.strip().startswith("# HTTP Cookie File") and \
       not text.strip().startswith("# Netscape HTTP Cookie File"):
        await ctx.send(
            "Invalid cookies file. The first line must be `# HTTP Cookie File` or "
            "`# Netscape HTTP Cookie File`.\n"
            "Make sure you exported correctly using the browser extension."
        )
        return

    os.makedirs(DATA_DIR, exist_ok=True)
    with open(COOKIES_FILE, "wb") as f:
        f.write(data)

    line_count = text.count("\n")
    await ctx.send(
        f"✅ Cookies saved successfully ({line_count} lines). "
        "YouTube searches will now use your cookies.\n"
        "Try `!play` again!"
    )

@bot.command(name="cookiestatus")
async def cookie_status(ctx: commands.Context):
    """Check whether a YouTube cookies file is loaded."""
    if os.path.isfile(COOKIES_FILE):
        size = os.path.getsize(COOKIES_FILE)
        mtime = os.path.getmtime(COOKIES_FILE)
        age_hours = (time.time() - mtime) / 3600
        age_str = f"{age_hours:.1f} hours ago" if age_hours < 48 else f"{age_hours/24:.1f} days ago"
        await ctx.send(
            f"✅ **Cookies file is present** — {size} bytes, last updated {age_str}.\n"
            "yt-dlp will use it for YouTube requests."
        )
    else:
        await ctx.send(
            "❌ **No cookies file found.** YouTube may block searches.\n"
            "Run `!setcookies` (attach your `cookies.txt`) to fix this."
        )

@bot.command(name="clearcookies")
async def clear_cookies(ctx: commands.Context):
    """Remove the saved cookies file (admin only)."""
    if not user_is_admin(ctx.author):
        await ctx.send("Only admins can clear cookies.")
        return
    if os.path.isfile(COOKIES_FILE):
        os.remove(COOKIES_FILE)
        await ctx.send("🗑️ Cookies file removed.")
    else:
        await ctx.send("No cookies file to remove.")

# =========================
# COMMANDS - ECONOMY
# =========================
@bot.command(name="balance", aliases=["bal", "coins"])
async def balance(ctx: commands.Context, member: discord.Member = None):
    """Check your coin balance."""
    target = member or ctx.author
    rec = get_economy(target.id)
    embed = discord.Embed(title=f"💰 {target.display_name}'s Wallet", color=discord.Color.gold())
    embed.add_field(name="Coins", value=f"**{rec['coins']:,}** 🪙")
    embed.set_thumbnail(url=target.display_avatar.url)
    await ctx.send(embed=embed)

@bot.command(name="daily")
async def daily(ctx: commands.Context):
    """Claim your daily coins (once per 24 hours)."""
    rec = get_economy(ctx.author.id)
    now = time.time()
    cooldown = 86400
    remaining = cooldown - (now - rec.get("daily_ts", 0))
    if remaining > 0:
        h, r = divmod(int(remaining), 3600)
        m = r // 60
        await ctx.send(f"⏳ Daily already claimed. Come back in **{h}h {m}m**.")
        return
    rec["daily_ts"] = now
    new_bal = add_coins(ctx.author.id, DAILY_AMOUNT)
    embed = discord.Embed(
        description=f"💰 {ctx.author.mention} claimed **{DAILY_AMOUNT:,}** daily coins!\nBalance: **{new_bal:,}** 🪙",
        color=discord.Color.gold()
    )
    await ctx.send(embed=embed)

@bot.command(name="work")
async def work(ctx: commands.Context):
    """Work to earn coins (1 hour cooldown)."""
    key = str(ctx.author.id)
    now = time.time()
    remaining = WORK_COOLDOWN - (now - work_cooldowns.get(key, 0))
    if remaining > 0:
        m = int(remaining // 60)
        await ctx.send(f"⏳ You're still tired. Come back in **{m}m**.")
        return
    work_cooldowns[key] = now
    jobs = [
        ("fixed a production bug at 3 AM", "Sysadmin"),
        ("configured a firewall from scratch", "Network Engineer"),
        ("explained DNS to a CEO", "IT Support"),
        ("wrote unit tests nobody asked for", "Developer"),
        ("debugged Python for 2 hours — it was a missing colon", "Programmer"),
        ("updated 47 npm packages and broke everything", "Web Dev"),
    ]
    task, title = random.choice(jobs)
    earned = random.randint(WORK_MIN, WORK_MAX)
    new_bal = add_coins(ctx.author.id, earned)
    embed = discord.Embed(
        title=f"💼 {title}",
        description=f"{ctx.author.mention} {task} and earned **{earned}** 🪙\nBalance: **{new_bal:,}** 🪙",
        color=discord.Color.green()
    )
    await ctx.send(embed=embed)

@bot.command(name="pay")
async def pay(ctx: commands.Context, member: discord.Member, amount: int):
    """Send coins to another member."""
    if member.bot:
        await ctx.send("You can't pay a bot.")
        return
    if member == ctx.author:
        await ctx.send("You can't pay yourself.")
        return
    if amount <= 0:
        await ctx.send("Amount must be positive.")
        return
    sender = get_economy(ctx.author.id)
    if sender["coins"] < amount:
        await ctx.send(f"You only have **{sender['coins']:,}** coins.")
        return
    add_coins(ctx.author.id, -amount)
    new_bal = add_coins(member.id, amount)
    embed = discord.Embed(
        description=f"💸 {ctx.author.mention} sent **{amount:,}** 🪙 to {member.mention}\nTheir new balance: **{new_bal:,}** 🪙",
        color=discord.Color.blurple()
    )
    await ctx.send(embed=embed)

@bot.command(name="richest", aliases=["top", "econlb"])
async def richest(ctx: commands.Context):
    """Show the richest members."""
    sorted_users = sorted(economy_data.items(), key=lambda x: x[1]["coins"], reverse=True)[:10]
    if not sorted_users:
        await ctx.send("No economy data yet.")
        return
    embed = discord.Embed(title="🏆 Richest Members", color=discord.Color.gold())
    medals = ["🥇", "🥈", "🥉"] + ["🏅"] * 7
    lines = []
    for i, (uid, rec) in enumerate(sorted_users):
        user = bot.get_user(int(uid))
        name = user.display_name if user else f"User {uid}"
        lines.append(f"{medals[i]} **{name}** — {rec['coins']:,} 🪙")
    embed.description = "\n".join(lines)
    await ctx.send(embed=embed)

# =========================
# COMMANDS - XP & LEVELING
# =========================
@bot.command(name="rank")
async def rank(ctx: commands.Context, member: discord.Member = None):
    """Show your level and XP."""
    target = member or ctx.author
    rec = get_xp_record(ctx.guild.id, target.id)
    needed = xp_for_level(rec["level"])
    bar = make_xp_bar(rec["xp"], rec["level"])
    embed = discord.Embed(title=f"⭐ {target.display_name}'s Rank", color=discord.Color.blurple())
    embed.add_field(name="Level", value=str(rec["level"]), inline=True)
    embed.add_field(name="XP", value=f"{rec['xp']:,} / {needed:,}", inline=True)
    embed.add_field(name="Progress", value=f"`{bar}`", inline=False)
    embed.set_thumbnail(url=target.display_avatar.url)
    await ctx.send(embed=embed)

@bot.command(name="leaderboard", aliases=["lb"])
async def leaderboard(ctx: commands.Context):
    """Show the top members by level."""
    guild_xp = xp_data.get(str(ctx.guild.id), {})
    sorted_users = sorted(guild_xp.items(), key=lambda x: (x[1]["level"], x[1]["xp"]), reverse=True)[:10]
    if not sorted_users:
        await ctx.send("No XP data yet. Start chatting!")
        return
    medals = ["🥇", "🥈", "🥉"] + ["🏅"] * 7
    embed = discord.Embed(title="🏆 XP Leaderboard", color=discord.Color.gold())
    lines = []
    for i, (uid, rec) in enumerate(sorted_users):
        member = ctx.guild.get_member(int(uid))
        name = member.display_name if member else f"User {uid}"
        lines.append(f"{medals[i]} **{name}** — Level {rec['level']} ({rec['xp']:,} XP)")
    embed.description = "\n".join(lines)
    await ctx.send(embed=embed)

# =========================
# COMMANDS - FUN
# =========================
EIGHT_BALL_RESPONSES = [
    "It is certain.", "Without a doubt.", "You may rely on it.",
    "Yes, definitely.", "As I see it, yes.", "Most likely.", "Outlook good.",
    "Signs point to yes.", "Reply hazy, try again.", "Ask again later.",
    "Better not tell you now.", "Cannot predict now.", "Don't count on it.",
    "My reply is no.", "My sources say no.", "Outlook not so good.", "Very doubtful.",
    "The server lag says maybe.", "DNS says no.", "Consult your sysadmin."
]

@bot.command(name="8ball", aliases=["eightball"])
async def eight_ball(ctx: commands.Context, *, question: str):
    """Ask the magic 8-ball a question."""
    embed = discord.Embed(color=discord.Color.dark_purple())
    embed.add_field(name="🎱 Question", value=question, inline=False)
    embed.add_field(name="Answer", value=random.choice(EIGHT_BALL_RESPONSES), inline=False)
    await ctx.send(embed=embed)

@bot.command(name="coinflip", aliases=["flip"])
async def coinflip(ctx: commands.Context):
    """Flip a coin."""
    result = random.choice(["Heads 🪙", "Tails 🪙"])
    await ctx.send(f"{ctx.author.mention} flipped: **{result}**")

@bot.command(name="dice", aliases=["roll"])
async def dice(ctx: commands.Context, sides: int = 6, count: int = 1):
    """Roll dice. !dice [sides] [count]  e.g. !dice 20 2"""
    if sides < 2 or sides > 1000:
        await ctx.send("Sides must be between 2 and 1000.")
        return
    count = min(count, 10)
    rolls = [random.randint(1, sides) for _ in range(count)]
    total = sum(rolls)
    roll_str = ", ".join(str(r) for r in rolls)
    embed = discord.Embed(
        title=f"🎲 {count}d{sides}",
        description=f"Rolls: **{roll_str}**\nTotal: **{total}**",
        color=discord.Color.orange()
    )
    await ctx.send(embed=embed)

@bot.command(name="rps")
async def rock_paper_scissors(ctx: commands.Context, choice: str):
    """Play rock paper scissors. !rps <rock|paper|scissors>"""
    choices = {"rock": "🪨", "paper": "📄", "scissors": "✂️"}
    choice_lower = choice.lower()
    if choice_lower not in choices:
        await ctx.send("Choose rock, paper, or scissors.")
        return
    bot_choice = random.choice(list(choices.keys()))
    wins = {"rock": "scissors", "paper": "rock", "scissors": "paper"}
    if choice_lower == bot_choice:
        result = "It's a tie!"
        color = discord.Color.yellow()
    elif wins[choice_lower] == bot_choice:
        result = "You win! 🎉"
        color = discord.Color.green()
        add_coins(ctx.author.id, 10)
        result += " +10 🪙"
    else:
        result = "I win. Better luck next time."
        color = discord.Color.red()
    embed = discord.Embed(
        description=f"You: **{choices[choice_lower]} {choice_lower}** vs Me: **{choices[bot_choice]} {bot_choice}**\n{result}",
        color=color
    )
    await ctx.send(embed=embed)

@bot.command(name="trivia")
async def trivia(ctx: commands.Context):
    """Answer a random trivia question for coins."""
    async with ctx.typing():
        q = fetch_trivia()
    if not q:
        await ctx.send("Couldn't fetch a trivia question right now. Try again later.")
        return
    trivia_sessions[ctx.channel.id] = q
    letters = ["A", "B", "C", "D"]
    options_text = "\n".join(f"**{letters[i]}** — {opt}" for i, opt in enumerate(q["options"]))
    embed = discord.Embed(
        title="🧠 Trivia Time!",
        description=q["question"],
        color=discord.Color.blurple()
    )
    embed.add_field(name="Options", value=options_text, inline=False)
    embed.set_footer(text=f"Category: {q['category']} | Difficulty: {q['difficulty']} | Type A/B/C/D to answer | +50 🪙 for correct")
    await ctx.send(embed=embed)

@bot.command(name="choose")
async def choose(ctx: commands.Context, *, options: str):
    """Choose between options separated by |.  e.g. !choose pizza | tacos | sushi"""
    opts = [o.strip() for o in options.split("|") if o.strip()]
    if len(opts) < 2:
        await ctx.send("Give me at least 2 options separated by `|`.")
        return
    chosen = random.choice(opts)
    await ctx.send(f"🤔 I choose: **{chosen}**")

@bot.command(name="meme")
async def meme(ctx: commands.Context):
    """Get a random programmer meme."""
    async with ctx.typing():
        data = fetch_meme()
    if not data:
        await ctx.send("Couldn't load a meme right now.")
        return
    embed = discord.Embed(title=data["title"], url=data["link"], color=discord.Color.orange())
    embed.set_image(url=data["url"])
    embed.set_footer(text=f"👍 {data['ups']:,} | r/ProgrammerHumor")
    await ctx.send(embed=embed)

@bot.command(name="joke")
async def joke(ctx: commands.Context):
    """Get a random tech/programming joke."""
    jokes = [
        "Why do programmers prefer dark mode? Because light attracts bugs.",
        "A SQL query walks into a bar, walks up to two tables and asks... 'Can I join you?'",
        "Why do Java developers wear glasses? Because they don't C#.",
        "!false — it's funny because it's true.",
        "There are only 10 types of people: those who understand binary and those who don't.",
        "Why was the JavaScript developer sad? Because he didn't Node how to Express himself.",
        "A programmer's spouse says: 'Go to the store, get a gallon of milk. If they have eggs, get a dozen.' The programmer comes home with 12 gallons of milk.",
        "Git blame: the most passive-aggressive feature in software.",
        "The cloud is just someone else's computer having a bad day.",
        "It works on my machine. — Famous last words.",
    ]
    await ctx.send(random.choice(jokes))

@bot.command(name="poll")
async def poll(ctx: commands.Context, *, text: str):
    """Create a poll. !poll Question | Option 1 | Option 2 | ..."""
    parts = [p.strip() for p in text.split("|")]
    if len(parts) < 2:
        await ctx.send("Format: `!poll Question | Option 1 | Option 2 ...`")
        return
    question = parts[0]
    options  = parts[1:10]  # max 9 options
    number_emojis = ["1️⃣","2️⃣","3️⃣","4️⃣","5️⃣","6️⃣","7️⃣","8️⃣","9️⃣"]
    embed = discord.Embed(title=f"📊 {question}", color=discord.Color.blurple())
    for i, opt in enumerate(options):
        embed.add_field(name=f"{number_emojis[i]} {opt}", value="\u200b", inline=False)
    embed.set_footer(text=f"Poll by {ctx.author.display_name}")
    msg = await ctx.send(embed=embed)
    for i in range(len(options)):
        await msg.add_reaction(number_emojis[i])

# =========================
# COMMANDS - UTILITY
# =========================
@bot.command(name="avatar", aliases=["av", "pfp"])
async def avatar(ctx: commands.Context, member: discord.Member = None):
    """Show a user's full avatar."""
    target = member or ctx.author
    embed = discord.Embed(title=f"{target.display_name}'s Avatar", color=discord.Color.blurple())
    embed.set_image(url=target.display_avatar.with_size(1024).url)
    await ctx.send(embed=embed)

@bot.command(name="userinfo", aliases=["whois", "ui"])
async def userinfo(ctx: commands.Context, member: discord.Member = None):
    """Show info about a user."""
    target = member or ctx.author
    roles = [r.mention for r in reversed(target.roles) if r.name != "@everyone"]
    embed = discord.Embed(title=f"👤 {target}", color=target.color or discord.Color.blurple())
    embed.set_thumbnail(url=target.display_avatar.url)
    embed.add_field(name="Display Name", value=target.display_name, inline=True)
    embed.add_field(name="ID", value=str(target.id), inline=True)
    embed.add_field(name="Bot", value="Yes" if target.bot else "No", inline=True)
    embed.add_field(name="Account Created", value=target.created_at.strftime("%b %d, %Y"), inline=True)
    embed.add_field(name="Joined Server", value=target.joined_at.strftime("%b %d, %Y") if target.joined_at else "Unknown", inline=True)
    xp_rec = get_xp_record(ctx.guild.id, target.id)
    embed.add_field(name="Level", value=str(xp_rec["level"]), inline=True)
    if roles:
        embed.add_field(name=f"Roles ({len(roles)})", value=" ".join(roles[:10]), inline=False)
    await ctx.send(embed=embed)

@bot.command(name="serverinfo", aliases=["si"])
async def serverinfo(ctx: commands.Context):
    """Show info about the server."""
    g = ctx.guild
    text_channels  = len(g.text_channels)
    voice_channels = len(g.voice_channels)
    bots   = sum(1 for m in g.members if m.bot)
    humans = g.member_count - bots
    embed = discord.Embed(title=f"🏰 {g.name}", color=discord.Color.blurple())
    if g.icon:
        embed.set_thumbnail(url=g.icon.url)
    embed.add_field(name="Owner", value=g.owner.mention if g.owner else "Unknown", inline=True)
    embed.add_field(name="Members", value=f"👥 {humans} humans | 🤖 {bots} bots", inline=True)
    embed.add_field(name="Channels", value=f"💬 {text_channels} text | 🔊 {voice_channels} voice", inline=True)
    embed.add_field(name="Roles", value=str(len(g.roles)), inline=True)
    embed.add_field(name="Created", value=g.created_at.strftime("%b %d, %Y"), inline=True)
    embed.add_field(name="Boost Level", value=f"Level {g.premium_tier} ({g.premium_subscription_count} boosts)", inline=True)
    await ctx.send(embed=embed)

@bot.command(name="calc", aliases=["math"])
async def calc(ctx: commands.Context, *, expression: str):
    """Evaluate a math expression. !calc 2 ** 10 + 5 * 3"""
    result = safe_eval(expression)
    embed = discord.Embed(color=discord.Color.blurple())
    embed.add_field(name="🧮 Expression", value=f"`{expression}`", inline=False)
    embed.add_field(name="Result", value=f"**{result}**", inline=False)
    await ctx.send(embed=embed)

@bot.command(name="remind", aliases=["reminder"])
async def remind(ctx: commands.Context, duration: str, *, message: str):
    """Set a reminder. !remind 10m Check the oven  |  !remind 2h Team meeting"""
    units = {"s": 1, "m": 60, "h": 3600, "d": 86400}
    unit  = duration[-1].lower()
    if unit not in units or not duration[:-1].isdigit():
        await ctx.send("Format: `!remind <number><s/m/h/d> <message>`\nExample: `!remind 30m Take a break`")
        return
    seconds = int(duration[:-1]) * units[unit]
    if seconds > 604800:  # 1 week max
        await ctx.send("Maximum reminder time is 1 week.")
        return
    await ctx.send(f"⏰ Got it! I'll remind you in **{duration}**: *{message}*")
    await asyncio.sleep(seconds)
    try:
        await ctx.author.send(f"⏰ **Reminder:** {message}\n*(Set in {ctx.guild.name} — {ctx.channel.mention})*")
    except Exception:
        await ctx.send(f"⏰ {ctx.author.mention} — **Reminder:** {message}")

@bot.command(name="afk")
async def afk_cmd(ctx: commands.Context, *, reason: str = "AFK"):
    """Set yourself as AFK."""
    set_afk(ctx.guild.id, ctx.author.id, reason)
    await ctx.send(f"💤 {ctx.author.mention} is now AFK: *{reason}*", delete_after=5)

# =========================
# COMMANDS - MODERATION PLUS
# =========================
@bot.command(name="lock")
@admin_only()
async def lock_channel(ctx: commands.Context, channel: discord.TextChannel = None):
    """Lock a channel so members can't send messages."""
    target = channel or ctx.channel
    overwrite = target.overwrites_for(ctx.guild.default_role)
    overwrite.send_messages = False
    await target.set_permissions(ctx.guild.default_role, overwrite=overwrite)
    embed = discord.Embed(description=f"🔒 {target.mention} has been locked.", color=discord.Color.red())
    await ctx.send(embed=embed)
    await log_mod_action(ctx.guild, f"🔒 {ctx.author} locked {target.name}")

@bot.command(name="unlock")
@admin_only()
async def unlock_channel(ctx: commands.Context, channel: discord.TextChannel = None):
    """Unlock a channel."""
    target = channel or ctx.channel
    overwrite = target.overwrites_for(ctx.guild.default_role)
    overwrite.send_messages = None
    await target.set_permissions(ctx.guild.default_role, overwrite=overwrite)
    embed = discord.Embed(description=f"🔓 {target.mention} has been unlocked.", color=discord.Color.green())
    await ctx.send(embed=embed)
    await log_mod_action(ctx.guild, f"🔓 {ctx.author} unlocked {target.name}")

@bot.command(name="slowmode")
@admin_only()
async def slowmode(ctx: commands.Context, seconds: int):
    """Set slowmode on the current channel (0 to disable)."""
    if seconds < 0 or seconds > 21600:
        await ctx.send("Slowmode must be between 0 and 21600 seconds.")
        return
    await ctx.channel.edit(slowmode_delay=seconds)
    if seconds == 0:
        await ctx.send("🐇 Slowmode disabled.")
    else:
        await ctx.send(f"🐢 Slowmode set to **{seconds}s**.")

@bot.command(name="announce")
@admin_only()
async def announce(ctx: commands.Context, *, text: str):
    """Post a styled announcement embed."""
    try:
        await ctx.message.delete()
    except Exception:
        pass
    embed = discord.Embed(
        title="📢 Announcement",
        description=text,
        color=discord.Color.blurple(),
    )
    embed.set_footer(text=f"Posted by {ctx.author.display_name}")
    await ctx.send(embed=embed)

@bot.command(name="nick")
@admin_only()
async def nick(ctx: commands.Context, member: discord.Member, *, new_nick: str):
    """Change a member's nickname."""
    try:
        old = member.display_name
        await member.edit(nick=new_nick)
        await ctx.send(f"✏️ Changed **{old}**'s nickname to **{new_nick}**.")
    except Exception as e:
        await ctx.send(f"Nickname change failed: {e}")

# =========================
# COMMANDS - WORD FILTER
# =========================
@bot.command(name="filter")
@admin_only()
async def word_filter_cmd(ctx: commands.Context, action: str, *, word: str = ""):
    """Manage the word filter. !filter add/remove/list <word>"""
    gid = str(ctx.guild.id)
    if gid not in word_filter_data:
        word_filter_data[gid] = []

    if action == "add":
        if not word:
            await ctx.send("Provide a word to filter.")
            return
        w = word.lower().strip()
        if w in word_filter_data[gid]:
            await ctx.send(f"`{w}` is already filtered.")
            return
        word_filter_data[gid].append(w)
        save_json_file(WORD_FILTER_FILE, word_filter_data)
        await ctx.send(f"✅ Added `{w}` to the word filter.")

    elif action == "remove":
        w = word.lower().strip()
        if w not in word_filter_data[gid]:
            await ctx.send(f"`{w}` is not in the filter list.")
            return
        word_filter_data[gid].remove(w)
        save_json_file(WORD_FILTER_FILE, word_filter_data)
        await ctx.send(f"🗑️ Removed `{w}` from the word filter.")

    elif action == "list":
        words = word_filter_data[gid]
        if not words:
            await ctx.send("No words filtered.")
            return
        await ctx.send(f"🚫 **Filtered words:** {', '.join(f'`{w}`' for w in words)}")

    else:
        await ctx.send("Usage: `!filter add <word>` | `!filter remove <word>` | `!filter list`")

# =========================
# COMMANDS - CUSTOM COMMANDS
# =========================
@bot.command(name="addcmd")
@admin_only()
async def add_custom_cmd(ctx: commands.Context, trigger: str, *, response: str):
    """Add a custom command. !addcmd <trigger> <response>"""
    gid = str(ctx.guild.id)
    if gid not in custom_cmds_data:
        custom_cmds_data[gid] = {}
    trigger_clean = trigger.lower().strip().lstrip("!")
    custom_cmds_data[gid][trigger_clean] = response
    save_json_file(CUSTOM_CMDS_FILE, custom_cmds_data)
    await ctx.send(f"✅ Custom command `!{trigger_clean}` added.")

@bot.command(name="delcmd")
@admin_only()
async def del_custom_cmd(ctx: commands.Context, trigger: str):
    """Remove a custom command."""
    gid = str(ctx.guild.id)
    trigger_clean = trigger.lower().strip().lstrip("!")
    if gid in custom_cmds_data and trigger_clean in custom_cmds_data[gid]:
        del custom_cmds_data[gid][trigger_clean]
        save_json_file(CUSTOM_CMDS_FILE, custom_cmds_data)
        await ctx.send(f"🗑️ Custom command `!{trigger_clean}` removed.")
    else:
        await ctx.send(f"No custom command `!{trigger_clean}` found.")

@bot.command(name="listcmds", aliases=["customcmds"])
async def list_custom_cmds(ctx: commands.Context):
    """List all custom commands for this server."""
    gid = str(ctx.guild.id)
    cmds = custom_cmds_data.get(gid, {})
    if not cmds:
        await ctx.send("No custom commands set up yet. Admins can use `!addcmd`.")
        return
    embed = discord.Embed(title="📋 Custom Commands", color=discord.Color.blurple())
    embed.description = "\n".join(f"`!{k}` → {v[:60]}" for k, v in list(cmds.items())[:20])
    await ctx.send(embed=embed)

# =========================
# COMMANDS - GIVEAWAY
# =========================
active_giveaways: dict[int, dict] = {}  # channel_id -> giveaway info

@bot.command(name="giveaway")
@admin_only()
async def giveaway(ctx: commands.Context, duration: str, *, prize: str):
    """Start a giveaway. !giveaway 1h Nitro Classic"""
    units = {"s": 1, "m": 60, "h": 3600, "d": 86400}
    unit = duration[-1].lower()
    if unit not in units or not duration[:-1].isdigit():
        await ctx.send("Format: `!giveaway <time> <prize>`  e.g. `!giveaway 1h Nitro`")
        return
    seconds = int(duration[:-1]) * units[unit]

    end_time = time.time() + seconds
    embed = discord.Embed(
        title="🎉 GIVEAWAY 🎉",
        description=f"**{prize}**\n\nReact with 🎉 to enter!\nEnds in **{duration}**",
        color=discord.Color.gold()
    )
    embed.set_footer(text=f"Hosted by {ctx.author.display_name} • Ends at")
    embed.timestamp = discord.utils.utcnow().__class__.fromtimestamp(end_time)
    msg = await ctx.send(embed=embed)
    await msg.add_reaction("🎉")

    active_giveaways[ctx.channel.id] = {
        "message_id": msg.id, "prize": prize,
        "host": ctx.author.id, "end": end_time
    }

    await asyncio.sleep(seconds)

    # Re-fetch the message to get accurate reaction counts
    try:
        msg = await ctx.channel.fetch_message(msg.id)
    except Exception:
        return

    reaction = discord.utils.get(msg.reactions, emoji="🎉")
    if not reaction:
        await ctx.send("No one entered the giveaway. 😔")
        return

    users = [u async for u in reaction.users() if not u.bot]
    if not users:
        await ctx.send("No valid entries. Giveaway cancelled.")
        return

    winner = random.choice(users)
    add_coins(winner.id, 500)

    result_embed = discord.Embed(
        title="🎉 Giveaway Ended!",
        description=f"**Prize:** {prize}\n**Winner:** {winner.mention} 🎊\n*(+500 bonus coins awarded!)*",
        color=discord.Color.green()
    )
    await ctx.send(content=winner.mention, embed=result_embed)
    active_giveaways.pop(ctx.channel.id, None)

@bot.command(name="greroll")
@admin_only()
async def greroll(ctx: commands.Context, message_id: int = None):
    """Reroll a giveaway winner by message ID."""
    if not message_id:
        await ctx.send("Provide the giveaway message ID: `!greroll <message_id>`")
        return
    try:
        msg = await ctx.channel.fetch_message(message_id)
    except Exception:
        await ctx.send("Message not found.")
        return
    reaction = discord.utils.get(msg.reactions, emoji="🎉")
    if not reaction:
        await ctx.send("No 🎉 reactions on that message.")
        return
    users = [u async for u in reaction.users() if not u.bot]
    if not users:
        await ctx.send("No valid entries to reroll.")
        return
    winner = random.choice(users)
    await ctx.send(f"🔁 Rerolled! New winner: {winner.mention} 🎊")

# =========================
# RUN
# =========================
if __name__ == "__main__":
    if not DISCORD_TOKEN:
        raise RuntimeError("DISCORD_TOKEN environment variable is not set.")

    def shutdown(sig, frame):
        print(f"Received signal {sig}, shutting down cleanly...")
        asyncio.run_coroutine_threadsafe(bot.close(), bot.loop)

    signal.signal(signal.SIGTERM, shutdown)
    signal.signal(signal.SIGINT, shutdown)

    bot.run(DISCORD_TOKEN)
