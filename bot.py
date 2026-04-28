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
    from openai import OpenAI
except ImportError:
    OpenAI = None

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

print("SPRINGBOT SAFE BUILD ACTIVE")

TOKEN = os.getenv("DISCORD_TOKEN")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
PREFIX = "!"
FFMPEG_PATH = os.getenv("FFMPEG_PATH", "ffmpeg")

client = OpenAI(api_key=OPENAI_API_KEY) if OpenAI and OPENAI_API_KEY else None

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

APLUS_PORTS = [
    ("20/21", "FTP", "File Transfer Protocol"),
    ("22", "SFTP", "Secure File Transfer Protocol"),
    ("22", "SSH", "Secure Shell"),
    ("23", "Telnet", "Remote terminal in plaintext"),
    ("25", "SMTP", "Simple Mail Transfer Protocol"),
    ("53", "DNS", "Domain Name System"),
    ("67/68", "DHCP", "Dynamic Host Configuration Protocol"),
    ("69", "TFTP", "Trivial File Transfer Protocol"),
    ("80", "HTTP", "Hypertext Transfer Protocol"),
    ("110", "POP3", "Post Office Protocol v3"),
    ("137", "NetBIOS", "Network Basic Input/Output System"),
    ("139", "NetBT", "NetBIOS over TCP/IP"),
    ("143", "IMAP4", "Internet Message Access Protocol v4"),
    ("161/162", "SNMP", "Simple Network Management Protocol"),
    ("389", "LDAP", "Lightweight Directory Access Protocol"),
    ("443", "HTTPS", "Hypertext Transfer Protocol Secure"),
    ("445", "SMB", "Server Message Block"),
    ("465", "SMTPS", "Secure SMTP with SSL"),
    ("587", "SMTP", "Secure SMTP with TLS"),
    ("990", "FTPS", "Secure FTP"),
    ("993", "IMAPS/POP3S", "Secure mail retrieval with SSL/TLS"),
    ("3389", "RDP", "Remote Desktop Protocol"),
]

APLUS_TOPICS = {
    "mobile": {
        "title": "1.0 Mobile Devices",
        "summary": [
            "Mobile device batteries commonly use lithium-ion; thermal runaway means the battery gets dangerously hot and may explode.",
            "A swollen battery is usually caused by gas buildup from overcharging, aging, heat, or physical damage.",
            "Laptops often use SODIMM memory because it is smaller than full-size DIMM.",
            "A digitizer converts touch input into coordinates on the screen.",
            "A pointing stick is a small pointing device mounted in the keyboard.",
            "Mobile accessories and connections include USB, USB-C, microUSB, miniUSB, Lightning, tethering/hotspot, stylus, headsets, speakers, and webcams.",
            "A docking station works like a port replicator so the laptop can quickly reconnect to peripherals.",
            "RFID uses radio waves for communication; NFC is a short-range subset often used for contactless payment.",
            "Laptop top halves often include the webcam, microphone, and Wi-Fi antenna.",
            "Mobile device management can enforce policy, support BYOD, and sync mail, contacts, calendars, and cloud storage.",
        ],
        "flashcards": [
            {"q": "What type of RAM is commonly used in laptops?", "a": "SODIMM."},
            {"q": "What does a digitizer do?", "a": "It converts touch input into coordinates or electrical signals the device can understand."},
            {"q": "What is thermal runaway?", "a": "A lithium-ion battery overheating to a dangerous level and potentially catching fire or exploding."},
            {"q": "What is NFC mainly known for?", "a": "Very short-range communication, especially contactless payment and quick data sharing."},
            {"q": "What does a docking station do?", "a": "It acts like a port replicator so peripherals can stay connected while the laptop is removed and reattached."},
        ],
        "quiz": [
            {
                "question": "What memory form factor is most commonly used in laptops?",
                "choices": {"A": "DIMM", "B": "SODIMM", "C": "PCIe", "D": "ATX"},
                "answer": "B",
                "explanation": "Laptops use SODIMM because it is smaller than standard desktop DIMM modules.",
            },
            {
                "question": "What does NFC mainly support in mobile devices?",
                "choices": {"A": "Long-distance satellite calls", "B": "Contactless payment and short-range sharing", "C": "GPU overclocking", "D": "Printer spooling"},
                "answer": "B",
                "explanation": "NFC is a short-range RFID-based technology often used for tap-to-pay and close-range data exchange.",
            },
            {
                "question": "A swollen lithium-ion battery is usually caused by what?",
                "choices": {"A": "Gas buildup from age, heat, or overcharging", "B": "Too much RAM", "C": "Bad Wi-Fi channels", "D": "A failed keyboard ribbon cable"},
                "answer": "A",
                "explanation": "Battery swelling is commonly caused by gas buildup inside the battery from heat, damage, age, or overcharging.",
            },
            {
                "question": "What is the main job of a digitizer?",
                "choices": {"A": "Boost battery life", "B": "Convert touch into signals the device can read", "C": "Increase Wi-Fi range", "D": "Encrypt files"},
                "answer": "B",
                "explanation": "A digitizer turns touch input into usable coordinates or electrical signals.",
            },
            {
                "question": "What does a docking station primarily do?",
                "choices": {"A": "Acts as a port replicator for peripherals", "B": "Replaces the CPU", "C": "Creates a RAID array", "D": "Adds thermal paste"},
                "answer": "A",
                "explanation": "A docking station lets a laptop reconnect quickly to monitors, keyboards, printers, and other ports.",
            },
        ],
    },
    "networking": {
        "title": "2.0 Networking",
        "summary": [
            "Know common ports and protocols: 20/21 FTP, 22 SSH/SFTP, 23 Telnet, 25 SMTP, 53 DNS, 67/68 DHCP, 69 TFTP, 80 HTTP, 110 POP3, 143 IMAP4, 161/162 SNMP, 389 LDAP, 443 HTTPS, 445 SMB, 3389 RDP.",
            "UDP is connectionless like a postcard; TCP is reliable like certified mail with confirmation and retransmission.",
            "Common wireless frequencies are 2.4 GHz, 5 GHz, and 6 GHz.",
            "Wi-Fi 4 is 802.11n, Wi-Fi 5 is 802.11ac, Wi-Fi 6/6e is 802.11ax, and Wi-Fi 7 is 802.11be.",
            "Hosted services include DNS, DHCP, file share, print server, mail server, syslog, AAA, database servers, and NTP.",
            "DNS records to know: SOA, NS, MX, A, AAAA, CNAME, and TXT.",
            "SPF, DKIM, and DMARC are anti-spam protections commonly stored in DNS TXT records.",
            "DHCP automatically assigns IP addresses; leases, reservations, scopes, and exclusions matter.",
            "VLANs segment one physical switch into multiple logical networks; VPNs create secure encrypted tunnels across public networks.",
            "A switch forwards by MAC address, a router connects networks, and a hub broadcasts to every connected device.",
            "PoE standards matter: PoE 15.4W, PoE+ 30W, PoE++ Type 3 60W, PoE++ Type 4 100W.",
            "APIPA is the 169.254.0.0 range and usually appears when DHCP fails.",
            "Private IPs are not routable on the internet; public IPs are accessible on the internet.",
            "Network types include LAN, WAN, PAN, MAN, SAN, and WLAN.",
            "Network tools include a toner probe, punchdown tool, cable tester, loopback plug, crimper, network tap, and Wi-Fi analyzer.",
        ],
        "flashcards": [
            {"q": "What does DHCP do?", "a": "It automatically assigns IP addresses and related settings to devices on a network."},
            {"q": "What does DNS do?", "a": "It resolves hostnames to IP addresses."},
            {"q": "What is APIPA?", "a": "A self-assigned address range starting with 169.254.x.x, usually seen when DHCP fails."},
            {"q": "What does a switch use to forward frames?", "a": "The destination MAC address."},
            {"q": "What is the difference between TCP and UDP?", "a": "TCP is reliable and connection-oriented; UDP is faster and connectionless."},
            {"q": "What is a VLAN?", "a": "A logical segmentation of a network on the same physical switch."},
            {"q": "What is a VPN?", "a": "An encrypted tunnel across a public network for secure communication."},
            {"q": "What does SPF help prevent?", "a": "Unauthorized email senders spoofing your domain."},
        ],
        "quiz": [
            {
                "question": "Which port is used for HTTPS?",
                "choices": {"A": "80", "B": "22", "C": "443", "D": "3389"},
                "answer": "C",
                "explanation": "HTTPS uses port 443.",
            },
            {
                "question": "What service automatically assigns IP addresses to clients?",
                "choices": {"A": "DNS", "B": "DHCP", "C": "LDAP", "D": "SNMP"},
                "answer": "B",
                "explanation": "DHCP automatically assigns IP addresses and related settings to network hosts.",
            },
            {
                "question": "What address range is associated with APIPA?",
                "choices": {"A": "10.0.0.0", "B": "172.16.0.0", "C": "192.168.1.0", "D": "169.254.0.0"},
                "answer": "D",
                "explanation": "APIPA uses the 169.254.0.0 range when a device cannot reach DHCP.",
            },
            {
                "question": "A switch primarily forwards traffic using what value?",
                "choices": {"A": "Subnet mask", "B": "MAC address", "C": "Port speed", "D": "SSID"},
                "answer": "B",
                "explanation": "Layer 2 switches forward frames based on the destination MAC address.",
            },
            {
                "question": "What is the main advantage of TCP over UDP?",
                "choices": {"A": "Longer cable distance", "B": "Reliable, ordered delivery", "C": "Lower power usage", "D": "Built-in Wi-Fi security"},
                "answer": "B",
                "explanation": "TCP confirms delivery, retransmits missing data, and keeps data in order.",
            },
            {
                "question": "Which Wi-Fi standard is Wi-Fi 6/6e?",
                "choices": {"A": "802.11ac", "B": "802.11ax", "C": "802.11n", "D": "802.11be"},
                "answer": "B",
                "explanation": "802.11ax is Wi-Fi 6/6e.",
            },
            {
                "question": "What do SPF, DKIM, and DMARC help protect against?",
                "choices": {"A": "Battery swelling", "B": "Email spoofing and spam abuse", "C": "Monitor burn-in", "D": "CPU overheating"},
                "answer": "B",
                "explanation": "These DNS-based controls help validate email and reduce spoofing and spam abuse.",
            },
            {
                "question": "What does a VLAN do?",
                "choices": {"A": "Creates a secure password vault", "B": "Segments one physical switch into logical networks", "C": "Adds more internet speed", "D": "Turns IPv4 into IPv6"},
                "answer": "B",
                "explanation": "A VLAN logically separates devices into different networks even on the same physical switch.",
            },
        ],
    },
    "hardware": {
        "title": "3.0 Hardware",
        "summary": [
            "Display technologies include LCD, OLED, Mini-LED, plus panel types like TN, IPS, and VA.",
            "A digitizer translates touch into electrical input; an inverter converts DC to AC for an LCD backlight.",
            "Screen attributes to know include pixel density, refresh rate, resolution, and color gamut.",
            "Cable topics include twisted pair, coaxial, fiber, USB, serial, Thunderbolt, HDMI, DisplayPort, DVI, VGA, USB-C, SATA, eSATA, RJ11, RJ45, ST, SC, LC, Molex, Lightning, and DB9.",
            "Know T568A and T568B wiring standards for copper cabling.",
            "RAM concepts include DIMM vs SODIMM, DDR generations, ECC vs non-ECC, and channel configurations.",
            "Storage devices include HDDs and SSDs; SSD interfaces include NVMe, SATA, PCIe, and SAS; common form factors include M.2 and mSATA.",
            "RAID 0 is striping, RAID 1 is mirroring, RAID 5 is striping with parity, RAID 6 is double parity, and RAID 10 is RAID 1+0.",
            "USB flash drives can be USB 2.0 or USB 3.x; FAT32 has a 4 GB single-file limit while exFAT removes that limit.",
            "Optical media to remember: CD up to 700 MB, DVD 4.7 to 8.5 GB, Blu-ray 25 GB or more.",
            "Motherboard form factors include XL-ATX, E-ATX, ATX, Micro-ATX, and Mini-ITX/Mini-ATX depending on the material used.",
            "Modern motherboards typically use a 24-pin power connector; older boards may use 20-pin.",
            "BIOS/UEFI settings to know include boot order, Secure Boot, TPM, virtualization support, fan settings, and passwords.",
            "CPU architectures include x86/x64 and ARM; expansion cards include sound, video, capture, and NIC cards.",
            "Cooling methods include fans, heat sinks, thermal paste/pads, and liquid cooling.",
        ],
        "flashcards": [
            {"q": "What does RAID 1 use?", "a": "Mirroring."},
            {"q": "What SSD form factor is very common in modern systems?", "a": "M.2."},
            {"q": "What is the main difference between ECC and non-ECC RAM?", "a": "ECC can detect and correct certain memory errors; non-ECC cannot."},
            {"q": "What is a common modern motherboard power connector size?", "a": "24-pin."},
            {"q": "What file system removes FAT32's 4 GB single-file limit on large USB drives?", "a": "exFAT."},
            {"q": "What are the three common optical disc generations?", "a": "CD, DVD, and Blu-ray."},
        ],
        "quiz": [
            {
                "question": "Which RAID level is known as mirroring?",
                "choices": {"A": "RAID 0", "B": "RAID 1", "C": "RAID 5", "D": "RAID 10"},
                "answer": "B",
                "explanation": "RAID 1 mirrors data across drives for redundancy.",
            },
            {
                "question": "Which SSD interface is commonly associated with very high-speed modern solid-state storage?",
                "choices": {"A": "VGA", "B": "RJ11", "C": "NVMe", "D": "IDE ribbon"},
                "answer": "C",
                "explanation": "NVMe is a modern high-speed SSD protocol commonly used over PCIe.",
            },
            {
                "question": "What RAM type includes error detection/correction for better data integrity?",
                "choices": {"A": "ECC", "B": "DDR", "C": "SODIMM", "D": "VRAM"},
                "answer": "A",
                "explanation": "ECC RAM can detect and correct certain memory errors.",
            },
            {
                "question": "Which connector is commonly used for Ethernet network cables?",
                "choices": {"A": "RJ45", "B": "RJ11", "C": "DB9", "D": "Molex"},
                "answer": "A",
                "explanation": "RJ45 is the common Ethernet connector.",
            },
            {
                "question": "Which BIOS/UEFI feature helps verify trusted boot components?",
                "choices": {"A": "FAT32", "B": "Secure Boot", "C": "RAID 0", "D": "APIPA"},
                "answer": "B",
                "explanation": "Secure Boot helps validate trusted boot loaders and startup components.",
            },
            {
                "question": "What file system is usually better than FAT32 for a USB drive larger than 32 GB?",
                "choices": {"A": "exFAT", "B": "Telnet", "C": "LDAP", "D": "NTLDR"},
                "answer": "A",
                "explanation": "exFAT removes the FAT32 4 GB single-file limit and is preferred for larger flash drives.",
            },
            {
                "question": "What is the typical modern motherboard main power connector?",
                "choices": {"A": "4-pin", "B": "8-pin", "C": "20-pin", "D": "24-pin"},
                "answer": "D",
                "explanation": "Modern motherboards commonly use a 24-pin main power connector.",
            },
        ],
    },
}

APLUS_TOPIC_ALIASES = {
    "1": "mobile",
    "1.0": "mobile",
    "mobile": "mobile",
    "mobile devices": "mobile",
    "devices": "mobile",
    "2": "networking",
    "2.0": "networking",
    "network": "networking",
    "networking": "networking",
    "ports": "networking",
    "protocols": "networking",
    "3": "hardware",
    "3.0": "hardware",
    "hardware": "hardware",
    "storage": "hardware",
    "display": "hardware",
    "ram": "hardware",
}

APLUS_QUIZ_SESSIONS = {}


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
        value="`!rules`\n`!welcome`\n`!goodbye`\n`!setwelcome`\n`!setgoodbye`\n`!testwelcome`\n`!testgoodbye`",
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
        value="`!join`\n`!leave`\n`!play <soundcloud link or song>`\n`!pause`\n`!resume`\n`!skip`\n`!stop`\n`!nowplaying`",
        inline=False
    )

    embed.add_field(
        name="Moderation",
        value="`!ban`\n`!kick`\n`!purge`",
        inline=False
    )

    embed.add_field(
        name="AI",
        value="`!ask`",
        inline=False
    )

    embed.add_field(
        name="A+ Study",
        value=(
            "`!aplus`\n`!aplusmobile`\n`!aplusnetwork`\n`!aplushardware`\n"
            "`!aplusports`\n`!aplusflash [topic]`\n`!aplusquiz [topic]`\n"
            "`!aplusanswer <A/B/C/D>`\n`!aplussearch <term>`"
        ),
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


@bot.event
async def on_member_remove(member: discord.Member):
    channel = get_goodbye_channel(member.guild)
    if channel:
        message = random.choice(config.get("goodbye_messages", DEFAULT_GOODBYE_MESSAGES)).format(member=member)
        await channel.send(message)


@bot.command(name="help")
async def help_command(ctx):
    await ctx.send(embed=build_help_embed())


@bot.command(name="about")
async def about_command(ctx):
    embed = discord.Embed(
        title="About SpringBot",
        description="SpringBot is a multi-purpose Discord bot with moderation, welcome/goodbye, utility, fun, economy, SoundCloud music, OpenAI-powered chat, and built-in CompTIA A+ Core 1 study commands.",
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


@bot.command(name="userinfo")
async def userinfo_command(ctx, member: discord.Member = None):
    member = member or ctx.author
    embed = discord.Embed(title=f"User Info - {member}", color=discord.Color.green())
    embed.set_thumbnail(url=member.display_avatar.url)
    embed.add_field(name="Username", value=str(member), inline=True)
    embed.add_field(name="Display Name", value=member.display_name, inline=True)
    embed.add_field(name="ID", value=member.id, inline=False)
    embed.add_field(name="Joined Server", value=member.joined_at.strftime("%Y-%m-%d %H:%M:%S") if member.joined_at else "Unknown", inline=False)
    embed.add_field(name="Account Created", value=member.created_at.strftime("%Y-%m-%d %H:%M:%S"), inline=False)
    roles = [role.mention for role in member.roles if role.name != "@everyone"]
    embed.add_field(name="Roles", value=", ".join(roles[:15]) if roles else "No roles", inline=False)
    await ctx.send(embed=embed)


@bot.command(name="serverinfo")
async def serverinfo_command(ctx):
    guild = ctx.guild
    embed = discord.Embed(title=f"Server Info - {guild.name}", color=discord.Color.green())
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
    embed = discord.Embed(title=f"{member.display_name}'s Avatar", color=discord.Color.green())
    embed.set_image(url=member.display_avatar.url)
    await ctx.send(embed=embed)


@bot.command(name="ask")
async def ask_command(ctx, *, question: str):
    if OpenAI is None:
        await ctx.send("The `openai` package is not installed.")
        return

    if client is None:
        await ctx.send("OPENAI_API_KEY is missing.")
        return

    async with ctx.typing():
        try:
            loop = asyncio.get_running_loop()

            def _run():
                response = client.responses.create(
                    model="gpt-5.4-mini",
                    input=(
                        "You are SpringBot, a smart Discord assistant. "
                        "Be clear, helpful, and concise.\n\n"
                        f"User question: {question}"
                    ),
                )
                return response.output_text

            answer = await loop.run_in_executor(None, _run)
        except Exception as e:
            await ctx.send(f"AI error: {e}")
            return

    if not answer:
        await ctx.send("I couldn't generate a response.")
        return

    chunks = [answer[i:i + 1900] for i in range(0, len(answer), 1900)]
    for chunk in chunks:
        await ctx.send(chunk)


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
    embed = discord.Embed(title="🎱 Magic 8-Ball", color=discord.Color.green())
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
    match = re.fullmatch(r"(\d+)d(\d+)", dice)
    if not match:
        await ctx.send("Use `!roll 1d6`, `!roll 2d20`, or `!roll 100`.")
        return
    count = int(match.group(1))
    sides = int(match.group(2))
    if count < 1 or count > 20 or sides < 2 or sides > 1000:
        await ctx.send("Number of dice must be between 1 and 20 and sides between 2 and 1000.")
        return
    rolls = [random.randint(1, sides) for _ in range(count)]
    total = sum(rolls)
    await ctx.send(f"🎲 Rolled **{count}d{sides}**: {', '.join(map(str, rolls))}\n**Total:** {total}")


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

    await ctx.send(f"💸 {ctx.author.mention} claimed **{reward} SpringCoins**.\nNew balance: **{user_record['wallet']} SpringCoins**.")


def chunk_text(text: str, limit: int = 1900) -> list[str]:
    return [text[i:i + limit] for i in range(0, len(text), limit)] or [""]


def normalize_aplus_topic(topic: str | None) -> str | None:
    if not topic:
        return None
    cleaned = re.sub(r"\s+", " ", re.sub(r"[^a-zA-Z0-9+ ]", " ", topic.lower())).strip()
    if cleaned in APLUS_TOPIC_ALIASES:
        return APLUS_TOPIC_ALIASES[cleaned]
    for alias, key in APLUS_TOPIC_ALIASES.items():
        if alias in cleaned:
            return key
    return None


def split_lines(lines: list[str], max_lines: int = 5) -> list[list[str]]:
    return [lines[i:i + max_lines] for i in range(0, len(lines), max_lines)]


def build_aplus_help_embed() -> discord.Embed:
    embed = discord.Embed(
        title="🧠 CompTIA A+ Core 1 Study Commands",
        description="Built from your uploaded Core 1 slides. Use these commands to study inside SpringBot.",
        color=discord.Color.blurple()
    )
    embed.add_field(
        name="Topic Commands",
        value="`!aplus`\n`!aplusmobile`\n`!aplusnetwork`\n`!aplushardware`\n`!aplusports`",
        inline=False
    )
    embed.add_field(
        name="Practice Commands",
        value="`!aplusflash [topic]`\n`!aplusquiz [topic]`\n`!aplusanswer <A/B/C/D>`\n`!aplussearch <term>`",
        inline=False
    )
    embed.add_field(
        name="Available Topics",
        value="`mobile` • `networking` • `hardware`",
        inline=False
    )
    embed.set_footer(text="Examples: !aplusquiz networking | !aplusflash hardware | !aplussearch dhcp")
    return embed


def build_aplus_topic_embed(topic_key: str) -> discord.Embed:
    topic = APLUS_TOPICS[topic_key]
    embed = discord.Embed(
        title=f"📘 {topic['title']}",
        description="Quick study notes from your uploaded slides.",
        color=discord.Color.blurple()
    )
    for idx, group in enumerate(split_lines(topic["summary"], max_lines=5), start=1):
        embed.add_field(
            name="Key Points" if idx == 1 else f"More Notes {idx}",
            value="\n".join(f"• {line}" for line in group),
            inline=False
        )
    embed.add_field(
        name="Try Next",
        value=f"`!aplusflash {topic_key}` • `!aplusquiz {topic_key}` • `!aplussearch {topic_key}`",
        inline=False
    )
    return embed


def build_aplus_ports_embed() -> discord.Embed:
    embed = discord.Embed(
        title="🌐 A+ Ports and Protocols",
        description="Fast memorization list for Core 1 networking.",
        color=discord.Color.blurple()
    )
    rows = [f"`{port}` — **{name}**: {desc}" for port, name, desc in APLUS_PORTS]
    for idx, group in enumerate(split_lines(rows, max_lines=8), start=1):
        embed.add_field(
            name="Ports" if idx == 1 else f"More Ports {idx}",
            value="\n".join(group),
            inline=False
        )
    return embed


def get_all_aplus_flashcards() -> list[dict]:
    cards = []
    for topic_key, topic in APLUS_TOPICS.items():
        for card in topic["flashcards"]:
            cards.append({"topic": topic_key, **card})
    return cards


def get_all_aplus_quiz_questions() -> list[dict]:
    questions = []
    for topic_key, topic in APLUS_TOPICS.items():
        for item in topic["quiz"]:
            questions.append({"topic": topic_key, **item})
    return questions


def search_aplus_notes(term: str) -> list[str]:
    needle = term.lower().strip()
    if not needle:
        return []

    results = []

    for topic_key, topic in APLUS_TOPICS.items():
        for line in topic["summary"]:
            if needle in line.lower():
                results.append(f"[{topic['title']}] {line}")
        for card in topic["flashcards"]:
            haystack = f"{card['q']} {card['a']}".lower()
            if needle in haystack:
                results.append(f"[{topic['title']}] {card['q']} — {card['a']}")

    for port, name, desc in APLUS_PORTS:
        haystack = f"{port} {name} {desc}".lower()
        if needle in haystack:
            results.append(f"[Ports] {port} — {name}: {desc}")

    deduped = []
    seen = set()
    for item in results:
        if item not in seen:
            seen.add(item)
            deduped.append(item)
    return deduped[:12]


def get_quiz_session_key(ctx) -> tuple[int, int]:
    guild_id = ctx.guild.id if ctx.guild else 0
    return guild_id, ctx.channel.id


@bot.command(name="aplus")
async def aplus_command(ctx, *, topic: str = None):
    if not topic:
        await ctx.send(embed=build_aplus_help_embed())
        return

    lowered = topic.lower().strip()
    if lowered in {"help", "topics", "topic", "list", "commands"}:
        await ctx.send(embed=build_aplus_help_embed())
        return
    if lowered in {"ports", "port", "protocols", "protocol"}:
        await ctx.send(embed=build_aplus_ports_embed())
        return

    topic_key = normalize_aplus_topic(topic)
    if topic_key:
        await ctx.send(embed=build_aplus_topic_embed(topic_key))
        return

    results = search_aplus_notes(topic)
    if results:
        message = "🔎 **A+ Search Results**\n" + "\n".join(f"• {item}" for item in results[:8])
        for chunk in chunk_text(message):
            await ctx.send(chunk)
        return

    await ctx.send("A+ topic not found. Use `!aplus` to see the study commands.")


@bot.command(name="aplusmobile")
async def aplusmobile_command(ctx):
    await ctx.send(embed=build_aplus_topic_embed("mobile"))


@bot.command(name="aplusnetwork")
async def aplusnetwork_command(ctx):
    await ctx.send(embed=build_aplus_topic_embed("networking"))


@bot.command(name="aplushardware")
async def aplushardware_command(ctx):
    await ctx.send(embed=build_aplus_topic_embed("hardware"))


@bot.command(name="aplusports")
async def aplusports_command(ctx):
    await ctx.send(embed=build_aplus_ports_embed())


@bot.command(name="aplusflash")
async def aplusflash_command(ctx, *, topic: str = None):
    topic_key = normalize_aplus_topic(topic) if topic else None

    if topic and not topic_key:
        await ctx.send("Unknown topic. Use `mobile`, `networking`, or `hardware`.")
        return

    cards = [
        {"topic": topic_key, **card} for card in APLUS_TOPICS[topic_key]["flashcards"]
    ] if topic_key else get_all_aplus_flashcards()

    card = random.choice(cards)
    embed = discord.Embed(
        title=f"🃏 A+ Flashcard — {APLUS_TOPICS[card['topic']]['title']}",
        color=discord.Color.blurple()
    )
    embed.add_field(name="Question", value=card["q"], inline=False)
    embed.add_field(name="Answer", value=card["a"], inline=False)
    embed.set_footer(text="Use !aplusquiz for practice questions.")
    await ctx.send(embed=embed)


@bot.command(name="aplusquiz")
async def aplusquiz_command(ctx, *, topic: str = None):
    topic_key = normalize_aplus_topic(topic) if topic else None

    if topic and not topic_key:
        await ctx.send("Unknown topic. Use `mobile`, `networking`, or `hardware`.")
        return

    questions = [
        {"topic": topic_key, **item} for item in APLUS_TOPICS[topic_key]["quiz"]
    ] if topic_key else get_all_aplus_quiz_questions()

    question = random.choice(questions)
    session_key = get_quiz_session_key(ctx)
    APLUS_QUIZ_SESSIONS[session_key] = question

    choices_text = "\n".join(
        f"**{letter}.** {choice_text}" for letter, choice_text in question["choices"].items()
    )

    embed = discord.Embed(
        title=f"📝 A+ Quiz — {APLUS_TOPICS[question['topic']]['title']}",
        description=question["question"],
        color=discord.Color.blurple()
    )
    embed.add_field(name="Choices", value=choices_text, inline=False)
    embed.set_footer(text="Reply with !aplusanswer A, B, C, or D")
    await ctx.send(embed=embed)


@bot.command(name="aplusanswer")
async def aplusanswer_command(ctx, choice: str):
    session_key = get_quiz_session_key(ctx)
    session = APLUS_QUIZ_SESSIONS.get(session_key)

    if not session:
        await ctx.send("No active quiz in this channel. Use `!aplusquiz` first.")
        return

    guess = choice.strip().upper()[:1]
    if guess not in {"A", "B", "C", "D"}:
        await ctx.send("Use `!aplusanswer A`, `!aplusanswer B`, `!aplusanswer C`, or `!aplusanswer D`.")
        return

    correct = session["answer"]
    explanation = session["explanation"]
    correct_text = session["choices"][correct]
    del APLUS_QUIZ_SESSIONS[session_key]

    if guess == correct:
        await ctx.send(
            f"✅ Correct. **{correct}** was the right answer: **{correct_text}**\n{explanation}"
        )
        return

    await ctx.send(
        f"❌ Not quite. The correct answer was **{correct}**: **{correct_text}**\n{explanation}"
    )


@bot.command(name="aplussearch")
async def aplussearch_command(ctx, *, term: str):
    results = search_aplus_notes(term)
    if not results:
        await ctx.send("No A+ study matches found for that search.")
        return

    message = "🔎 **A+ Search Results**\n" + "\n".join(f"• {item}" for item in results)
    for chunk in chunk_text(message):
        await ctx.send(chunk)




@bot.command(name="join")
async def join_command(ctx):
    voice_client = await join_author_voice_channel(ctx)
    if voice_client:
        await ctx.send(f"Joined **{voice_client.channel.name}**.")


@bot.command(name="leave")
async def leave_command(ctx):
    voice_client = ctx.guild.voice_client
    if not voice_client or not voice_client.is_connected():
        await ctx.send("I am not in a voice channel.")
        return
    state = get_music_state(ctx.guild.id)
    state.queue.clear()
    state.now_playing = None
    channel_name = voice_client.channel.name
    await voice_client.disconnect()
    await ctx.send(f"Left **{channel_name}**.")


@bot.command(name="play")
async def play_command(ctx, *, query: str):
    if yt_dlp is None:
        await ctx.send("yt-dlp is not installed. Add it to your requirements and redeploy.")
        return

    voice_client = await join_author_voice_channel(ctx)
    if not voice_client:
        return

    state = get_music_state(ctx.guild.id)
    state.text_channel_id = ctx.channel.id

    async with ctx.typing():
        try:
            song = await extract_soundcloud_song_info(query)
        except Exception as e:
            await ctx.send(f"SOUNDCLOUD SAFE BUILD: {e}")
            return

    if not song or not song.get("url"):
        await ctx.send("I could not find a playable SoundCloud audio source.")
        return

    song["requested_by"] = ctx.author

    if voice_client.is_playing() or voice_client.is_paused() or state.now_playing:
        state.queue.append(song)
        await ctx.send(f"➕ Added to queue: **{song['title']}**\nRequested by: {ctx.author.mention}")
        return

    state.queue.append(song)
    await ctx.send(f"🔎 Loaded from SoundCloud: **{song['title']}**")
    await play_next_song(ctx.guild)


@bot.command(name="pause")
async def pause_command(ctx):
    voice_client = ctx.guild.voice_client
    if not voice_client or not voice_client.is_connected():
        await ctx.send("I am not in a voice channel.")
        return
    if not voice_client.is_playing():
        await ctx.send("Nothing is currently playing.")
        return
    voice_client.pause()
    await ctx.send("⏸️ Paused.")


@bot.command(name="resume")
async def resume_command(ctx):
    voice_client = ctx.guild.voice_client
    if not voice_client or not voice_client.is_connected():
        await ctx.send("I am not in a voice channel.")
        return
    if not voice_client.is_paused():
        await ctx.send("Nothing is paused right now.")
        return
    voice_client.resume()
    await ctx.send("▶️ Resumed.")


@bot.command(name="skip")
async def skip_command(ctx):
    voice_client = ctx.guild.voice_client
    if not voice_client or not voice_client.is_connected():
        await ctx.send("I am not in a voice channel.")
        return
    if not voice_client.is_playing() and not voice_client.is_paused():
        await ctx.send("Nothing is currently playing.")
        return
    voice_client.stop()
    await ctx.send("⏭️ Skipped.")


@bot.command(name="stop")
async def stop_command(ctx):
    voice_client = ctx.guild.voice_client
    if not voice_client or not voice_client.is_connected():
        await ctx.send("I am not in a voice channel.")
        return
    state = get_music_state(ctx.guild.id)
    state.queue.clear()
    state.now_playing = None
    if voice_client.is_playing() or voice_client.is_paused():
        voice_client.stop()
    await ctx.send("⏹️ Stopped playback and cleared the queue.")


@bot.command(name="nowplaying")
async def nowplaying_command(ctx):
    state = get_music_state(ctx.guild.id)
    song = state.now_playing
    if not song:
        await ctx.send("Nothing is playing right now.")
        return
    embed = discord.Embed(title="🎶 Now Playing", description=f"**{song['title']}**", color=discord.Color.green())
    embed.add_field(name="Duration", value=format_duration(song.get("duration")), inline=True)
    embed.add_field(name="Uploader", value=song.get("uploader", "Unknown"), inline=True)
    embed.add_field(name="Requested By", value=song["requested_by"].mention, inline=True)
    embed.add_field(name="Link", value=song.get("webpage_url", "N/A"), inline=False)
    if song.get("thumbnail"):
        embed.set_thumbnail(url=song["thumbnail"])
    await ctx.send(embed=embed)


@bot.command(name="ban")
@commands.has_permissions(ban_members=True)
async def ban_command(ctx, member: discord.Member, *, reason: str = "No reason provided."):
    if member == ctx.author or member == ctx.guild.owner:
        await ctx.send("That action is blocked.")
        return
    try:
        await member.ban(reason=f"{reason} | Banned by {ctx.author}")
        await ctx.send(f"🔨 Banned **{member}** | Reason: {reason}")
    except discord.Forbidden:
        await ctx.send("I do not have permission to ban that member.")


@bot.command(name="kick")
@commands.has_permissions(kick_members=True)
async def kick_command(ctx, member: discord.Member, *, reason: str = "No reason provided."):
    if member == ctx.author or member == ctx.guild.owner:
        await ctx.send("That action is blocked.")
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

