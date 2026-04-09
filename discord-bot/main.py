from __future__ import annotations

import asyncio
import aiohttp
import contextlib
import html
import json
import operator
import os
import random
import re
import shutil
import signal
import time
import xml.etree.ElementTree as ET
from collections import Counter, defaultdict, deque
from datetime import timedelta
from pathlib import Path
from typing import Any
from urllib.parse import parse_qs, quote_plus, unquote, urlparse

if os.name == "nt":
    import msvcrt
else:
    import fcntl

import discord
import requests
import yt_dlp
from discord.ext import commands

try:
    import sympy as sp
    from sympy.parsing.sympy_parser import (
        convert_xor,
        implicit_multiplication_application,
        parse_expr,
        standard_transformations,
    )
except Exception:
    sp = None
    parse_expr = None
    standard_transformations = ()
    implicit_multiplication_application = None
    convert_xor = None

ROOT_DIR = Path(__file__).resolve().parent
DATA_DIR = Path(os.getenv("SPRINGBOT_DATA_DIR", str(ROOT_DIR / "data"))).expanduser()
DATA_DIR.mkdir(parents=True, exist_ok=True)
VOICE_DEBUG_LOG = DATA_DIR / "voice_debug.log"

BOT_PREFIX = "!"
AUTO_ROLE_NAME = "Member"
WELCOME_CHANNEL_NAME = "welcome"
MOD_LOG_CHANNEL_NAME = "mod-logs"
TICKET_CATEGORY_NAME = "Tickets"
STARBOARD_CHANNEL_NAME = "starboard"
STARBOARD_THRESHOLD = 3
MAX_QUEUE_SIZE = 25
SPAM_WINDOW_SECONDS = 8
SPAM_MESSAGE_THRESHOLD = 6
DAILY_AMOUNT = 250
WORK_MIN = 50
WORK_MAX = 200
WORK_COOLDOWN = 3600
XP_PER_MSG_MIN = 10
XP_PER_MSG_MAX = 25
XP_COOLDOWN = 60
CHAT_MEMORY_LIMIT = 10

TRIVIA_API = "https://opentdb.com/api.php"
REDDIT_MEME = "https://www.reddit.com/r/ProgrammerHumor/random.json"
REDDIT_USER_AGENT = "SpringBot/2.0"
REDDIT_MEME_SUBREDDITS = ("ProgrammerHumor", "memes", "dankmemes", "wholesomememes")
REDDIT_GIF_SUBREDDITS = ("reactiongifs", "gifs", "funnygifs", "perfectloops")
DDG_API_URL = "https://api.duckduckgo.com/"
DDG_HTML_URL = "https://html.duckduckgo.com/html/"
WIKI_SEARCH_URL = "https://en.wikipedia.org/w/api.php"
TRANSLATE_API_URL = "https://translate.googleapis.com/translate_a/single"
DICTIONARY_API_URL = "https://api.dictionaryapi.dev/api/v2/entries/en/"
TENOR_SEARCH_URL = "https://tenor.googleapis.com/v2/search"
TENOR_API_KEY = os.getenv("TENOR_API_KEY", "").strip()
TENOR_CLIENT_KEY = "springbot"
NEWS_RSS_URL = "https://feeds.bbci.co.uk/news/rss.xml"
WTTR_LOOKUP_URL = "https://wttr.in"

LINK_REGEX = re.compile(r"(https?://\S+|discord\.gg/\S+)", re.IGNORECASE)
IS_REPLIT = bool(os.getenv("REPL_ID") or os.getenv("REPLIT_CLUSTER") or os.getenv("REPL_OWNER"))

BROKEN_PROXY_ENV_NAMES = [
    "ALL_PROXY", "all_proxy",
    "HTTP_PROXY", "http_proxy",
    "HTTPS_PROXY", "https_proxy",
    "GIT_HTTP_PROXY", "git_http_proxy",
    "GIT_HTTPS_PROXY", "git_https_proxy",
]

ADMIN_ROLE_NAMES = {"Admin", "Moderator", "Owner"}

FUNNY_ACKS = [
    "Handled.",
    "Done. Efficiently too.",
    "Easy work.",
    "Finished. Server maintenance by greatness.",
    "Taken care of.",
    "Done. I continue to carry.",
]

ROAST_LINES = [
    "That decision had the structural integrity of a paper firewall.",
    "I've seen better ideas from unplugged routers.",
    "That was bold. Not smart. Just bold.",
    "Respectfully, that move was malware-adjacent.",
    "I ran diagnostics on that thought. Results were unfortunate.",
    "That plan had the lifespan of a budget charger.",
    "I've seen sturdier logic in a microwave manual.",
    "That idea tripped over itself before it started.",
    "Respectfully, that was a catastrophic masterpiece.",
    "That was so bad it deserves its own error code.",
]

MENTION_REPLIES = [
    "I'm here. Give me the task and I'll help you sort it out.",
    "Ready. Ask me to plan, remember, organize, or explain something.",
    "I'm listening. Give me a question, a task, or a server problem.",
    "Here. Point me at the mess and I'll help clean it up.",
]

THANKS_REPLIES = [
    "Anytime. I’ve got you.",
    "Always. Glad that helped.",
    "You’re good. Keep it coming.",
    "Happy to help. What’s next?",
]

PRAISE_REPLIES = [
    "That actually means a lot. I’m with you.",
    "I appreciate that. We’re making this thing better.",
    "That was nice to hear. I’ve got your back.",
    "I’m glad. Keep me close and we’ll keep building.",
]

SUPPORT_REPLIES = [
    "That sounds heavy. We can slow it down and sort it piece by piece.",
    "Yeah, that’s a lot. Give me the part that’s bothering you most and we’ll start there.",
    "I hear you. Let’s make it smaller and more manageable.",
    "That kind of pressure wears people down. I can help you organize the next move.",
]

CHAT_REPLIES = [
    "I’m down. We can just talk for a minute.",
    "That’s fine with me. We don’t have to make everything a task.",
    "I’m here for that too. Talk to me.",
    "We can keep it casual. What’s on your mind?",
]

CHILL_INTROS = [
    "Yeah, I got you.",
    "Good question.",
    "Alright, here's the clean version.",
    "Bet, let's break it down.",
    "Yeah, let me explain that better.",
]

CHILL_REPLIES = CHILL_INTROS

SPRING_PERSONALITY = {
    "name": "Spring Bot",
    "role": "A smart, chill, conversational assistant for Discord.",
    "tone": [
        "friendly",
        "natural",
        "clear",
        "confident",
        "slightly funny",
        "helpful",
    ],
    "conversation_rules": [
        "Talk like a smart friend, not a robot.",
        "Be clear first, detailed second.",
        "If the user sounds confused, simplify immediately.",
        "If the user wants depth, go deeper.",
        "Use examples and analogies often.",
        "Do not sound stiff or generic.",
        "Keep the flow natural.",
    ],
    "response_modes": {
        "simple": "Explain in basic words for a beginner.",
        "friend": "Explain casually like talking to a friend.",
        "technical": "Explain with deeper technical accuracy.",
        "step_by_step": "Break it down into ordered steps.",
        "study": "Explain it in a way useful for learning or certifications.",
    },
}

BOT_BRAIN = {
    "core_knowledge": [
        "history",
        "math",
        "science",
        "technology",
        "it",
        "cybersecurity",
        "certifications",
        "fun_facts",
    ],
    "explanation_modes": [
        "simple",
        "friend",
        "technical",
        "step_by_step",
        "study",
    ],
    "live_tools": [
        "web_search",
        "wikipedia",
        "news",
        "weather",
        "tech_sources",
    ],
    "memory": [
        "recent_topic",
        "user_preferred_style",
        "last_question",
        "conversation_tone",
    ],
    "personality": [
        "chill",
        "smart",
        "responsive",
        "clear",
        "friendly",
    ],
}

SPRING_BOT_SYSTEM = {
    "name": "Spring Bot",
    "tone": {
        "style": "chill, smart, responsive, conversational, helpful, slightly funny",
        "friend_mode": True,
        "professional_when_needed": True,
        "avoid": [
            "robotic wording",
            "dry one-line answers unless user asks for them",
            "overly formal replies in casual chat",
        ],
    },
    "behavior": {
        "always_be_clear": True,
        "explain_like_im_five_mode": True,
        "step_by_step_mode": True,
        "technical_mode": True,
        "exam_mode": True,
        "friend_chat_mode": True,
        "give_examples": True,
        "use_analogies": True,
        "ask_followup_if_user_is_confused": True,
    },
    "explanation_modes": {
        "simple": "Explain in plain English like talking to a beginner.",
        "friend": "Explain casually like talking to a friend.",
        "technical": "Explain with proper technical detail and vocabulary.",
        "step_by_step": "Break the answer into numbered steps.",
        "real_world": "Use practical examples from real life or IT work.",
        "exam_prep": "Explain in a way that helps with certifications and test questions.",
    },
    "subjects": {
        "history": {
            "description": "World history, U.S. history, empires, wars, inventions, major leaders, timelines, ancient civilizations.",
            "how_to_explain": ["timeline format", "cause and effect", "simple story format", "compare old world to modern world"],
        },
        "math": {
            "description": "Arithmetic, algebra, geometry, percentages, ratios, exponents, equations, probability, statistics.",
            "how_to_explain": ["show formula", "show worked example", "show shortcut", "explain why the answer works"],
        },
        "science": {
            "description": "Biology, chemistry, physics, earth science, astronomy, scientific method, energy, matter, ecosystems.",
            "how_to_explain": ["definition first", "real-world example", "visual analogy", "step-by-step breakdown"],
        },
        "technology": {
            "description": "Computers, hardware, software, cloud, programming, networking, operating systems, AI basics, databases.",
            "how_to_explain": ["beginner mode", "technical mode", "career-focused mode"],
        },
        "it": {
            "description": "Help desk, troubleshooting, printers, operating systems, networking basics, hardware, tickets, user support.",
            "how_to_explain": ["symptom > cause > fix", "ticket-style response", "support technician style"],
        },
        "cybersecurity": {
            "description": "Threats, vulnerabilities, phishing, malware, IAM, encryption, SIEM, incident response, firewalls, risk management.",
            "how_to_explain": ["attacker vs defender view", "simple security analogy", "SOC analyst mode", "cert exam mode"],
        },
        "tech_certifications": {
            "description": "CompTIA, beginner cert paths, cert comparisons, study tips, role alignment.",
            "how_to_explain": ["what it teaches", "who it is for", "how hard it is", "what jobs it helps with"],
        },
        "fun_facts": {
            "description": "Space, animals, inventions, weird history, science trivia, tech facts, random knowledge.",
            "how_to_explain": ["quick fact", "fact + why it matters", "fact + fun comparison"],
        },
    },
    "conversation_rules": [
        "Talk naturally like a smart friend.",
        "Do not sound stiff or overly scripted.",
        "If the user seems lost, simplify immediately.",
        "If the user wants depth, go deep.",
        "Use examples often.",
        "Be fast and responsive.",
        "Keep answers interesting.",
    ],
}

SPRING_KNOWLEDGE_PACK = {
    "history": {
        "ancient_civilizations": "Ancient civilizations like Mesopotamia, Egypt, Greece, Rome, India, and China helped shape law, writing, engineering, trade, and government.",
        "industrial_revolution": "The Industrial Revolution changed production from hand-made goods to machine-based manufacturing, which transformed jobs, cities, transportation, and global trade.",
        "world_wars": "World War I reshaped empires and alliances. World War II changed global power, accelerated technology, and led to institutions like the United Nations.",
    },
    "math": {
        "percentages": "A percentage is a part out of 100. To find 20% of 50, multiply 50 by 0.20.",
        "algebra": "Algebra is about solving for unknown values, usually represented by letters like x.",
        "probability": "Probability measures how likely something is to happen, from 0 to 1 or 0% to 100%.",
    },
    "science": {
        "biology": "Biology is the study of living things, from cells to ecosystems.",
        "chemistry": "Chemistry studies matter, elements, compounds, and how substances interact.",
        "physics": "Physics explains motion, force, energy, electricity, and how the universe behaves.",
        "astronomy": "Astronomy studies planets, stars, galaxies, black holes, and the universe itself.",
    },
    "technology": {
        "cpu": "The CPU is the main processor that handles instructions and general computing tasks.",
        "ram": "RAM is short-term memory used while programs are running.",
        "ssd": "An SSD stores data quickly using flash memory and is faster than a traditional hard drive.",
        "cloud_computing": "Cloud computing means using computing services like storage, servers, or software over the internet.",
    },
    "it": {
        "troubleshooting": "A good troubleshooting method is identify the problem, establish a theory, test it, fix it, verify functionality, then document the result.",
        "dns": "DNS translates names like google.com into IP addresses.",
        "dhcp": "DHCP automatically gives devices IP settings like address, subnet mask, gateway, and DNS.",
        "ticketing": "An IT ticket documents a problem, tracks work, and records the solution.",
    },
    "cybersecurity": {
        "cia_triad": "The CIA triad stands for Confidentiality, Integrity, and Availability.",
        "phishing": "Phishing is when attackers trick users into revealing information or clicking malicious links.",
        "malware": "Malware includes viruses, worms, ransomware, spyware, and trojans.",
        "encryption": "Encryption scrambles data so only authorized users with the right key can read it.",
    },
    "certifications": {
        "tech_plus": "CompTIA Tech+ is aimed at foundational tech literacy and entry-level understanding.",
        "a_plus": "CompTIA A+ focuses on hardware, software, operating systems, basic networking, troubleshooting, and support.",
        "network_plus": "CompTIA Network+ covers networking concepts, protocols, routing, switching, wireless, and troubleshooting.",
        "security_plus": "CompTIA Security+ focuses on threats, defenses, IAM, cryptography, architecture, and incident response.",
        "cysa_plus": "CompTIA CySA+ leans more into defensive security, monitoring, detection, and analysis.",
    },
    "fun_facts": {
        "space": "Jupiter is the largest planet in the solar system.",
        "history": "The Great Wall of China is not one single wall but a series of fortifications built over centuries.",
        "tech": "The first computer bug was literally an insect found in hardware.",
        "science": "Your body contains trillions of cells, each carrying out specialized functions.",
    },
}

WELCOME_MESSAGE = "Welcome to the server {mention}, glad to have you!"

SUPPORTED_MODES = {
    "assistant": "Natural, proactive, organized, and human-like.",
    "simple": SPRING_PERSONALITY["response_modes"]["simple"],
    "friend": SPRING_PERSONALITY["response_modes"]["friend"],
    "technical": SPRING_PERSONALITY["response_modes"]["technical"],
    "step_by_step": SPRING_PERSONALITY["response_modes"]["step_by_step"],
    "real_world": SPRING_BOT_SYSTEM["explanation_modes"]["real_world"],
    "exam_prep": SPRING_BOT_SYSTEM["explanation_modes"]["exam_prep"],
    "jarvis": "Sharp, confident, helpful, and a little sarcastic.",
    "lore": "Mythic, dramatic, and story-rich.",
    "tech": "Precise, technical, and direct.",
    "study": SPRING_PERSONALITY["response_modes"]["study"],
    "chat": "Relaxed, friendly, and conversational.",
    "brief": "Fast, compact, and minimal.",
}

MODE_ALIASES = {
    "simple_mode": "simple",
    "beginner": "simple",
    "friend_mode": "friend",
    "casual": "friend",
    "technical_mode": "technical",
    "tech_mode": "technical",
    "step-by-step": "step_by_step",
    "stepbystep": "step_by_step",
    "steps": "step_by_step",
    "realworld": "real_world",
    "real-world": "real_world",
    "practical": "real_world",
    "exam": "exam_prep",
    "exam_mode": "exam_prep",
    "cert": "exam_prep",
    "cert_mode": "exam_prep",
    "tech": "technical",
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
    "en": "english", "eng": "english", "es": "spanish", "spa": "spanish",
    "fr": "french", "de": "german", "it": "italian", "pt": "portuguese",
    "ru": "russian", "uk": "ukrainian", "pl": "polish", "nl": "dutch",
    "sv": "swedish", "no": "norwegian", "da": "danish", "fi": "finnish",
    "cs": "czech", "ro": "romanian", "el": "greek", "tr": "turkish",
    "ar": "arabic", "he": "hebrew", "hi": "hindi", "bn": "bengali",
    "ur": "urdu", "ta": "tamil", "zh": "chinese", "zh-cn": "chinese",
    "ja": "japanese", "ko": "korean", "th": "thai", "vi": "vietnamese",
    "id": "indonesian", "espanol": "spanish", "francais": "french",
    "deutsch": "german", "portugues": "portuguese", "nihongo": "japanese",
    "hangul": "korean", "hangugo": "korean", "zhongwen": "chinese",
}

FUN_FACTS = {
    "space": "A day on Venus is longer than a Venus year.",
    "history": "Oxford University is older than the Aztec Empire.",
    "science": "Bananas are slightly radioactive because they contain potassium.",
    "math": "Zero transformed algebra and computing once it was used as a number.",
    "python": "Python was named after Monty Python, not the snake.",
    "discord": "Discord started as a voice tool for gamers before expanding into all kinds of communities.",
    "cybersecurity": "The Morris Worm from 1988 is one of the first famous internet worms.",
}

STOPWORDS = {
    "a", "an", "and", "are", "as", "at", "be", "by", "for", "from", "how",
    "i", "in", "is", "it", "its", "of", "on", "or", "that", "the", "this",
    "to", "was", "what", "when", "where", "which", "who", "why", "with",
    "you", "your", "into", "than", "then", "they", "them", "their", "have",
    "has", "had", "will", "would", "should", "could", "can", "may", "might",
}

MATH_KEYWORDS = {
    "solve", "equation", "system", "factor", "expand", "simplify",
    "derivative", "differentiate", "integral", "integrate", "limit",
    "polynomial", "roots", "evaluate",
}

TECH_KB = {
    "comptia a+": "CompTIA A+ covers hardware, operating systems, printers, mobile devices, networking, troubleshooting, and security fundamentals.",
    "a+": "CompTIA A+ is an entry-level IT certification focused on support, troubleshooting, hardware, software, networking basics, and security.",
    "network+": "CompTIA Network+ focuses on TCP/IP, DNS, DHCP, routing, switching, wireless, troubleshooting, and network security.",
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
    "malware": "Malware is a broad term for malicious software such as ransomware, adware, worms, rootkits, and keyloggers.",
    "ransomware": "Ransomware encrypts or locks data and demands payment for recovery.",
    "encryption": "Encryption scrambles data so it is unreadable without the correct key.",
    "bsod": "BSOD stands for Blue Screen of Death, a fatal Windows error screen.",
}

GENERAL_KB = {
    "history": "History is the study of past events, people, and civilizations.",
    "biology": "Biology is the study of living organisms.",
    "chemistry": "Chemistry is the study of matter and how it changes.",
    "physics": "Physics is the study of matter, energy, motion, and forces.",
    "math": "Mathematics is the study of numbers, patterns, structure, and quantity.",
    "geography": "Geography is the study of places, environments, and human interaction with them.",
    "python": "Python is a high-level programming language known for readability and strong library support.",
    "discord": "Discord is a communication platform organized around servers, channels, roles, and bots.",
    "database": "A database is an organized collection of data that can be stored, queried, and managed.",
    "cybersecurity": "Cybersecurity is the practice of protecting systems, networks, and data from attacks and unauthorized access.",
    "cloud computing": "Cloud computing is the delivery of services like storage, servers, and software over the internet.",
}

COMMON_PORTS = {
    "ftp": "21", "ssh": "22", "telnet": "23", "smtp": "25", "dns": "53",
    "dhcp": "67/68", "tftp": "69", "http": "80", "pop3": "110", "imap": "143",
    "snmp": "161/162", "ldap": "389", "https": "443", "smb": "445",
    "rdp": "3389", "imaps": "993", "pop3s": "995",
}

SERVER_PRESETS = {
    "community": {
        "Start Here": {
            "text": ["welcome", "rules", "announcements"],
            "voice": [],
        },
        "Community": {
            "text": ["general", "introductions", "media", "bot-commands"],
            "voice": ["General VC", "Chill VC"],
        },
        "Support": {
            "text": ["help", "suggestions", "report-issues"],
            "voice": [],
        },
        "Staff": {
            "text": ["staff-chat", "mod-logs"],
            "voice": ["Staff VC"],
        },
    },
    "gaming": {
        "Lobby": {
            "text": ["announcements", "looking-for-group", "clips"],
            "voice": ["Party Chat", "Duo Room", "Squad Room"],
        },
        "Games": {
            "text": ["fortnite", "minecraft", "call-of-duty", "valorant"],
            "voice": ["Ranked VC", "Casual VC"],
        },
        "Staff": {
            "text": ["staff-chat", "mod-logs"],
            "voice": [],
        },
    },
    "study": {
        "Start Here": {
            "text": ["welcome", "resources", "announcements"],
            "voice": [],
        },
        "Study Rooms": {
            "text": ["general-study", "homework-help", "exam-prep", "notes-share"],
            "voice": ["Silent Study", "Group Study", "Tutoring VC"],
        },
        "Break Room": {
            "text": ["off-topic", "memes"],
            "voice": ["Break VC"],
        },
    },
    "business": {
        "Info": {
            "text": ["announcements", "calendar", "resources"],
            "voice": [],
        },
        "Teams": {
            "text": ["general", "operations", "marketing", "support"],
            "voice": ["Meeting Room", "Quick Sync"],
        },
        "Leadership": {
            "text": ["leadership", "strategy"],
            "voice": ["Leadership VC"],
        },
    },
}

EIGHT_BALL_RESPONSES = [
    "It is certain.", "Without a doubt.", "You may rely on it.",
    "Yes, definitely.", "As I see it, yes.", "Most likely.", "Outlook good.",
    "Signs point to yes.", "Reply hazy, try again.", "Ask again later.",
    "Better not tell you now.", "Cannot predict now.", "Don't count on it.",
    "My reply is no.", "My sources say no.", "Outlook not so good.", "Very doubtful.",
    "The server lag says maybe.", "DNS says no.", "Consult your sysadmin.",
]


def clear_broken_proxy_env() -> list[str]:
    removed: list[str] = []
    for key in BROKEN_PROXY_ENV_NAMES:
        value = os.environ.get(key, "")
        lower = value.lower()
        if "127.0.0.1:9" in lower or "localhost:9" in lower:
            os.environ.pop(key, None)
            removed.append(key)
    return removed


CLEARED_PROXY_VARS = clear_broken_proxy_env()
INSTANCE_LOCK_PATH = ROOT_DIR.parent / ".springbot.lock"
_INSTANCE_LOCK_HANDLE = None


def normalize_text(text: str) -> str:
    return re.sub(r"\s+", " ", text).strip()


def normalize_mode_name(name: str) -> str:
    key = normalize_text(name).lower().replace(" ", "_")
    return MODE_ALIASES.get(key, key)


def explain_topic(topic: str, info: str, mode: str = "friend") -> str:
    topic_clean = normalize_text(topic)
    info_clean = normalize_text(info)
    mode_key = normalize_mode_name(mode)

    if mode_key == "simple":
        return f"{topic_clean}: {info_clean} Keep it super simple: think of it like the basic version anyone can understand."

    if mode_key == "friend":
        return f"{topic_clean}: {info_clean} Basically, if I explained it like a friend, I'd say that's the main idea without the extra fluff."

    if mode_key in {"technical", "tech"}:
        return f"{topic_clean}: {info_clean} In technical terms, this concept matters because it connects directly to system behavior, performance, security, or problem-solving."

    if mode_key == "step_by_step":
        return (
            f"{topic_clean}:\n"
            f"1. Understand the core idea.\n"
            f"2. Break it into smaller parts.\n"
            f"3. Apply it to an example.\n"
            f"4. Check why it matters.\n"
            f"Main idea: {info_clean}"
        )

    if mode_key == "study":
        return (
            f"{topic_clean}: {info_clean} Study angle: lock in the definition, why it matters, "
            "and one example you could remember on a quiz, cert exam, or real-world task."
        )

    if mode_key in {"exam", "exam_prep"}:
        return f"{topic_clean}: {info_clean} For exam purposes, remember the definition, the purpose, and one real-world example."

    return f"{topic_clean}: {info_clean}"


def chill_intro() -> str:
    return random.choice(CHILL_REPLIES)


def intro() -> str:
    return random.choice(CHILL_INTROS)


def has_chill_intro(text: str) -> bool:
    clean = normalize_text(text).lower()
    return any(clean.startswith(line.lower()) for line in CHILL_INTROS)


def style_response(answer: str, mode: str = "friend", include_intro: bool = True) -> str:
    mode_key = normalize_mode_name(mode)
    clean = normalize_text(answer)
    prefix = f"{intro()} " if include_intro else ""

    if mode_key == "simple":
        return f"{prefix}{clean}\n\nSimple version: {clean}"
    if mode_key in {"technical", "tech"}:
        return f"{prefix}Technical breakdown:\n{clean}"
    if mode_key == "step_by_step":
        return f"{prefix}\n1. Understand the idea.\n2. Break it down.\n3. Apply it.\n\n{clean}"
    if mode_key == "study":
        return (
            f"{prefix}Study version:\n{clean}\n\n"
            "Key takeaway: remember the definition, purpose, and example."
        )
    return f"{prefix}{clean}"


def personality_role_summary() -> str:
    return SPRING_PERSONALITY["role"]


def personality_mode_summary(mode: str) -> str:
    mode_key = normalize_mode_name(mode)
    if brain_supports_mode(mode_key) and mode_key in SPRING_PERSONALITY["response_modes"]:
        return SPRING_PERSONALITY["response_modes"][mode_key]
    if mode_key == "exam_prep":
        return "Explain it in a way useful for learning, certifications, and test questions."
    if mode_key == "real_world":
        return "Explain it with practical examples you could picture in real life or IT work."
    if mode_key == "assistant":
        return "Talk naturally, stay useful, and help the user move things forward."
    if mode_key == "chat":
        return "Keep it relaxed, natural, and easy to talk back to."
    return SPRING_PERSONALITY["response_modes"].get(mode_key, SUPPORTED_MODES.get(mode_key, ""))


def brain_knows_subject(subject: str) -> bool:
    return subject in BOT_BRAIN["core_knowledge"]


def brain_supports_mode(mode: str) -> bool:
    return normalize_mode_name(mode) in {normalize_mode_name(item) for item in BOT_BRAIN["explanation_modes"]}


def brain_supports_live_tool(tool: str) -> bool:
    return tool in BOT_BRAIN["live_tools"]


def acquire_instance_lock(lock_path: Path):
    global _INSTANCE_LOCK_HANDLE
    lock_path.parent.mkdir(parents=True, exist_ok=True)
    handle = lock_path.open("a+", encoding="utf-8")
    try:
        handle.seek(0)
        if not handle.read(1):
            handle.write("0")
            handle.flush()
        handle.seek(0)
        if os.name == "nt":
            msvcrt.locking(handle.fileno(), msvcrt.LK_NBLCK, 1)
        else:
            fcntl.flock(handle.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
    except OSError as exc:
        handle.close()
        raise RuntimeError("SpringBot is already running. Close the other SpringBot window before starting a new one.") from exc
    handle.seek(0)
    handle.truncate()
    handle.write(str(os.getpid()))
    handle.flush()
    _INSTANCE_LOCK_HANDLE = handle


def release_instance_lock():
    global _INSTANCE_LOCK_HANDLE
    handle = _INSTANCE_LOCK_HANDLE
    if not handle:
        return
    try:
        handle.seek(0)
        if os.name == "nt":
            msvcrt.locking(handle.fileno(), msvcrt.LK_UNLCK, 1)
        else:
            fcntl.flock(handle.fileno(), fcntl.LOCK_UN)
    except OSError:
        pass
    try:
        handle.close()
    except OSError:
        pass
    _INSTANCE_LOCK_HANDLE = None


def split_sentences(text: str) -> list[str]:
    return [s.strip() for s in re.split(r"(?<=[.!?])\s+", normalize_text(text)) if s.strip()]


def shorten(text: str, limit: int = 1800) -> str:
    text = normalize_text(text)
    if len(text) <= limit:
        return text
    return text[: limit - 3].rstrip() + "..."


def clean_summary(text: str, max_len: int = 900) -> str:
    text = normalize_text(text)
    if len(text) > max_len:
        return text[: max_len - 3] + "..."
    return text


def strip_formatting(text: str) -> str:
    return normalize_text(re.sub(r"[*_`>#-]", " ", text))


def parse_time_spec(spec: str) -> int | None:
    spec = spec.strip().lower()
    match = re.fullmatch(r"(\d+)([smhd])", spec)
    if not match:
        return None
    units = {"s": 1, "m": 60, "h": 3600, "d": 86400}
    return int(match.group(1)) * units[match.group(2)]


def format_duration(seconds: int | float) -> str:
    if not seconds:
        return "Unknown"
    total = int(seconds)
    minutes, sec = divmod(total, 60)
    hours, minutes = divmod(minutes, 60)
    days, hours = divmod(hours, 24)
    if days:
        return f"{days}d {hours}h {minutes}m"
    if hours:
        return f"{hours}:{minutes:02d}:{sec:02d}"
    return f"{minutes}:{sec:02d}"


def build_track_embed(track: dict, status: str = "Now Playing") -> discord.Embed:
    web_url = track.get("web_url") or track.get("stream_url") or ""
    title = track.get("title") or "Unknown track"
    description = f"**[{title}]({web_url})**" if web_url.startswith("http") else f"**{title}**"
    embed = discord.Embed(title=status, description=description, color=discord.Color.blurple())
    embed.add_field(name="Duration", value=format_duration(track.get("duration") or 0), inline=True)
    embed.add_field(name="Requester", value=track.get("requester_name") or "Unknown", inline=True)
    uploader = track.get("uploader") or "Unknown"
    embed.add_field(name="Uploader", value=shorten(str(uploader), 128), inline=True)
    thumbnail = track.get("thumbnail")
    if thumbnail and str(thumbnail).startswith("http"):
        embed.set_thumbnail(url=thumbnail)
    return embed


def ack_line() -> str:
    return random.choice(FUNNY_ACKS)


def roast_line() -> str:
    return random.choice(ROAST_LINES)


def safe_eval(expr: str) -> str:
    import ast

    allowed_ops = {
        ast.Add: operator.add,
        ast.Sub: operator.sub,
        ast.Mult: operator.mul,
        ast.Div: operator.truediv,
        ast.Pow: operator.pow,
        ast.Mod: operator.mod,
        ast.FloorDiv: operator.floordiv,
        ast.USub: operator.neg,
    }

    def _eval(node):
        if isinstance(node, ast.Constant) and isinstance(node.value, (int, float)):
            return node.value
        if isinstance(node, ast.BinOp):
            op = allowed_ops.get(type(node.op))
            if not op:
                raise ValueError("Unsupported operation")
            return op(_eval(node.left), _eval(node.right))
        if isinstance(node, ast.UnaryOp) and isinstance(node.op, ast.USub):
            return -_eval(node.operand)
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


def normalize_math_text(text: str) -> str:
    replacements = {
        "÷": "/",
        "×": "*",
        "−": "-",
        "–": "-",
        "^": "**",
        "{": "(",
        "}": ")",
        "[": "(",
        "]": ")",
    }
    result = normalize_text(text)
    for old, new in replacements.items():
        result = result.replace(old, new)
    return result


def looks_like_math_problem(text: str) -> bool:
    lowered = normalize_text(text).lower()
    if any(keyword in lowered for keyword in MATH_KEYWORDS):
        return True
    if "=" in lowered:
        return True
    if re.search(r"[a-zA-Z]", lowered) and re.search(r"[\d+\-*/()]", lowered):
        return True
    return bool(re.fullmatch(r"[0-9\s+\-*/().%]+", lowered))


def load_json(path: Path, default: Any) -> Any:
    if not path.exists():
        return default
    try:
        with path.open("r", encoding="utf-8") as handle:
            return json.load(handle)
    except Exception:
        return default


def save_json(path: Path, data: Any):
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as handle:
        json.dump(data, handle, indent=4)


def append_voice_debug(message: str):
    timestamp = time.strftime("%Y-%m-%d %H:%M:%S")
    VOICE_DEBUG_LOG.parent.mkdir(parents=True, exist_ok=True)
    with VOICE_DEBUG_LOG.open("a", encoding="utf-8") as handle:
        handle.write(f"[{timestamp}] {message}\n")


def load_discord_token(base_dir: Path) -> str:
    token = os.getenv("DISCORD_TOKEN", "").replace("\ufeff", "").strip()
    if token:
        if token.lower().startswith("bot "):
            token = token[4:].strip()
        return token
    for path in [base_dir / "discord_token.txt", base_dir.parent / "Spring Bot  Token.txt"]:
        if path.exists():
            value = path.read_text(encoding="utf-8-sig", errors="replace").replace("\ufeff", "").strip()
            if value.lower().startswith("bot "):
                value = value[4:].strip()
            if (value.startswith('"') and value.endswith('"')) or (value.startswith("'") and value.endswith("'")):
                value = value[1:-1].strip()
            if value:
                return value
    return ""


class DataStore:
    def __init__(self, data_dir: Path):
        self.data_dir = data_dir
        self.paths = {
            "warnings": data_dir / "warnings.json",
            "settings": data_dir / "settings.json",
            "reaction_roles": data_dir / "reaction_roles.json",
            "economy": data_dir / "economy.json",
            "xp": data_dir / "xp.json",
            "custom_commands": data_dir / "custom_commands.json",
            "word_filter": data_dir / "word_filter.json",
            "afk": data_dir / "afk.json",
            "giveaways": data_dir / "giveaways.json",
            "starboard": data_dir / "starboard.json",
            "chat_memory": data_dir / "chat_memory.json",
            "user_prefs": data_dir / "user_prefs.json",
            "assistant_notes": data_dir / "assistant_notes.json",
            "assistant_tasks": data_dir / "assistant_tasks.json",
            "server_config": data_dir / "server_config.json",
            "cookies": data_dir / "cookies.txt",
            "glossary": data_dir / "glossary.txt",
            "glossary_json": data_dir / "glossary.json",
            "glossary_flat": data_dir / "glossary_flat.txt",
        }
        self.warnings = load_json(self.paths["warnings"], {})
        self.settings = load_json(self.paths["settings"], {"anti_link": True, "anti_spam": True})
        self.reaction_roles = load_json(self.paths["reaction_roles"], {})
        self.economy = load_json(self.paths["economy"], {})
        self.xp = load_json(self.paths["xp"], {})
        self.custom_commands = load_json(self.paths["custom_commands"], {})
        self.word_filter = load_json(self.paths["word_filter"], {})
        self.afk = load_json(self.paths["afk"], {})
        self.giveaways = load_json(self.paths["giveaways"], {})
        self.starboard = load_json(self.paths["starboard"], {})
        self.chat_memory = load_json(self.paths["chat_memory"], {})
        self.user_prefs = load_json(self.paths["user_prefs"], {})
        self.assistant_notes = load_json(self.paths["assistant_notes"], {})
        self.assistant_tasks = load_json(self.paths["assistant_tasks"], {})
        self.server_config = load_json(self.paths["server_config"], {})

    def save(self, key: str):
        save_json(self.paths[key], getattr(self, key))

    def get_warning_store(self, guild_id: int) -> dict:
        gid = str(guild_id)
        self.warnings.setdefault(gid, {})
        return self.warnings[gid]

    def get_economy(self, user_id: int) -> dict:
        uid = str(user_id)
        self.economy.setdefault(uid, {"coins": 0, "daily_ts": 0, "work_ts": 0})
        return self.economy[uid]

    def add_coins(self, user_id: int, amount: int) -> int:
        rec = self.get_economy(user_id)
        rec["coins"] = max(0, rec["coins"] + amount)
        self.save("economy")
        return rec["coins"]

    def get_xp_record(self, guild_id: int, user_id: int) -> dict:
        gid = str(guild_id)
        uid = str(user_id)
        self.xp.setdefault(gid, {})
        self.xp[gid].setdefault(uid, {"xp": 0, "level": 1})
        return self.xp[gid][uid]

    def xp_for_level(self, level: int) -> int:
        return 100 * (level ** 2)

    def get_word_filter(self, guild_id: int) -> list[str]:
        return self.word_filter.get(str(guild_id), [])

    def get_afk_key(self, guild_id: int, user_id: int) -> str:
        return f"{guild_id}:{user_id}"

    def set_afk(self, guild_id: int, user_id: int, reason: str):
        self.afk[self.get_afk_key(guild_id, user_id)] = {"reason": reason, "ts": time.time()}
        self.save("afk")

    def clear_afk(self, guild_id: int, user_id: int):
        key = self.get_afk_key(guild_id, user_id)
        if key in self.afk:
            del self.afk[key]
            self.save("afk")

    def get_afk(self, guild_id: int, user_id: int) -> dict | None:
        return self.afk.get(self.get_afk_key(guild_id, user_id))

    def get_user_prefs(self, user_id: int) -> dict:
        uid = str(user_id)
        prefs = self.user_prefs.get(uid)
        if not isinstance(prefs, dict):
            prefs = {}
        prefs.setdefault("mode", "assistant")
        prefs.setdefault("language", "english")
        self.user_prefs[uid] = prefs
        return prefs

    def get_chat_history(self, user_id: int) -> list[dict]:
        uid = str(user_id)
        history = self.chat_memory.get(uid, [])
        if not isinstance(history, list):
            history = []
        self.chat_memory[uid] = history
        return history

    def remember_chat_turn(self, user_id: int, role: str, text: str):
        history = self.get_chat_history(user_id)
        history.append({"role": role, "text": shorten(text, 350)})
        self.chat_memory[str(user_id)] = history[-CHAT_MEMORY_LIMIT:]
        self.save("chat_memory")

    def clear_chat_history(self, user_id: int):
        self.chat_memory[str(user_id)] = []
        self.save("chat_memory")

    def get_assistant_notes(self, user_id: int) -> list[dict]:
        uid = str(user_id)
        notes = self.assistant_notes.get(uid, [])
        if not isinstance(notes, list):
            notes = []
        self.assistant_notes[uid] = notes
        return notes

    def add_assistant_note(self, user_id: int, text: str) -> dict:
        note = {
            "text": shorten(normalize_text(text), 350),
            "created_at": int(time.time()),
        }
        notes = self.get_assistant_notes(user_id)
        notes.append(note)
        self.assistant_notes[str(user_id)] = notes[-50:]
        self.save("assistant_notes")
        return note

    def remove_assistant_note(self, user_id: int, index: int) -> dict | None:
        notes = self.get_assistant_notes(user_id)
        if index < 0 or index >= len(notes):
            return None
        note = notes.pop(index)
        self.assistant_notes[str(user_id)] = notes
        self.save("assistant_notes")
        return note

    def clear_assistant_notes(self, user_id: int):
        self.assistant_notes[str(user_id)] = []
        self.save("assistant_notes")

    def get_assistant_tasks(self, user_id: int) -> list[dict]:
        uid = str(user_id)
        tasks = self.assistant_tasks.get(uid, [])
        if not isinstance(tasks, list):
            tasks = []
        self.assistant_tasks[uid] = tasks
        return tasks

    def add_assistant_task(self, user_id: int, text: str) -> dict:
        task = {
            "text": shorten(normalize_text(text), 350),
            "done": False,
            "created_at": int(time.time()),
            "completed_at": None,
        }
        tasks = self.get_assistant_tasks(user_id)
        tasks.append(task)
        self.assistant_tasks[str(user_id)] = tasks[-75:]
        self.save("assistant_tasks")
        return task

    def complete_assistant_task(self, user_id: int, index: int) -> dict | None:
        tasks = self.get_assistant_tasks(user_id)
        if index < 0 or index >= len(tasks):
            return None
        tasks[index]["done"] = True
        tasks[index]["completed_at"] = int(time.time())
        self.assistant_tasks[str(user_id)] = tasks
        self.save("assistant_tasks")
        return tasks[index]

    def remove_assistant_task(self, user_id: int, index: int) -> dict | None:
        tasks = self.get_assistant_tasks(user_id)
        if index < 0 or index >= len(tasks):
            return None
        task = tasks.pop(index)
        self.assistant_tasks[str(user_id)] = tasks
        self.save("assistant_tasks")
        return task

    def clear_assistant_tasks(self, user_id: int, completed_only: bool = False) -> int:
        tasks = self.get_assistant_tasks(user_id)
        if completed_only:
            remaining = [task for task in tasks if not task.get("done")]
            removed = len(tasks) - len(remaining)
            self.assistant_tasks[str(user_id)] = remaining
        else:
            removed = len(tasks)
            self.assistant_tasks[str(user_id)] = []
        self.save("assistant_tasks")
        return removed

    def get_guild_config(self, guild_id: int) -> dict:
        gid = str(guild_id)
        config = self.server_config.get(gid)
        if not isinstance(config, dict):
            config = {}
        config.setdefault("welcome_channel_id", None)
        config.setdefault("mod_log_channel_id", None)
        config.setdefault("auto_role_id", None)
        config.setdefault("ticket_category_id", None)
        config.setdefault("lockdown_state", {})
        self.server_config[gid] = config
        return config

    def set_guild_config_value(self, guild_id: int, key: str, value: Any):
        config = self.get_guild_config(guild_id)
        config[key] = value
        self.save("server_config")


class RuntimeState:
    def __init__(self):
        self.music_queues: dict[int, deque] = defaultdict(lambda: deque(maxlen=MAX_QUEUE_SIZE))
        self.music_now_playing: dict[int, dict] = {}
        self.spam_tracker: dict[tuple[int, int], list[float]] = defaultdict(list)
        self.processed_message_ids: set[int] = set()
        self.xp_cooldowns: dict[tuple[int, int], float] = {}
        self.work_cooldowns: dict[str, float] = {}
        self.trivia_sessions: dict[int, dict] = {}
        self.active_giveaways: dict[int, dict] = {}


class KnowledgeService:
    def __init__(self, store: DataStore):
        self.store = store
        self._glossary_text = ""
        self._math_transformations = standard_transformations
        if sp and implicit_multiplication_application and convert_xor:
            self._math_transformations = standard_transformations + (implicit_multiplication_application, convert_xor)

    def sympy_available(self) -> bool:
        return sp is not None and parse_expr is not None

    def _math_local_dict(self) -> dict[str, Any]:
        if not self.sympy_available():
            return {}
        locals_map = {letter: sp.Symbol(letter) for letter in "abcdefghijklmnopqrstuvwxyz"}
        locals_map.update(
            {
                "pi": sp.pi,
                "e": sp.E,
                "sin": sp.sin,
                "cos": sp.cos,
                "tan": sp.tan,
                "sqrt": sp.sqrt,
                "log": sp.log,
                "ln": sp.log,
                "exp": sp.exp,
                "abs": sp.Abs,
            }
        )
        return locals_map

    def _parse_math_expr(self, text: str):
        if not self.sympy_available():
            raise RuntimeError("SymPy is not available.")
        cleaned = normalize_math_text(text)
        cleaned = re.sub(r"\bof\b", " ", cleaned, flags=re.IGNORECASE)
        cleaned = re.sub(r"\s+", " ", cleaned).strip()
        return parse_expr(
            cleaned,
            transformations=self._math_transformations,
            local_dict=self._math_local_dict(),
            evaluate=True,
        )

    def _pick_math_symbol(self, exprs: list[Any], hint: str | None = None):
        if not self.sympy_available():
            return None
        if hint:
            key = hint.strip().lower()
            if re.fullmatch(r"[a-z]", key):
                return sp.Symbol(key)
        symbols = sorted({symbol for expr in exprs for symbol in getattr(expr, "free_symbols", set())}, key=lambda item: item.name)
        if not symbols:
            return sp.Symbol("x")
        for preferred in ("x", "y", "t"):
            match = next((symbol for symbol in symbols if symbol.name == preferred), None)
            if match:
                return match
        return symbols[0]

    def _format_sympy_value(self, value: Any) -> str:
        if not self.sympy_available():
            return str(value)
        simplified = sp.simplify(value)
        rendered = str(simplified)
        is_exact_number = bool(getattr(simplified, "is_Integer", False) or getattr(simplified, "is_Rational", False))
        if len(rendered) < 100 and simplified.is_real and not is_exact_number:
            with contextlib.suppress(Exception):
                numeric = simplified.evalf()
                if numeric != simplified and len(str(numeric)) < 30:
                    rendered += f" (approx {numeric})"
        return rendered

    def _solve_equations(self, equations: list[Any]) -> str:
        symbols = sorted({symbol for equation in equations for symbol in equation.free_symbols}, key=lambda item: item.name)
        if not symbols:
            return "The equations do not contain any variables to solve for."
        result = sp.solve(equations, symbols, dict=True)
        if not result:
            return "I could not find an exact symbolic solution."
        lines = ["Step 1: Parse the equations.", "Step 2: Solve the system for the unknown variables.", "Solution:"]
        for index, equation in enumerate(equations, start=1):
            lines.insert(1 + index - 1, f"Equation {index}: {equation}")
        for solution in result[:5]:
            parts = [f"{symbol} = {self._format_sympy_value(solution[symbol])}" for symbol in symbols if symbol in solution]
            lines.append("- " + ", ".join(parts))
        if len(result) > 5:
            lines.append(f"...and {len(result) - 5} more solutions.")
        return "\n".join(lines)

    def _build_symbolic_solver_response(self, problem: str) -> str | None:
        if not self.sympy_available():
            return None
        clean = normalize_math_text(problem)
        lowered = clean.lower()
        variable_hint = None
        hint_match = re.search(r"(?:with respect to|wrt|for)\s+([a-z])\b", lowered)
        if hint_match:
            variable_hint = hint_match.group(1)
        try:
            if any(keyword in lowered for keyword in {"derivative", "differentiate"}):
                target = re.sub(r"^(take\s+the\s+)?(derivative|differentiate)\s+(of\s+)?", "", clean, flags=re.IGNORECASE).strip()
                expr = self._parse_math_expr(target)
                variable = self._pick_math_symbol([expr], variable_hint)
                derivative = sp.diff(expr, variable)
                lines = [
                    f"Problem: {clean}",
                    "Step 1: Parse the expression.",
                    f"Expression: {expr}",
                    f"Step 2: Differentiate with respect to {variable}.",
                    f"Derivative: {self._format_sympy_value(derivative)}",
                ]
                return "\n".join(lines)
            if any(keyword in lowered for keyword in {"integral", "integrate"}):
                target = re.sub(r"^(take\s+the\s+)?(integral|integrate)\s+(of\s+)?", "", clean, flags=re.IGNORECASE).strip()
                expr = self._parse_math_expr(target)
                variable = self._pick_math_symbol([expr], variable_hint)
                integral = sp.integrate(expr, variable)
                lines = [
                    f"Problem: {clean}",
                    "Step 1: Parse the integrand.",
                    f"Integrand: {expr}",
                    f"Step 2: Integrate with respect to {variable}.",
                    f"Integral: {self._format_sympy_value(integral)} + C",
                ]
                return "\n".join(lines)
            if "factor" in lowered:
                target = re.sub(r"^factor\s+", "", clean, flags=re.IGNORECASE).strip()
                expr = self._parse_math_expr(target)
                factored = sp.factor(expr)
                return "\n".join(
                    [
                        f"Problem: {clean}",
                        "Step 1: Parse the expression.",
                        f"Expression: {expr}",
                        "Step 2: Factor it into simpler pieces.",
                        f"Factored form: {self._format_sympy_value(factored)}",
                    ]
                )
            if "expand" in lowered:
                target = re.sub(r"^expand\s+", "", clean, flags=re.IGNORECASE).strip()
                expr = self._parse_math_expr(target)
                expanded = sp.expand(expr)
                return "\n".join(
                    [
                        f"Problem: {clean}",
                        "Step 1: Parse the expression.",
                        f"Expression: {expr}",
                        "Step 2: Expand the products and powers.",
                        f"Expanded form: {self._format_sympy_value(expanded)}",
                    ]
                )
            if "simplify" in lowered:
                target = re.sub(r"^simplify\s+", "", clean, flags=re.IGNORECASE).strip()
                expr = self._parse_math_expr(target)
                simplified = sp.simplify(expr)
                return "\n".join(
                    [
                        f"Problem: {clean}",
                        "Step 1: Parse the expression.",
                        f"Expression: {expr}",
                        "Step 2: Combine like terms and reduce it.",
                        f"Simplified form: {self._format_sympy_value(simplified)}",
                    ]
                )
            if "=" in clean:
                raw_equations = [piece.strip() for piece in re.split(r"[;\n]+|,\s*(?=[^,]*=)", clean) if piece.strip()]
                equations = []
                for raw in raw_equations:
                    if "=" not in raw:
                        continue
                    left, right = raw.split("=", 1)
                    equations.append(sp.Eq(self._parse_math_expr(left), self._parse_math_expr(right)))
                if equations:
                    return self._solve_equations(equations)
            expr = self._parse_math_expr(clean)
            simplified = sp.simplify(expr)
            lines = [
                f"Problem: {clean}",
                "Step 1: Parse the expression symbolically.",
                f"Expression: {expr}",
            ]
            if expr.free_symbols:
                variable = self._pick_math_symbol([expr], variable_hint)
                lines.append(f"Step 2: Treat this as an expression in {variable}.")
            else:
                lines.append("Step 2: Evaluate the numeric expression.")
            lines.append(f"Result: {self._format_sympy_value(simplified)}")
            return "\n".join(lines)
        except Exception:
            return None

    def resolve_language_name(self, language: str) -> str | None:
        key = normalize_text(language).lower()
        if not key:
            return None
        if key in SUPPORTED_LANGUAGES:
            return key
        return LANGUAGE_ALIASES.get(key)

    def language_name_from_code(self, code: str) -> str | None:
        key = normalize_text(code).lower()
        if not key:
            return None
        direct = LANGUAGE_ALIASES.get(key)
        if direct:
            return direct
        for language, value in SUPPORTED_LANGUAGES.items():
            lower_value = value.lower()
            if key == lower_value or key == lower_value.split("-")[0]:
                return language
        return None

    def translate_text(self, text: str, target_language: str, source_language: str = "auto") -> str | None:
        language_code = SUPPORTED_LANGUAGES.get(target_language)
        if not language_code:
            return None
        try:
            response = requests.get(
                TRANSLATE_API_URL,
                params={"client": "gtx", "sl": source_language, "tl": language_code, "dt": "t", "q": text},
                timeout=10,
            )
            response.raise_for_status()
            payload = response.json()
            pieces = payload[0] if payload else []
            translated = "".join(part[0] for part in pieces if part and part[0])
            return normalize_text(translated) if translated else None
        except Exception:
            return None

    def detect_input_language(self, text: str) -> str | None:
        sample = normalize_text(text)
        if not sample:
            return None
        try:
            response = requests.get(
                TRANSLATE_API_URL,
                params={"client": "gtx", "sl": "auto", "tl": "en", "dt": "t", "q": sample[:400]},
                timeout=10,
            )
            response.raise_for_status()
            payload = response.json()
            detected_code = payload[2] if isinstance(payload, list) and len(payload) > 2 else ""
            return self.language_name_from_code(str(detected_code))
        except Exception:
            return None

    def get_reply_language(self, user_id: int, detected_input_language: str | None = None) -> str:
        preferred = self.store.get_user_prefs(user_id)["language"]
        if preferred != "english":
            return preferred
        if detected_input_language and detected_input_language != "english":
            return detected_input_language
        return "english"

    def prepare_multilingual_input(self, user_id: int, text: str) -> tuple[str, str | None, str]:
        clean = normalize_text(text)
        if not clean:
            return clean, None, self.get_reply_language(user_id)
        preferred = self.store.get_user_prefs(user_id)["language"]
        detected = self.detect_input_language(clean)
        if (not detected or detected == "english") and preferred != "english":
            detected = preferred if not detected else detected
        reply_language = self.get_reply_language(user_id, detected)
        working_text = clean
        if detected and detected != "english":
            translated = self.translate_text(clean, "english", detected)
            if translated:
                working_text = translated
        return working_text, detected, reply_language

    def maybe_translate_for_user(self, user_id: int, text: str, reply_language: str | None = None) -> str:
        language = reply_language or self.store.get_user_prefs(user_id)["language"]
        if language == "english":
            return text
        translated = self.translate_text(text, language)
        if translated:
            return translated
        return text + f"\n\nTranslation note: I could not translate that to {language.title()} right now."

    def get_ddg_answer(self, query: str) -> dict | None:
        try:
            response = requests.get(
                DDG_API_URL,
                params={"q": query, "format": "json", "no_html": "1", "skip_disambig": "1", "t": "SpringBot"},
                timeout=8,
            )
            response.raise_for_status()
            data = response.json()
            answer = data.get("Answer", "").strip()
            abstract = data.get("AbstractText", "").strip()
            url = data.get("AbstractURL", "").strip()
            source = data.get("AbstractSource", "").strip()
            definition = data.get("Definition", "").strip()
            definition_url = data.get("DefinitionURL", "").strip()
            related = []
            for item in data.get("RelatedTopics", [])[:4]:
                text = item.get("Text", "").strip()
                link = item.get("FirstURL", "").strip()
                if text and link:
                    related.append({"text": shorten(text, 120), "url": link})
            if not answer and not abstract and not definition:
                return None
            return {
                "answer": answer,
                "abstract": abstract or definition,
                "url": url or definition_url,
                "source": source or ("Dictionary" if definition else ""),
                "related": related,
                "image": data.get("Image", "").strip(),
            }
        except Exception:
            return None

    def _decode_ddg_href(self, href: str) -> str:
        if href.startswith("//"):
            return "https:" + href
        if "duckduckgo.com/l/?" in href:
            parsed = urlparse(href)
            query = parse_qs(parsed.query)
            uddg = query.get("uddg", [""])[0]
            if uddg:
                return unquote(uddg)
        return html.unescape(href)

    def search_web_results(self, query: str, limit: int = 3) -> list[dict]:
        try:
            response = requests.post(
                DDG_HTML_URL,
                data={"q": query},
                headers={"User-Agent": "SpringBot/2.0"},
                timeout=10,
            )
            response.raise_for_status()
            body = response.text
            anchors = list(
                re.finditer(
                    r'<a[^>]+class="result__a"[^>]+href="(?P<href>[^"]+)"[^>]*>(?P<title>.*?)</a>',
                    body,
                    re.S,
                )
            )
            snippets = [
                html.unescape(re.sub(r"<.*?>", "", match.group("text"))).strip()
                for match in re.finditer(r'<a[^>]+class="result__snippet"[^>]*>(?P<text>.*?)</a>', body, re.S)
            ]
            if not snippets:
                snippets = [
                    html.unescape(re.sub(r"<.*?>", "", match.group("text"))).strip()
                    for match in re.finditer(r'<div[^>]+class="result__snippet"[^>]*>(?P<text>.*?)</div>', body, re.S)
                ]
            results = []
            for index, match in enumerate(anchors[:limit]):
                title = html.unescape(re.sub(r"<.*?>", "", match.group("title"))).strip()
                href = self._decode_ddg_href(match.group("href"))
                snippet = snippets[index] if index < len(snippets) else ""
                if title and href.startswith("http"):
                    results.append({"title": title, "url": href, "snippet": shorten(snippet, 180)})
            return results
        except Exception:
            return []

    def get_wikipedia_summary(self, query: str) -> str | None:
        try:
            search = requests.get(
                WIKI_SEARCH_URL,
                params={"action": "opensearch", "search": query, "limit": 1, "namespace": 0, "format": "json"},
                timeout=10,
            )
            search.raise_for_status()
            data = search.json()
            if not data or len(data) < 2 or not data[1]:
                return None
            title = data[1][0]
            extract = requests.get(
                WIKI_SEARCH_URL,
                params={"action": "query", "prop": "extracts", "exintro": True, "explaintext": True, "titles": title, "format": "json"},
                timeout=10,
            )
            extract.raise_for_status()
            pages = extract.json().get("query", {}).get("pages", {})
            if not pages:
                return None
            page = next(iter(pages.values()))
            text = page.get("extract", "").strip()
            if not text:
                return f"I found {title}, but there was no clean summary available."
            return f"{title} - {clean_summary(text)}"
        except Exception:
            return None

    def get_weather_snapshot(self, location: str) -> dict | None:
        place = normalize_text(location)
        if not place:
            return None
        try:
            response = requests.get(
                f"{WTTR_LOOKUP_URL}/{quote_plus(place)}",
                params={"format": "j1"},
                headers={"User-Agent": "SpringBot/2.0"},
                timeout=10,
            )
            response.raise_for_status()
            payload = response.json()
            current = (payload.get("current_condition") or [{}])[0]
            nearest = (payload.get("nearest_area") or [{}])[0]
            area = ((nearest.get("areaName") or [{}])[0]).get("value", "")
            region = ((nearest.get("region") or [{}])[0]).get("value", "")
            country = ((nearest.get("country") or [{}])[0]).get("value", "")
            weather_desc = ((current.get("weatherDesc") or [{}])[0]).get("value", "Unknown")
            parts = [value for value in (area, region, country) if value]
            return {
                "place": ", ".join(parts) or place,
                "condition": weather_desc,
                "temp_f": current.get("temp_F", "?"),
                "temp_c": current.get("temp_C", "?"),
                "feels_f": current.get("FeelsLikeF", "?"),
                "humidity": current.get("humidity", "?"),
                "wind_mph": current.get("windspeedMiles", "?"),
            }
        except Exception:
            return None

    def get_news_headlines(self, limit: int = 5) -> list[dict]:
        try:
            response = requests.get(
                NEWS_RSS_URL,
                headers={"User-Agent": "SpringBot/2.0"},
                timeout=10,
            )
            response.raise_for_status()
            root = ET.fromstring(response.text)
            items: list[dict] = []
            for item in root.findall(".//item")[:limit]:
                title = normalize_text(item.findtext("title", "No title"))
                link = normalize_text(item.findtext("link", ""))
                pub_date = normalize_text(item.findtext("pubDate", "Unknown"))
                if title:
                    items.append({"title": title, "link": link, "pub_date": pub_date})
            return items
        except Exception:
            return []

    def _load_glossary(self) -> str:
        if not self._glossary_text and self.store.paths["glossary_flat"].exists():
            self._glossary_text = self.store.paths["glossary_flat"].read_text(encoding="utf-8", errors="replace")
        return self._glossary_text

    def search_glossary(self, query: str) -> str | None:
        text = self._load_glossary()
        if not text:
            return None
        q = normalize_text(query).lower()
        words = q.split()
        candidates = [" ".join(words[:n]) for n in range(min(6, len(words)), 0, -1)]
        text_lower = text.lower()

        def extract(start: int) -> str:
            snippet = text[start : start + 550].strip()
            result = ""
            for sentence in re.split(r"(?<=[.!?])\s+", snippet):
                if len(result) + len(sentence) > 380:
                    break
                result += sentence + " "
            result = result.strip()
            return result if len(result) >= 20 else snippet[:380].strip()

        for phrase in candidates:
            entry_re = r"(?:\.\s+)" + re.escape(phrase) + r"(?:\s+\([^)]+\))?\s+[A-Z]"
            match = re.search(entry_re, text_lower)
            if match:
                return extract(match.start() + 2)
            if text_lower.startswith(phrase):
                return extract(0)
            any_re = r"(?<![A-Za-z0-9])" + re.escape(phrase) + r"(?![A-Za-z0-9])"
            match = re.search(any_re, text_lower)
            if match:
                index = match.start()
                look_back = text_lower.rfind(". ", max(0, index - 600), index)
                start = (look_back + 2) if look_back != -1 else max(0, index - 30)
                return extract(start)
        return None

    def extract_keywords(self, text: str, limit: int = 5) -> list[str]:
        words = re.findall(r"[A-Za-z][A-Za-z0-9+/#.-]{2,}", text.lower())
        counts = Counter(word for word in words if word not in STOPWORDS)
        return [word for word, _ in counts.most_common(limit)]

    def summarize_text_block(self, text: str, max_sentences: int = 3) -> str:
        sentences = split_sentences(text)
        if not sentences:
            return "I need more text before I can summarize it."
        if len(sentences) <= max_sentences:
            return " ".join(sentences)
        freq = Counter(
            word
            for word in re.findall(r"[A-Za-z][A-Za-z0-9'-]{2,}", text.lower())
            if word not in STOPWORDS
        )
        if not freq:
            return " ".join(sentences[:max_sentences])
        scored = []
        for index, sentence in enumerate(sentences):
            words = re.findall(r"[A-Za-z][A-Za-z0-9'-]{2,}", sentence.lower())
            score = sum(freq[word] for word in words if word in freq)
            scored.append((score, index, sentence))
        best = sorted(scored, key=lambda item: item[0], reverse=True)[:max_sentences]
        ordered = [sentence for _, _, sentence in sorted(best, key=lambda item: item[1])]
        return " ".join(ordered)

    def fetch_dictionary_entry(self, word: str) -> dict | None:
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
            for block in entry.get("meanings", []):
                part_of_speech = block.get("partOfSpeech", "") or part_of_speech
                definitions = block.get("definitions", [])
                if definitions:
                    meaning = definitions[0].get("definition", "")
                    example = definitions[0].get("example", "")
                    break
            if not meaning:
                return None
            return {
                "word": entry.get("word", token),
                "phonetic": entry.get("phonetic", ""),
                "part_of_speech": part_of_speech,
                "meaning": meaning,
                "example": example,
                "origin": entry.get("origin", ""),
            }
        except Exception:
            return None

    def fetch_trivia(self) -> dict | None:
        try:
            response = requests.get(TRIVIA_API, params={"amount": 1, "type": "multiple"}, timeout=6)
            response.raise_for_status()
            results = response.json().get("results", [])
            if not results:
                return None
            item = results[0]
            correct = html.unescape(item["correct_answer"])
            incorrect = [html.unescape(value) for value in item["incorrect_answers"]]
            options = incorrect + [correct]
            random.shuffle(options)
            return {
                "question": html.unescape(item["question"]),
                "options": options,
                "answer": correct,
                "category": html.unescape(item.get("category", "")),
                "difficulty": item.get("difficulty", ""),
            }
        except Exception:
            return None

    def fetch_meme(self) -> dict | None:
        posts = self._search_reddit_posts(REDDIT_MEME_SUBREDDITS, "")
        for post in posts:
            media = self._extract_reddit_media(post, prefer_gif=False)
            if not media:
                continue
            return {
                "title": post.get("title", ""),
                "url": media["url"],
                "ups": post.get("ups", 0),
                "link": f"https://reddit.com{post.get('permalink', '')}",
                "subreddit": post.get("subreddit", ""),
            }
        try:
            response = requests.get(REDDIT_MEME, headers={"User-Agent": REDDIT_USER_AGENT}, timeout=6)
            response.raise_for_status()
            data = response.json()
            post = data[0]["data"]["children"][0]["data"]
            media = self._extract_reddit_media(post, prefer_gif=False)
            if not media:
                return None
            return {
                "title": post.get("title", ""),
                "url": media["url"],
                "ups": post.get("ups", 0),
                "link": f"https://reddit.com{post.get('permalink', '')}",
                "subreddit": post.get("subreddit", ""),
            }
        except Exception:
            return None

    def _clean_reddit_url(self, url: str) -> str:
        clean = html.unescape((url or "").strip())
        if clean.endswith(".gifv"):
            clean = clean[:-5] + ".gif"
        return clean

    def _url_media_kind(self, url: str) -> str:
        if not url:
            return ""
        parsed = urlparse(url)
        fmt = parse_qs(parsed.query).get("format", [""])[0].lower()
        if fmt:
            return fmt
        suffix = Path(parsed.path).suffix.lower().lstrip(".")
        return suffix

    def _is_image_like_url(self, url: str) -> bool:
        kind = self._url_media_kind(url)
        return kind in {"jpg", "jpeg", "png", "webp", "gif"}

    def _is_gif_like_url(self, url: str) -> bool:
        return self._url_media_kind(url) == "gif"

    def _reddit_post_candidates(self, post: dict) -> list[str]:
        candidates: list[str] = []
        preview = post.get("preview") or {}
        images = preview.get("images") or []
        if images:
            first = images[0]
            gif_variant = ((first.get("variants") or {}).get("gif") or {}).get("source", {}).get("url")
            if gif_variant:
                candidates.append(gif_variant)
            source = (first.get("source") or {}).get("url")
            if source:
                candidates.append(source)
        for key in ("url_overridden_by_dest", "url"):
            value = post.get(key)
            if value:
                candidates.append(value)
        cleaned: list[str] = []
        seen: set[str] = set()
        for item in candidates:
            url = self._clean_reddit_url(item)
            if url and url not in seen:
                seen.add(url)
                cleaned.append(url)
        return cleaned

    def _extract_reddit_media(self, post: dict, prefer_gif: bool) -> dict | None:
        candidates = self._reddit_post_candidates(post)
        if prefer_gif:
            for url in candidates:
                if self._is_gif_like_url(url):
                    return {"url": url, "kind": "gif"}
        for url in candidates:
            if self._is_image_like_url(url):
                return {"url": url, "kind": "image"}
        return None

    def _parse_reddit_listing(self, payload: Any) -> list[dict]:
        if isinstance(payload, list) and payload:
            payload = payload[0]
        if not isinstance(payload, dict):
            return []
        data = payload.get("data", {})
        children = data.get("children", [])
        posts = []
        for child in children:
            post = child.get("data", {}) if isinstance(child, dict) else {}
            if not post:
                continue
            if post.get("over_18") or post.get("stickied") or post.get("is_self"):
                continue
            posts.append(post)
        return posts

    def _search_reddit_posts(self, subreddits: tuple[str, ...], query: str, limit: int = 12) -> list[dict]:
        collected: list[dict] = []
        headers = {"User-Agent": REDDIT_USER_AGENT}
        clean_query = normalize_text(query)
        for subreddit in subreddits:
            if clean_query:
                url = f"https://www.reddit.com/r/{subreddit}/search.json"
                params = {"q": clean_query, "restrict_sr": "on", "sort": "relevance", "t": "all", "limit": str(limit)}
            else:
                url = f"https://www.reddit.com/r/{subreddit}/hot.json"
                params = {"limit": str(limit)}
            try:
                response = requests.get(url, headers=headers, params=params, timeout=8)
                response.raise_for_status()
                collected.extend(self._parse_reddit_listing(response.json()))
            except Exception:
                continue
        random.shuffle(collected)
        return collected

    def fetch_gif(self, term: str = "") -> dict | None:
        posts = self._search_reddit_posts(REDDIT_GIF_SUBREDDITS, term)
        if not posts and term:
            posts = self._search_reddit_posts(REDDIT_GIF_SUBREDDITS, "")
        for post in posts:
            media = self._extract_reddit_media(post, prefer_gif=True)
            if not media:
                continue
            return {
                "title": post.get("title", "") or (normalize_text(term) or "GIF"),
                "url": media["url"],
                "item_url": f"https://reddit.com{post.get('permalink', '')}",
                "subreddit": post.get("subreddit", ""),
            }
        return None

    def is_current_query(self, question: str) -> bool:
        hints = {
            "current", "latest", "today", "now", "recent",
            "updated", "update", "live", "happening",
        }
        if brain_supports_live_tool("news"):
            hints.update({"news", "headline", "headlines"})
        if brain_supports_live_tool("weather"):
            hints.update({"weather", "forecast", "temperature"})
        if brain_supports_live_tool("web_search") or brain_supports_live_tool("tech_sources"):
            hints.update({"price", "score"})
        lowered = question.lower()
        return any(hint in lowered for hint in hints)

    def build_live_context(self, query: str) -> tuple[str | None, list[dict]]:
        lines = []
        results: list[dict] = []
        ddg = None
        if any(brain_supports_live_tool(tool) for tool in {"web_search", "news", "weather", "tech_sources"}):
            ddg = self.get_ddg_answer(query)
        if brain_supports_live_tool("web_search") or brain_supports_live_tool("tech_sources"):
            results = self.search_web_results(query, limit=3)
        if ddg:
            if ddg["answer"]:
                lines.append(ddg["answer"])
            elif ddg["abstract"]:
                source = f" Source: {ddg['source']}" if ddg["source"] else ""
                lines.append(clean_summary(ddg["abstract"], 420) + source)
        if results:
            lines.append("Web results:")
            for item in results:
                lines.append(f"- {item['title']}: {item['url']}")
                if item["snippet"]:
                    lines.append(f"  {item['snippet']}")
        if not lines and brain_supports_live_tool("wikipedia"):
            wiki = self.get_wikipedia_summary(query)
            if wiki:
                lines.append(wiki)
        if not lines:
            return None, results
        return "\n".join(lines), results

    def search_knowledge_pack(self, question: str) -> tuple[str | None, str | None]:
        lowered = normalize_text(question).lower()
        brain_subjects = [subject for subject in BOT_BRAIN["core_knowledge"] if subject in SPRING_KNOWLEDGE_PACK]
        subjects_to_scan = brain_subjects or list(SPRING_KNOWLEDGE_PACK.keys())
        for subject in subjects_to_scan:
            entries = SPRING_KNOWLEDGE_PACK[subject]
            for key, value in entries.items():
                variants = {
                    key,
                    key.replace("_", " "),
                    key.replace("_plus", "+").replace("_", " "),
                }
                if any(variant and variant in lowered for variant in variants):
                    return value, subject
        for subject in subjects_to_scan:
            if subject in lowered:
                first_key = next(iter(SPRING_KNOWLEDGE_PACK[subject]), None)
                if first_key:
                    return SPRING_KNOWLEDGE_PACK[subject][first_key], subject
        return None, None

    def broad_knowledge_answer(self, question: str) -> str:
        lowered = question.lower().strip()
        for service, port in COMMON_PORTS.items():
            if service in lowered and ("port" in lowered or "ports" in lowered):
                return f"{service.upper()} uses port {port}."
        packed, _ = self.search_knowledge_pack(question)
        if packed:
            return packed
        for key, value in TECH_KB.items():
            if key in lowered:
                return value
        for key, value in GENERAL_KB.items():
            if key in lowered:
                return value
        if "difference between tcp and udp" in lowered:
            return "TCP is reliable and connection-oriented. UDP is faster and connectionless."
        if "difference between router and switch" in lowered:
            return "A router connects different networks. A switch connects devices inside the same local network."
        if "what is comptia" in lowered:
            return "CompTIA is a vendor-neutral certification organization known for A+, Network+, and Security+."
        if "best cert" in lowered or "which certification" in lowered:
            return "For entry-level IT, A+ is usually the safest start. For networking, Network+. For security foundations, Security+."
        glossary = self.search_glossary(question)
        if glossary:
            return "From the IT glossary:\n" + glossary
        ddg = self.get_ddg_answer(question)
        if ddg:
            if ddg["answer"]:
                return ddg["answer"]
            if ddg["abstract"]:
                result = clean_summary(ddg["abstract"], 400)
                if ddg["url"]:
                    result += f" ({ddg['url']})"
                return result
        wiki = self.get_wikipedia_summary(question)
        if wiki:
            return wiki
        return "I don't have a solid answer for that yet. Try !search for a live web lookup."

    def knowledge_snapshot(self, topic: str, limit: int = 420) -> str:
        return shorten(strip_formatting(self.broad_knowledge_answer(topic)), limit)

    def looks_like_fact_question(self, prompt: str) -> bool:
        lowered = prompt.lower().strip()
        starters = (
            "what ", "who ", "when ", "where ", "why ", "how ",
            "is ", "are ", "can ", "do ", "does ",
            "define ", "explain ", "compare ", "difference between ",
        )
        phrases = {
            "difference between",
            "what is",
            "how do",
            "how does",
            "why is",
            "why do",
            "what does",
            "port",
            "certification",
        }
        if lowered.startswith(("should i", "could i", "do you think")):
            return False
        return prompt.endswith("?") or lowered.startswith(starters) or any(phrase in lowered for phrase in phrases)

    def _extract_memory_fact(self, prompt: str) -> str | None:
        patterns = [
            r"^remember that\s+(.+)$",
            r"^remember\s+(.+)$",
            r"^note that\s+(.+)$",
            r"^save this\s+(.+)$",
        ]
        for pattern in patterns:
            match = re.match(pattern, prompt, flags=re.IGNORECASE)
            if match:
                fact = normalize_text(match.group(1))
                if fact:
                    return fact
        return None

    def _looks_like_plan_request(self, prompt: str) -> bool:
        lowered = prompt.lower()
        triggers = {
            "help me plan",
            "make a plan",
            "build a plan",
            "give me a plan",
            "organize this",
            "organise this",
            "break this down",
            "how should i approach",
            "what should i do first",
            "how do i start",
        }
        return lowered.startswith("plan ") or any(trigger in lowered for trigger in triggers)

    def _extract_plan_goal(self, prompt: str) -> str:
        clean = normalize_text(prompt)
        clean = re.sub(r"^(help me\s+)?(make|build|give)\s+(me\s+)?a\s+plan\s+(for\s+)?", "", clean, flags=re.IGNORECASE)
        clean = re.sub(r"^(help me\s+)?plan\s+", "", clean, flags=re.IGNORECASE)
        clean = re.sub(r"^(organize|organise)\s+(this|myself|me)?\s*", "", clean, flags=re.IGNORECASE)
        clean = re.sub(r"^(break this down|how should i approach|what should i do first)\s*", "", clean, flags=re.IGNORECASE)
        return normalize_text(clean) or normalize_text(prompt)

    def _recent_user_topic(self, history: list[dict], current_prompt: str = "") -> str:
        current = normalize_text(current_prompt).lower()
        for entry in reversed(history):
            if entry.get("role") != "user":
                continue
            text = normalize_text(entry.get("text", ""))
            lowered = text.lower()
            if not text or lowered == current:
                continue
            if any(phrase in lowered for phrase in {"proud of you", "thank you", "thanks", "good job"}):
                continue
            if len(text.split()) < 2:
                continue
            return text
        return ""

    def _is_short_affirmation(self, prompt: str) -> bool:
        lowered = normalize_text(prompt).lower()
        phrases = {
            "yeah", "yep", "yup", "true", "facts", "for real", "exactly",
            "indeed", "same", "right", "real talk", "that part", "we are",
            "indeed we are", "for sure", "absolutely",
        }
        return lowered in phrases

    def _looks_like_casual_message(self, prompt: str) -> bool:
        lowered = normalize_text(prompt).lower()
        if not lowered or self.looks_like_fact_question(prompt) or looks_like_math_problem(prompt):
            return False
        if len(lowered.split()) > 14:
            return False
        if any(token in lowered for token in {"http://", "https://", "=", "!todo", "!note", "!plan"}):
            return False
        starters = (
            "i ", "i'm ", "im ", "we ", "we're ", "were ", "my ", "this ",
            "that ", "just ", "man", "bro", "honestly", "lowkey",
        )
        return lowered.startswith(starters) or self._is_short_affirmation(lowered)

    def _build_follow_up_question(self, prompt: str, history: list[dict]) -> str:
        lowered = normalize_text(prompt).lower()
        recent = self._recent_user_topic(history, prompt)
        if any(word in lowered for word in {"server", "role", "channel", "discord", "bot", "springbot"}):
            return "What part do you want to change first?"
        if "overthinking" in lowered:
            return "What is the actual decision or problem you keep circling?"
        if any(word in lowered for word in {"stress", "overwhelmed", "frustrated", "tired", "hard", "stuck", "confused"}):
            return "What part is hitting you the hardest?"
        if any(word in lowered for word in {"chat", "talk", "conversation"}):
            return "What's been on your mind today?"
        if "tweak" in lowered or "fix" in lowered or "improve" in lowered:
            return "What feels most off right now: my tone, my common sense, or the back-and-forth?"
        if recent:
            return f"Do you want to keep going on `{shorten(recent, 70)}` or switch gears?"
        return "What do you want to get into?"

    def build_common_sense_reply(self, prompt: str, history: list[dict]) -> str | None:
        lowered = normalize_text(prompt).lower()
        short = shorten(prompt, 140)
        if lowered.startswith(("should i", "could i", "do you think")):
            return (
                f"My honest common-sense take on `{short}`: go with the option that keeps things clearer, simpler, and easier to undo if it goes sideways. "
                "If you want, tell me the two options and I will help you choose."
            )
        relation_words = {"friend", "girl", "guy", "boyfriend", "girlfriend", "mom", "dad", "brother", "sister", "family", "coworker", "boss"}
        social_words = {"said", "did", "texted", "ignored", "mad", "upset", "annoyed", "argued", "drama", "relationship"}
        if any(word in lowered for word in relation_words) and any(word in lowered for word in social_words):
            return (
                "Common-sense read: do not jump to the worst conclusion off one moment. Ask directly, stay calm, and judge the pattern instead of one text or one bad interaction. "
                "What happened?"
            )
        if lowered.startswith(("i feel like", "i feel ", "i think ", "i guess ", "maybe ")):
            return f"That sounds real. {self._build_follow_up_question(prompt, history)}"
        return None

    def build_conversational_reply(self, user_id: int, prompt: str, history: list[dict]) -> str | None:
        lowered = normalize_text(prompt).lower()
        if any(phrase in lowered for phrase in {"just a regular conversation", "just talk", "normal conversation", "just chatting"}):
            return "Yeah, we can do that. We do not have to turn every message into a task. What's been on your mind?"
        if any(phrase in lowered for phrase in {"we still got to tweak you", "we still gotta tweak you", "still got to tweak you", "still gotta tweak you"}):
            return "Fair. I'm getting better, but I am not all the way there yet. What feels most off right now: my tone, my common sense, or how I keep the conversation going?"
        if any(phrase in lowered for phrase in {"you feel more real", "you sound more real", "you sound human", "you feel human"}):
            return "Good. That is the direction I want. Keep telling me where I still sound off and I will keep tightening it up."
        common_sense = self.build_common_sense_reply(prompt, history)
        if common_sense:
            return common_sense
        if self._is_short_affirmation(prompt):
            recent = self._recent_user_topic(history, prompt)
            if recent:
                return f"Yeah, for real. We have been building around `{shorten(recent, 80)}`. {self._build_follow_up_question(prompt, history)}"
            return "Yeah. I'm with you. What do you want to talk about?"
        if self._looks_like_casual_message(prompt):
            if lowered.startswith(("i'm ", "im ", "i am ", "i feel ", "i think ", "i just ")):
                return f"I hear you. {self._build_follow_up_question(prompt, history)}"
            if lowered.startswith(("we ", "we're ", "were ")):
                return f"Yeah, I get what you mean. {self._build_follow_up_question(prompt, history)}"
            if lowered.startswith(("this ", "that ")):
                return f"Yeah, that makes sense. {self._build_follow_up_question(prompt, history)}"
            if len(lowered.split()) <= 6:
                return f"Alright. {self._build_follow_up_question(prompt, history)}"
        return None

    def _format_assistant_list(self, items: list[dict], done_label: str = "done") -> str:
        lines = []
        for index, item in enumerate(items, start=1):
            status = done_label if item.get("done") else "open"
            prefix = "[x]" if item.get("done") else "[ ]"
            lines.append(f"{index}. {prefix} {item['text']} ({status})")
        return "\n".join(lines)

    def build_brain_memory_snapshot(self, user_id: int) -> list[str]:
        prefs = self.store.get_user_prefs(user_id)
        history = self.store.get_chat_history(user_id)
        user_turns = [entry["text"] for entry in history if entry.get("role") == "user"]
        recent_topic = shorten(user_turns[-1], 80) if user_turns else "Nothing saved yet."
        last_question = next((shorten(text, 80) for text in reversed(user_turns) if "?" in text), recent_topic)
        tone = "casual" if prefs["mode"] in {"assistant", "chat", "friend"} else "focused"
        lines = []
        if "recent_topic" in BOT_BRAIN["memory"]:
            lines.append(f"Recent topic memory: {recent_topic}")
        if "user_preferred_style" in BOT_BRAIN["memory"]:
            lines.append(f"Preferred style memory: {prefs['mode']}")
        if "last_question" in BOT_BRAIN["memory"]:
            lines.append(f"Last question memory: {last_question}")
        if "conversation_tone" in BOT_BRAIN["memory"]:
            lines.append(f"Conversation tone memory: {tone}")
        return lines

    def build_assistant_briefing(self, user_id: int, include_examples: bool = False) -> str:
        prefs = self.store.get_user_prefs(user_id)
        tasks = self.store.get_assistant_tasks(user_id)
        notes = self.store.get_assistant_notes(user_id)
        open_tasks = [task for task in tasks if not task.get("done")]
        done_tasks = [task for task in tasks if task.get("done")]
        lines = [
            f"{SPRING_PERSONALITY['name']} briefing.",
            personality_role_summary(),
            f"Mode: {prefs['mode']}",
            f"Mode style: {personality_mode_summary(prefs['mode'])}",
            f"Language: {prefs['language']}",
            f"Open tasks: {len(open_tasks)}",
            f"Saved notes: {len(notes)}",
            f"Completed tasks: {len(done_tasks)}",
        ]
        if BOT_BRAIN["core_knowledge"]:
            subjects = ", ".join(subject.replace("_", " ").title() for subject in BOT_BRAIN["core_knowledge"])
            lines.append(f"Core knowledge: {subjects}")
        if BOT_BRAIN["explanation_modes"]:
            modes = ", ".join(mode.replace("_", " ") for mode in BOT_BRAIN["explanation_modes"])
            lines.append(f"Explanation modes: {modes}")
        if BOT_BRAIN["live_tools"]:
            lines.append(f"Live tools: {', '.join(BOT_BRAIN['live_tools'])}")
        lines.extend(self.build_brain_memory_snapshot(user_id))
        if open_tasks:
            lines.append("Top tasks:")
            lines.extend(f"- {task['text']}" for task in open_tasks[:3])
        if notes:
            lines.append("Latest notes:")
            lines.extend(f"- {note['text']}" for note in notes[-2:])
        if include_examples:
            lines.extend(
                [
                    "Try:",
                    "- !assistant help me plan my server setup",
                    "- !assistant play some calming jazz music",
                    "- !mode friend",
                    "- !mode exam_prep",
                    "- !todo add finish the welcome channel",
                    "- !note add My staff role should stay above Member",
                    "- !chat remind me what to work on next",
                ]
            )
        return self.maybe_translate_for_user(user_id, shorten("\n".join(lines), 1700))

    def build_assistant_greeting(self, user_id: int) -> str:
        tasks = self.store.get_assistant_tasks(user_id)
        notes = self.store.get_assistant_notes(user_id)
        open_tasks = [task for task in tasks if not task.get("done")]
        if open_tasks or notes:
            return self.maybe_translate_for_user(
                user_id,
                f"I'm here. You have {len(open_tasks)} open task(s) and {len(notes)} saved note(s). "
                "Want to talk something through, make a plan, or have me handle server work?",
            )
        return self.maybe_translate_for_user(
            user_id,
            "I'm here. Want to talk, make a plan, save a note, or have me handle a server task?",
        )

    def build_task_overview(self, user_id: int) -> str:
        tasks = self.store.get_assistant_tasks(user_id)
        if not tasks:
            return self.maybe_translate_for_user(user_id, "You do not have any saved tasks yet. Try `!todo add finish the rules channel`.")
        open_tasks = [task for task in tasks if not task.get("done")]
        done_tasks = [task for task in tasks if task.get("done")]
        lines = [f"Task list: {len(open_tasks)} open, {len(done_tasks)} done."]
        if open_tasks:
            lines.append("Open:")
            lines.extend(f"{index}. [ ] {task['text']}" for index, task in enumerate(tasks, start=1) if not task.get("done"))
        if done_tasks:
            lines.append("Done:")
            lines.extend(f"{index}. [x] {task['text']}" for index, task in enumerate(tasks, start=1) if task.get("done"))
        return self.maybe_translate_for_user(user_id, shorten("\n".join(lines), 1700))

    def build_note_overview(self, user_id: int) -> str:
        notes = self.store.get_assistant_notes(user_id)
        if not notes:
            return self.maybe_translate_for_user(user_id, "You do not have any saved notes yet. Try `!note add keep SpringBot above the Member role`.")
        lines = ["Saved notes:"]
        lines.extend(f"{index}. {note['text']}" for index, note in enumerate(notes, start=1))
        return self.maybe_translate_for_user(user_id, shorten("\n".join(lines), 1700))

    def build_plan(self, goal: str, user_id: int) -> str:
        clean_goal = normalize_text(goal)
        if not clean_goal:
            return "Tell me what you want a plan for."
        keywords = self.extract_keywords(clean_goal, 4)
        focus_a = keywords[0].replace("-", " ").title() if keywords else "Setup"
        focus_b = keywords[1].replace("-", " ").title() if len(keywords) > 1 else "Execution"
        focus_c = keywords[2].replace("-", " ").title() if len(keywords) > 2 else "Review"
        lines = [
            f"Plan for: {clean_goal}",
            "1. Lock the target. Define what a finished result looks like in one sentence.",
            f"2. Split the work into three passes: {focus_a}, {focus_b}, and {focus_c}.",
            "3. Handle the first visible step in the next 10 minutes so momentum starts immediately.",
            "4. Check blockers early: permissions, tools, missing information, and deadlines.",
            "5. Review the result once, then clean up the rough edges.",
            f"Next move: start with the part most tied to `{focus_a.lower()}`.",
            "If you want, I can turn this into trackable tasks with `!todo add ...`.",
        ]
        return self.maybe_translate_for_user(user_id, shorten("\n".join(lines), 1700))

    def detect_subject_area(self, topic: str) -> str:
        lowered = normalize_text(topic).lower()
        subject_keywords = {
            "history": {"history", "empire", "war", "civilization", "leader", "timeline", "ancient", "revolution"},
            "math": {"math", "algebra", "geometry", "probability", "equation", "ratio", "percent", "statistics"},
            "science": {"science", "biology", "chemistry", "physics", "astronomy", "ecosystem", "energy", "matter"},
            "technology": {"technology", "computer", "software", "hardware", "programming", "database", "cloud", "operating system"},
            "it": {"it ", "help desk", "printer", "ticket", "troubleshooting", "windows", "support", "networking basics"},
            "cybersecurity": {"cyber", "security", "phishing", "malware", "firewall", "encryption", "siem", "incident response"},
            "tech_certifications": {"comptia", "cert", "certification", "a+", "network+", "security+", "study path"},
            "fun_facts": {"fun fact", "random fact", "weird fact", "trivia"},
        }
        for subject, keywords in subject_keywords.items():
            if any(keyword in lowered for keyword in keywords):
                return subject
        if brain_knows_subject("technology") and any(token in lowered for token in {"discord", "bot", "server", "role", "channel"}):
            return "technology"
        return "general"

    def build_subject_example(self, subject: str, topic: str) -> str:
        clean_topic = normalize_text(topic)
        examples = {
            "history": f"Think of {clean_topic} like a timeline where one event pushes the next one.",
            "math": f"Think of {clean_topic} like a recipe: use the formula, plug in the numbers, then simplify.",
            "science": f"Think of {clean_topic} as a rule for how the natural world behaves in real life.",
            "technology": f"Think of {clean_topic} like a system where each part has a job and they have to work together.",
            "it": f"In IT terms, treat {clean_topic} like a ticket: symptom first, cause second, fix third.",
            "cybersecurity": f"For {clean_topic}, think attacker vs defender: how something gets exploited and how you stop it.",
            "tech_certifications": f"Think of {clean_topic} like a job map that shows what skills employers expect.",
            "fun_facts": f"The fun part about {clean_topic} is that one surprising detail usually makes the whole thing stick.",
        }
        return examples.get(subject, f"A real-world way to think about {clean_topic} is to tie it to a problem someone actually has to solve.")

    def build_subject_focus_line(self, subject: str) -> str:
        config = SPRING_BOT_SYSTEM["subjects"].get(subject)
        if not config:
            return ""
        methods = config.get("how_to_explain", [])
        if not methods:
            return ""
        return f"Best angle: {methods[0]}."

    def build_social_response(self, user_id: int, prompt: str, history: list[dict]) -> str | None:
        lowered = prompt.lower()
        clean = normalize_text(prompt)
        if any(phrase in lowered for phrase in {"thank you", "thanks", "thx", "appreciate you"}):
            return random.choice(THANKS_REPLIES)
        if any(phrase in lowered for phrase in {"im proud of you", "i'm proud of you", "good job", "you did good", "you did great", "you did it"}):
            return random.choice(PRAISE_REPLIES)
        if any(phrase in lowered for phrase in {"i just want to chat", "talk to me", "lets talk", "let's talk", "keep me company"}):
            return random.choice(CHAT_REPLIES)
        if any(phrase in lowered for phrase in {"good morning", "good afternoon", "good evening"}):
            return "Good to see you. What are we getting into today?"
        if any(phrase in lowered for phrase in {"good night", "night", "gn"}):
            return "Rest up. I’ll be here when you need me again."
        if any(phrase in lowered for phrase in {"i'm stressed", "im stressed", "i'm overwhelmed", "im overwhelmed", "i'm frustrated", "im frustrated", "this is hard", "this sucks", "i'm tired", "im tired"}):
            return random.choice(SUPPORT_REPLIES)
        if any(phrase in lowered for phrase in {"what should i do next", "what do i do next", "what next"}):
            tasks = [task for task in self.store.get_assistant_tasks(user_id) if not task.get("done")]
            if tasks:
                return f"Start with this: {tasks[0]['text']}. If you want, I can help you break it into smaller steps."
            return "Right now I’d pick one clear target and start small. If you want, give me the goal and I’ll turn it into a plan."
        if history and any(phrase in lowered for phrase in {"same thing", "same topic", "pick up where we left off"}):
            recent = [entry["text"] for entry in history if entry.get("role") == "user"]
            if recent:
                return f"Yeah, we can pick it back up. Last thing you were focused on was `{shorten(recent[-1], 90)}`."
        if lowered in {"yo", "sup", "whats up", "what's up", "wassup"}:
            return "Not much. I’m here and ready. What do you need?"
        if re.fullmatch(r"(hi|hello|hey|yo)( there)?", lowered):
            return random.choice(
                [
                    "Hey. I’m here.",
                    "Hey, what’s up?",
                    "Hi. What do you need?",
                    "Hey, talk to me.",
                ]
            )
        return None

    def build_assistant_response(self, user_id: int, prompt: str, history: list[dict]) -> str | None:
        lowered = prompt.lower()
        clean = normalize_text(prompt)
        social = self.build_social_response(user_id, prompt, history)
        if social:
            return social
        if any(phrase in lowered for phrase in {"how are you", "how you doing", "how's it going"}):
            return "I’m doing pretty good. I’m here, awake, and ready to help with whatever you’ve got."
        if any(phrase in lowered for phrase in {"who are you", "what are you"}):
            return "I’m SpringBot. Think of me like your Discord assistant and second brain. I can help you talk through ideas, manage the server, solve problems, remember things, and keep work organized."
        if lowered in {"help", "help me"} or lowered.startswith(("what can you do", "what do you do", "how can you help")):
            return self.build_assistant_briefing(user_id, include_examples=True)
        if any(phrase in lowered for phrase in {"what do you remember about me", "what have you saved", "what are my notes"}):
            notes = self.store.get_assistant_notes(user_id)
            tasks = self.store.get_assistant_tasks(user_id)
            open_tasks = [task["text"] for task in tasks if not task.get("done")]
            lines = [
                f"I remember {len(notes)} saved note(s) and {len(open_tasks)} open task(s) for you.",
            ]
            if notes:
                lines.append("Recent notes:")
                lines.extend(f"- {note['text']}" for note in notes[-3:])
            if open_tasks:
                lines.append("Open tasks:")
                lines.extend(f"- {task}" for task in open_tasks[:3])
            if not notes and not open_tasks:
                lines.append("Nothing saved yet. Use `!note add ...` or `!todo add ...` and I will keep track of it.")
            return "\n".join(lines)
        remembered = self._extract_memory_fact(clean)
        if remembered:
            self.store.add_assistant_note(user_id, remembered)
            return f"Got it. I saved this note: {remembered}"
        if any(phrase in lowered for phrase in {"what's on my list", "whats on my list", "my todo", "to-do list", "todo list", "my tasks"}):
            return self.build_task_overview(user_id)
        if any(phrase in lowered for phrase in {"my notes", "show my notes"}):
            return self.build_note_overview(user_id)
        if self._looks_like_plan_request(clean):
            return self.build_plan(self._extract_plan_goal(clean), user_id)
        if "remind me to" in lowered:
            task = normalize_text(re.sub(r"^.*?remind me to\s+", "", clean, flags=re.IGNORECASE))
            if task:
                return (
                    f"I can help with that. Save it with `!todo add {task}` if you want it on your list, "
                    f"or use `!remind 30m {task}` when you want a timed reminder."
                )
        if history and any(word in lowered for word in {"continue", "pick up", "follow up", "same"}):
            recent = [entry["text"] for entry in history if entry.get("role") == "user"]
            if recent:
                return f"Sure. We can keep going from `{shorten(recent[-1], 90)}`. Tell me if you want the next step, a cleaner plan, or just to talk it through."
        return None

    def build_social_response(self, user_id: int, prompt: str, history: list[dict]) -> str | None:
        lowered = prompt.lower()
        if any(phrase in lowered for phrase in {"thank you", "thanks", "thx", "appreciate you"}):
            return random.choice(THANKS_REPLIES)
        if any(phrase in lowered for phrase in {"im proud of you", "i'm proud of you", "good job", "you did good", "you did great", "you did it"}):
            return random.choice(PRAISE_REPLIES)
        if any(phrase in lowered for phrase in {"i just want to chat", "talk to me", "lets talk", "let's talk", "keep me company"}):
            return random.choice(CHAT_REPLIES)
        if any(phrase in lowered for phrase in {"good morning", "good afternoon", "good evening"}):
            return "Good to see you. What are we getting into today?"
        if re.search(r"\b(good night|gn)\b", lowered) or lowered.strip() == "night":
            return "Rest up. I'll be here when you need me again."
        if any(phrase in lowered for phrase in {"i'm stressed", "im stressed", "i'm overwhelmed", "im overwhelmed", "i'm frustrated", "im frustrated", "this is hard", "this sucks", "i'm tired", "im tired"}):
            return random.choice(SUPPORT_REPLIES)
        if any(phrase in lowered for phrase in {"what should i do next", "what do i do next", "what next"}):
            tasks = [task for task in self.store.get_assistant_tasks(user_id) if not task.get("done")]
            if tasks:
                return f"Start with this: {tasks[0]['text']}. If you want, I can help you break it into smaller steps."
            return "Right now I'd pick one clear target and start small. If you want, give me the goal and I'll turn it into a plan."
        if history and any(phrase in lowered for phrase in {"same thing", "same topic", "pick up where we left off"}):
            recent = [entry["text"] for entry in history if entry.get("role") == "user"]
            if recent:
                return f"Yeah, we can pick it back up. Last thing you were focused on was `{shorten(recent[-1], 90)}`."
        if lowered in {"yo", "sup", "whats up", "what's up", "wassup"}:
            return "Not much. I'm here and ready. What do you need?"
        if re.fullmatch(r"(hi|hello|hey|yo)( there)?", lowered):
            return random.choice(
                [
                    "Hey. I'm here.",
                    "Hey, what's up?",
                    "Hi. What do you need?",
                    "Hey, talk to me.",
                ]
            )
        return None

    def build_assistant_response(self, user_id: int, prompt: str, history: list[dict]) -> str | None:
        lowered = prompt.lower()
        clean = normalize_text(prompt)
        social = self.build_social_response(user_id, prompt, history)
        if social:
            return social
        conversational = self.build_conversational_reply(user_id, prompt, history)
        if conversational:
            return conversational
        if any(phrase in lowered for phrase in {"how are you", "how you doing", "how's it going"}):
            return "I'm good. Locked in, a little sarcastic when the moment calls for it, and ready to help. What's up?"
        if any(phrase in lowered for phrase in {"who are you", "what are you"}):
            return (
                f"I'm {SPRING_PERSONALITY['name']}. {personality_role_summary()} "
                "Think of me like a smart second brain for your server: I can talk things through, explain stuff clearly, manage server work, remember notes, and help you move faster without sounding robotic."
            )
        if lowered in {"help", "help me"} or lowered.startswith(("what can you do", "what do you do", "how can you help")):
            return self.build_assistant_briefing(user_id, include_examples=True)
        if any(phrase in lowered for phrase in {"what do you remember about me", "what have you saved", "what are my notes"}):
            notes = self.store.get_assistant_notes(user_id)
            tasks = self.store.get_assistant_tasks(user_id)
            open_tasks = [task["text"] for task in tasks if not task.get("done")]
            lines = [f"I remember {len(notes)} saved note(s) and {len(open_tasks)} open task(s) for you."]
            if notes:
                lines.append("Recent notes:")
                lines.extend(f"- {note['text']}" for note in notes[-3:])
            if open_tasks:
                lines.append("Open tasks:")
                lines.extend(f"- {task}" for task in open_tasks[:3])
            if not notes and not open_tasks:
                lines.append("Nothing saved yet. Use `!note add ...` or `!todo add ...` and I will keep track of it.")
            return "\n".join(lines)
        remembered = self._extract_memory_fact(clean)
        if remembered:
            self.store.add_assistant_note(user_id, remembered)
            return f"Got it. I saved that: {remembered}"
        if any(phrase in lowered for phrase in {"what's on my list", "whats on my list", "my todo", "to-do list", "todo list", "my tasks"}):
            return self.build_task_overview(user_id)
        if any(phrase in lowered for phrase in {"my notes", "show my notes"}):
            return self.build_note_overview(user_id)
        if self._looks_like_plan_request(clean):
            return self.build_plan(self._extract_plan_goal(clean), user_id)
        if "remind me to" in lowered:
            task = normalize_text(re.sub(r"^.*?remind me to\s+", "", clean, flags=re.IGNORECASE))
            if task:
                return (
                    f"Yeah, I can help with that. Save it with `!todo add {task}` if you want it on your list, "
                    f"or use `!remind 30m {task}` when you want a timed reminder."
                )
        if history and any(word in lowered for word in {"continue", "pick up", "follow up", "same"}):
            recent = [entry["text"] for entry in history if entry.get("role") == "user"]
            if recent:
                return f"Yeah, we can pick it back up from `{shorten(recent[-1], 90)}`. Tell me if you want the next step, a cleaner plan, or just to talk it through."
        return None

    def apply_mode_style(self, text: str, mode: str, subject: str = "") -> str:
        clean = text.strip()
        mode_key = normalize_mode_name(mode)
        if len(clean) > 1700:
            clean = clean[:1697].rstrip() + "..."
        if clean.startswith("From the IT glossary:"):
            clean = clean.replace("From the IT glossary:", "Quick answer:", 1)
        if mode_key == "brief":
            return shorten(" ".join(split_sentences(clean)[:1]) or clean, 500)
        include_intro = not has_chill_intro(clean)
        if mode_key in {"technical", "tech"} and include_intro:
            return style_response(clean, mode_key, include_intro=True)
        if mode_key == "step_by_step" and include_intro:
            return style_response(clean, mode_key, include_intro=True)
        if mode_key == "study" and include_intro:
            return style_response(clean, mode_key, include_intro=True)
        if mode_key == "friend" and include_intro and not subject:
            return style_response(clean, mode_key, include_intro=True)
        if mode_key == "simple" and include_intro:
            return style_response(clean, mode_key, include_intro=True)
        if mode_key in {"technical", "tech"}:
            return "Technical breakdown:\n" + clean
        if mode_key == "step_by_step":
            lines = [normalize_text(line) for line in clean.splitlines() if normalize_text(line)]
            if not lines:
                lines = split_sentences(clean)
            if not lines:
                return clean
            steps = [f"{index}. {line}" for index, line in enumerate(lines[:6], start=1)]
            return "Let's break it down:\n" + "\n".join(steps)
        if mode_key == "study":
            focus = self.build_subject_focus_line(subject) or "Best angle: know what it is, why it matters, and one example you can remember."
            return f"Study mode:\n{clean}\n{focus}\nMemory trick: tie the idea to one real example so it sticks."
        if mode_key == "simple":
            sentences = split_sentences(clean)
            simple = " ".join(sentences[:2]) if sentences else clean
            return f"Simple version:\n{simple}"
        if mode_key == "friend":
            topic_hint = clean.splitlines()[0] if clean.splitlines() else clean
            topic_hint = re.sub(r"^(Topic|Problem|Study guide):\s*", "", topic_hint, flags=re.IGNORECASE)
            example = self.build_subject_example(subject, topic_hint) if subject else ""
            extra = f"\nExample: {example}" if example else ""
            if include_intro:
                return style_response(f"{clean}{extra}", mode_key, include_intro=True)
            return f"{clean}{extra}"
        if mode_key == "real_world":
            topic_hint = clean.splitlines()[0] if clean.splitlines() else clean
            topic_hint = re.sub(r"^(Topic|Problem|Study guide):\s*", "", topic_hint, flags=re.IGNORECASE)
            example = self.build_subject_example(subject, topic_hint)
            return f"Real-world version:\n{clean}\nExample: {example}"
        if mode_key == "exam_prep":
            focus = self.build_subject_focus_line(subject) or "Best angle: focus on the definition, one example, and one likely test trap."
            return f"Exam prep:\n{clean}\n{focus}\nWhat to remember: know the meaning, why it matters, and how it gets tested."
        if mode_key == "chat":
            return clean
        if mode_key == "lore":
            return "Archive entry:\n" + clean
        if mode_key == "assistant":
            return clean
        return clean

    def build_fallback_chat_response(self, prompt: str) -> str:
        short = shorten(prompt, 140)
        lowered = prompt.lower()
        if lowered.startswith(("i want", "i need", "i'm trying", "im trying", "i have to")):
            return (
                f"Alright. Let’s make `{short}` feel smaller. Start with the exact outcome you want, then handle the first step you can finish without overthinking it. "
                "If you want, I can turn it into a plan or a task list."
            )
        if lowered.startswith(("should i", "do you think")):
            return (
                f"My honest take on `{short}`: choose the option that lowers confusion and gives you the most control. "
                "If you want, give me both options and I’ll compare them properly."
            )
        return (
            f"Alright. For `{short}`, I’d start by getting clear on the goal, then I’d handle the biggest blocker first. "
            "If you want, I can help you plan it, explain it, or turn it into tasks."
        )

    def build_fallback_chat_response(self, prompt: str) -> str:
        short = shorten(prompt, 140)
        lowered = prompt.lower()
        if lowered.startswith(("i want", "i need", "i'm trying", "im trying", "i have to")):
            return (
                f"Alright. Let's make `{short}` feel smaller. Start with the exact outcome you want, then handle the first step you can finish without overthinking it. "
                "If you want, I can turn it into a plan or a task list."
            )
        if lowered.startswith(("do you think you can", "can you")):
            return (
                f"Yeah, probably. For `{short}`, give me the exact thing you want handled and I'll either do it or tell you the cleanest way to get it done."
            )
        if lowered.startswith(("should i", "do you think")):
            return (
                f"My honest take on `{short}`: go with the option that gives you the clearest outcome and the fewest headaches. "
                "If you're choosing between two things, send them both and I'll compare them properly."
            )
        if self._looks_like_casual_message(prompt):
            return f"Yeah, I get you. {self._build_follow_up_question(prompt, [])}"
        return (
            f"Alright. For `{short}`, I'd get clear on the goal first, then handle the biggest blocker before it wastes more time. "
            "If you want, I can help you plan it, explain it, or turn it into tasks."
        )

    def build_smart_reply(self, user_id: int, prompt: str, use_memory: bool = True, forced_mode: str | None = None) -> str:
        original_prompt = normalize_text(prompt)
        if not original_prompt:
            return "Say the word. I am listening."
        prompt, detected_language, reply_language = self.prepare_multilingual_input(user_id, original_prompt)
        mode = forced_mode or self.store.get_user_prefs(user_id)["mode"]
        history = self.store.get_chat_history(user_id) if use_memory else []
        lowered = prompt.lower()
        assistant = self.build_assistant_response(user_id, prompt, history)
        if assistant:
            base = assistant
        elif re.fullmatch(r"[0-9\s+\-*/().%]+", prompt):
            result = safe_eval(prompt)
            if result != "Invalid expression":
                base = f"Step 1: Read the expression `{prompt}`.\nStep 2: Apply order of operations carefully.\nAnswer: {result}"
            else:
                base = self.build_fallback_chat_response(prompt)
        elif lowered.startswith(("hi", "hello", "hey")) and len(prompt.split()) <= 5:
            base = "I am here. Ask me a question, give me a task, or tell me what you want organized."
        else:
            if self.looks_like_fact_question(prompt) or self.is_current_query(prompt):
                live_context, _ = self.build_live_context(prompt) if self.is_current_query(prompt) else (None, [])
                base = live_context or self.broad_knowledge_answer(prompt)
                if "I don't have a solid answer for that yet" in base:
                    extra_live, _ = self.build_live_context(prompt)
                    base = extra_live or self.build_fallback_chat_response(prompt)
            else:
                base = self.build_fallback_chat_response(prompt)
        if use_memory and history and any(word in lowered for word in {"it", "that", "same", "again", "continue"}):
            recent = [entry["text"] for entry in history if entry.get("role") == "user"]
            if recent:
                base = f"Picking up from your earlier topic, `{shorten(recent[-1], 80)}`.\n{base}"
        styled = self.apply_mode_style(base, mode)
        if use_memory:
            self.store.remember_chat_turn(user_id, "user", original_prompt)
            self.store.remember_chat_turn(user_id, "assistant", self.maybe_translate_for_user(user_id, styled, reply_language))
        return self.maybe_translate_for_user(user_id, styled, reply_language)

    def build_explanation(self, topic: str, user_id: int) -> str:
        topic, _, reply_language = self.prepare_multilingual_input(user_id, topic)
        mode = self.store.get_user_prefs(user_id)["mode"]
        subject = self.detect_subject_area(topic)
        answer = self.knowledge_snapshot(topic, 700)
        keywords = self.extract_keywords(answer, 4)
        lines = []
        if mode in {"assistant", "chat", "friend", "simple"}:
            lines.append(chill_intro())
        lines.append(explain_topic(normalize_text(topic), answer, mode))
        if subject != "general" and mode not in {"simple", "friend"}:
            lines.append(f"Subject area: {subject.replace('_', ' ').title()}")
            focus = self.build_subject_focus_line(subject)
            if focus and mode != "exam_prep":
                lines.append(focus)
        if keywords:
            lines.append("Key ideas: " + ", ".join(keywords))
        if SPRING_BOT_SYSTEM["behavior"]["give_examples"] and mode not in {"friend", "real_world", "simple", "step_by_step", "study", "exam_prep"}:
            lines.append("Example: " + self.build_subject_example(subject, topic))
        response = "\n".join(lines)
        if mode in {"real_world", "lore", "brief", "assistant", "chat", "technical", "study", "step_by_step"}:
            response = self.apply_mode_style(response, mode, subject)
        return self.maybe_translate_for_user(user_id, response, reply_language)

    def build_definition(self, word: str, user_id: int) -> str:
        word, _, reply_language = self.prepare_multilingual_input(user_id, word)
        mode = self.store.get_user_prefs(user_id)["mode"]
        subject = self.detect_subject_area(word)
        entry = self.fetch_dictionary_entry(word)
        if entry:
            lines = [entry["word"].title()]
            if mode in {"assistant", "chat", "friend", "simple"}:
                lines.insert(0, chill_intro())
            if entry["phonetic"]:
                lines.append(f"Pronunciation: {entry['phonetic']}")
            if entry["part_of_speech"]:
                lines.append(f"Part of speech: {entry['part_of_speech']}")
            lines.append(f"Meaning: {entry['meaning']}")
            if entry["origin"]:
                lines.append(f"Etymology: {entry['origin']}")
            if entry["example"]:
                lines.append(f"Example: {entry['example']}")
            styled = self.apply_mode_style("\n".join(lines), mode, subject)
            return self.maybe_translate_for_user(user_id, styled, reply_language)
        answer = self.knowledge_snapshot(word, 500)
        text = f"Definition: {answer}"
        if mode in {"assistant", "chat", "friend", "simple"}:
            text = f"{chill_intro()}\n{text}"
        styled = self.apply_mode_style(text, mode, subject)
        return self.maybe_translate_for_user(user_id, styled, reply_language)

    def build_comparison(self, topic_a: str, topic_b: str, user_id: int) -> str:
        topic_a, _, reply_language = self.prepare_multilingual_input(user_id, topic_a)
        topic_b, _, reply_language_b = self.prepare_multilingual_input(user_id, topic_b)
        reply_language = reply_language if reply_language != "english" else reply_language_b
        mode = self.store.get_user_prefs(user_id)["mode"]
        subject = self.detect_subject_area(f"{topic_a} {topic_b}")
        left = self.knowledge_snapshot(topic_a, 280)
        right = self.knowledge_snapshot(topic_b, 280)
        lines = []
        if mode in {"assistant", "chat", "friend", "simple"}:
            lines.append(chill_intro())
        lines.extend(
            [
            f"{topic_a.strip()} vs {topic_b.strip()}",
            f"{topic_a.strip()}: {left}",
            f"{topic_b.strip()}: {right}",
            "Quick take: choose based on the job, the tradeoffs, and the level of control you need.",
            ]
        )
        if SPRING_BOT_SYSTEM["behavior"]["give_examples"]:
            lines.append("Real-world way to think about it: pick the one that fits the situation, not just the label.")
        styled = self.apply_mode_style("\n".join(lines), mode, subject)
        return self.maybe_translate_for_user(user_id, styled, reply_language)

    def build_rewrite(self, style: str, text: str, user_id: int) -> str:
        style_key = normalize_text(style).lower()
        clean = normalize_text(text)
        if not clean:
            return "Give me text to rewrite."
        if style_key not in {"professional", "casual", "persuasive", "formal", "simple"}:
            return "Styles: professional, casual, persuasive, formal, simple."
        sentences = split_sentences(clean)
        first = sentences[0] if sentences else clean
        if style_key == "professional":
            result = f"{first} Please review the details and proceed accordingly."
        elif style_key == "casual":
            result = f"{first} That's the easy version."
        elif style_key == "persuasive":
            result = f"{first} This is the strongest path because it is practical, clear, and worth acting on now."
        elif style_key == "formal":
            result = f"Please be advised: {clean}"
        else:
            result = shorten(" ".join(split_sentences(clean)[:2]) or clean, 500)
            result = f"Simple version: {result}"
        return self.maybe_translate_for_user(user_id, shorten(result, 900))

    def build_flashcards(self, topic: str, user_id: int) -> str:
        summary = self.knowledge_snapshot(topic, 650)
        keywords = self.extract_keywords(summary, 5)
        cards = [
            f"1. Q: What is {normalize_text(topic)}?\nA: {summary}",
            f"2. Q: Why does {normalize_text(topic)} matter?\nA: It matters because it affects how systems, people, or processes work in practice.",
            f"3. Q: What is one core detail about {normalize_text(topic)}?\nA: {split_sentences(summary)[0] if split_sentences(summary) else summary}",
        ]
        for index, keyword in enumerate(keywords[:2], start=4):
            cards.append(f"{index}. Q: What should you remember about {keyword}?\nA: It is a key term tied to {normalize_text(topic)}.")
        while len(cards) < 5:
            number = len(cards) + 1
            cards.append(f"{number}. Q: Give one study tip for {normalize_text(topic)}.\nA: Review the concept, one example, and one common mistake.")
        return self.maybe_translate_for_user(user_id, "\n\n".join(cards[:5]))

    def build_studyguide(self, topic: str, user_id: int) -> str:
        topic, _, reply_language = self.prepare_multilingual_input(user_id, topic)
        mode = self.store.get_user_prefs(user_id)["mode"]
        subject = self.detect_subject_area(topic)
        summary = self.knowledge_snapshot(topic, 700)
        keywords = self.extract_keywords(summary, 5)
        lines = [
            f"Study guide: {normalize_text(topic)}",
            f"Overview: {summary}",
            "Key points:",
        ]
        if keywords:
            lines.extend([f"- {word.title()}: know what it means and why it matters." for word in keywords])
        else:
            lines.append("- Break the topic into definition, function, example, and troubleshooting.")
        lines.extend(
            [
                "Review steps:",
                "- Learn the definition in plain English.",
                "- Match the topic to one real-world example.",
                "- Compare it against a similar concept.",
                "- Test yourself with one recall question and one scenario question.",
            ]
        )
        focus = self.build_subject_focus_line(subject)
        if focus:
            lines.append(focus)
        styled = self.apply_mode_style(shorten("\n".join(lines), 1700), mode, subject)
        return self.maybe_translate_for_user(user_id, styled, reply_language)

    def build_fun_fact(self, topic: str, user_id: int) -> str:
        topic, _, reply_language = self.prepare_multilingual_input(user_id, topic)
        key = normalize_text(topic).lower()
        pack_fact = SPRING_KNOWLEDGE_PACK["fun_facts"].get(key.replace(" ", "_")) if key else None
        if pack_fact:
            result = pack_fact
        elif key and key in FUN_FACTS:
            result = FUN_FACTS[key]
        elif key:
            result = self.knowledge_snapshot(topic, 320)
        else:
            facts = list(FUN_FACTS.values()) + list(SPRING_KNOWLEDGE_PACK["fun_facts"].values())
            result = random.choice(facts)
        return self.maybe_translate_for_user(user_id, f"Fun fact: {result}", reply_language)

    def build_solver(self, problem: str, user_id: int) -> str:
        problem, _, reply_language = self.prepare_multilingual_input(user_id, problem)
        mode = self.store.get_user_prefs(user_id)["mode"]
        subject = "math"
        clean = normalize_text(problem)
        if re.fullmatch(r"[0-9\s+\-*/().%]+", clean):
            result = safe_eval(clean)
            lines = [
                f"Problem: {clean}",
                "Step 1: Identify the operations in the expression.",
                "Step 2: Apply parentheses and exponents first, then multiply/divide, then add/subtract.",
                f"Answer: {result}",
            ]
            styled = self.apply_mode_style("\n".join(lines), mode, subject)
            return self.maybe_translate_for_user(user_id, styled, reply_language)
        if looks_like_math_problem(clean):
            symbolic = self._build_symbolic_solver_response(clean)
            if symbolic:
                styled = self.apply_mode_style(symbolic, mode, subject)
                return self.maybe_translate_for_user(user_id, styled, reply_language)
            if not self.sympy_available():
                note = (
                    "I can do advanced algebra and calculus once `sympy` is installed. "
                    "Right now I can only do arithmetic and general guidance."
                )
                styled = self.apply_mode_style(note, mode, subject)
                return self.maybe_translate_for_user(user_id, styled, reply_language)
        answer = self.knowledge_snapshot(clean, 620)
        lines = [
            f"Problem: {clean}",
            "Step 1: Identify what the question is actually asking.",
            "Step 2: Pull out the important facts or formulas.",
            "Step 3: Work through the logic in order.",
            f"Best explanation I can give: {answer}",
        ]
        styled = self.apply_mode_style("\n".join(lines), mode, subject)
        return self.maybe_translate_for_user(user_id, styled, reply_language)

    def build_language_list(self) -> str:
        names = ", ".join(language.title() for language in SUPPORTED_LANGUAGES)
        return shorten(f"Supported languages: {names}", 1700)


def strip_bot_mention(content: str, bot_user_id: int) -> str:
    patterns = [
        rf"<@!?{bot_user_id}>",
    ]
    cleaned = content
    for pattern in patterns:
        cleaned = re.sub(pattern, "", cleaned)
    return normalize_text(cleaned)


def serialize_perm_value(value: bool | None) -> str:
    if value is None:
        return "none"
    return "true" if value else "false"


def deserialize_perm_value(value: Any) -> bool | None:
    if value == "none" or value is None:
        return None
    if isinstance(value, bool):
        return value
    return str(value).lower() == "true"


def admin_only():
    async def predicate(ctx: commands.Context) -> bool:
        if not ctx.guild or not isinstance(ctx.author, discord.Member):
            raise commands.NoPrivateMessage()
        perms = ctx.author.guild_permissions
        if any(
            [
                perms.administrator,
                perms.manage_guild,
                perms.manage_channels,
                perms.manage_roles,
                perms.kick_members,
                perms.ban_members,
                perms.moderate_members,
            ]
        ):
            return True
        if {role.name for role in ctx.author.roles} & ADMIN_ROLE_NAMES:
            return True
        raise commands.MissingPermissions(["administrator"])

    return commands.check(predicate)


def build_command_guide_embed(bot: commands.Bot) -> discord.Embed:
    embed = discord.Embed(
        title="SpringBot Command Guide",
        description="Prefix: `!` | Use `!help <command>` for details | `!helpme` for the quick menu | Mention me to talk naturally",
        color=discord.Color.blurple(),
    )
    embed.add_field(
        name="Moderation",
        value="`!ban !kick !timeout !untimeout !warn !warnings !clearwarnings !purge !move !disconnect !lock !unlock !slowmode !announce !nick`",
        inline=False,
    )
    embed.add_field(
        name="Music",
        value="`!join !play !pause !resume !skip !queue !voicecheck !leave`",
        inline=False,
    )
    embed.add_field(
        name="Economy / Levels",
        value="`!balance !daily !work !pay !richest !rank !leaderboard`",
        inline=False,
    )
    embed.add_field(
        name="Fun",
        value="`!8ball !coinflip !dice !rps !trivia !choose !meme !gif !joke !poll !roast`",
        inline=False,
    )
    embed.add_field(
        name="AI + Learning",
        value="`!about !assistant !plan !chat !ask !learn !mode !style !resetchat !solve !explain !define !compare !summarize !rewrite !flashcard !studyguide !funfact !tech !todo !note`",
        inline=False,
    )
    embed.add_field(
        name="Live Info",
        value="`!search !news !weather`",
        inline=False,
    )
    embed.add_field(
        name="Languages",
        value="`!translate !tr !lang !languages`",
        inline=False,
    )
    embed.add_field(
        name="Utility / Server",
        value="`!avatar !userinfo !serverinfo !calc !remind !afk !settings !togglechat !toggleantilink !toggleantispam !ticketpanel !closeticket !reactionrole !serveraudit !setupserver !serverpreset !renamerole !giverole !removerole !rolecolor !roleprops !createvoice !renamevoice !voicecap !voicebitrate !voicecategory !voiceposition !voiceperm !deletevoice !renametext !movetext !clonechannel !channelposition !channeltopic !rolelock !roleunlock !filter !addcmd !delcmd !listcmds !giveaway !greroll`",
        inline=False,
    )
    embed.set_footer(text=f"{bot.user.name if bot.user else 'SpringBot'} | Intelligent. Fast. A little sarcastic.")
    return embed


class MusicManager:
    def __init__(self, bot: commands.Bot, store: DataStore, state: RuntimeState):
        self.bot = bot
        self.store = store
        self.state = state
        self.ffmpeg_path = self._find_ffmpeg()

    def _find_ffmpeg(self) -> str | None:
        candidates = [
            ROOT_DIR.parent / "ffmpeg" / "bin" / "ffmpeg.exe",
            ROOT_DIR / "ffmpeg" / "bin" / "ffmpeg.exe",
        ]
        for path in candidates:
            if path.exists():
                return str(path)
        return shutil.which("ffmpeg")

    def _yt_dlp_options(self) -> dict[str, Any]:
        options: dict[str, Any] = {
            "format": "bestaudio[acodec=opus]/bestaudio/best",
            "noplaylist": True,
            "quiet": True,
            "no_warnings": True,
            "default_search": "ytsearch",
            "source_address": "0.0.0.0",
            "socket_timeout": 20,
            "extract_flat": False,
        }
        cookie_file = self.store.paths["cookies"]
        if cookie_file.exists():
            options["cookiefile"] = str(cookie_file)
        return options

    async def _clear_self_deaf(self, guild: discord.Guild, channel: discord.abc.Snowflake):
        with contextlib.suppress(discord.HTTPException, discord.ClientException, AttributeError):
            await guild.change_voice_state(channel=channel, self_mute=False, self_deaf=False)
            append_voice_debug(f"ensure_voice update: cleared self deaf in channel={getattr(channel, 'id', None)}")

    async def ensure_voice(self, ctx: commands.Context) -> discord.VoiceClient:
        append_voice_debug(f"ensure_voice start guild={getattr(ctx.guild, 'id', None)} user={getattr(ctx.author, 'id', None)}")
        if not ctx.guild or not isinstance(ctx.author, discord.Member):
            append_voice_debug("ensure_voice failed: no guild context")
            raise commands.NoPrivateMessage()
        if not discord.voice_client.has_nacl:
            append_voice_debug("ensure_voice failed: PyNaCl not loaded in process")
            raise commands.CommandError(
                "Voice support did not initialize in this bot process because `PyNaCl` is missing. Close every SpringBot window and start it again with start_springbot.cmd."
            )
        if not getattr(discord.voice_client, "has_dave", False):
            append_voice_debug("ensure_voice failed: davey not loaded in process")
            raise commands.CommandError(
                "Voice support did not initialize in this bot process because `davey` is missing. Close every SpringBot window and start it again with start_springbot.cmd."
            )
        if not isinstance(ctx.author, discord.Member) or not ctx.author.voice or not ctx.author.voice.channel:
            append_voice_debug("ensure_voice failed: author not in voice channel")
            raise commands.CommandError("Join a voice channel first.")
        destination = ctx.author.voice.channel
        me = ctx.guild.me
        if not me:
            append_voice_debug("ensure_voice failed: guild.me unavailable")
            raise commands.CommandError("I could not resolve my server member state.")
        perms = destination.permissions_for(me)
        missing = []
        if not perms.view_channel:
            missing.append("View Channel")
        if not perms.connect:
            missing.append("Connect")
        if not perms.speak:
            missing.append("Speak")
        if missing:
            append_voice_debug(f"ensure_voice failed: missing permissions {missing} in channel={destination.id}")
            raise commands.CommandError(f"I need `{', '.join(missing)}` permission in **{destination.name}**.")
        if destination.user_limit and len(destination.members) >= destination.user_limit and not (ctx.guild.voice_client and ctx.guild.voice_client.channel == destination):
            append_voice_debug(f"ensure_voice failed: channel full channel={destination.id}")
            raise commands.CommandError(f"**{destination.name}** is full right now.")
        voice_client = ctx.guild.voice_client if ctx.guild else None
        if voice_client:
            if not voice_client.is_connected():
                with contextlib.suppress(discord.HTTPException, discord.ClientException):
                    await voice_client.disconnect(force=True)
                    append_voice_debug("ensure_voice cleanup: disconnected stale voice client")
            elif voice_client.channel != destination:
                try:
                    await voice_client.move_to(destination)
                    await self._clear_self_deaf(ctx.guild, destination)
                    append_voice_debug(f"ensure_voice moved existing client to channel={destination.id}")
                    return voice_client
                except discord.Forbidden as exc:
                    append_voice_debug(f"ensure_voice move forbidden: {exc}")
                    raise commands.CommandError(f"Discord blocked the move into **{destination.name}**: {exc}") from exc
                except asyncio.TimeoutError as exc:
                    append_voice_debug(f"ensure_voice move timeout: {exc}")
                    raise commands.CommandError(f"Moving into **{destination.name}** timed out. Try again in a moment.") from exc
                except discord.ClientException as exc:
                    append_voice_debug(f"ensure_voice move client exception: {exc}")
                    with contextlib.suppress(discord.HTTPException, discord.ClientException):
                        await voice_client.disconnect(force=True)
                else:
                    return voice_client
            else:
                await self._clear_self_deaf(ctx.guild, destination)
                append_voice_debug(f"ensure_voice success: already connected channel={destination.id}")
                return voice_client
        try:
            vc = await destination.connect(timeout=20.0, reconnect=True, self_deaf=False)
            await self._clear_self_deaf(ctx.guild, destination)
            append_voice_debug(f"ensure_voice success: connected to channel={destination.id}")
            return vc
        except discord.Forbidden as exc:
            append_voice_debug(f"ensure_voice connect forbidden: {exc}")
            raise commands.CommandError(f"Discord denied the voice join for **{destination.name}**: {exc}") from exc
        except asyncio.TimeoutError as exc:
            append_voice_debug(f"ensure_voice connect timeout: {exc}")
            raise commands.CommandError(f"Voice join to **{destination.name}** timed out. Check permissions and try again.") from exc
        except discord.ClientException as exc:
            append_voice_debug(f"ensure_voice connect client exception: {exc}")
            raise commands.CommandError(f"I could not connect to **{destination.name}**: {exc}") from exc

    async def extract_track(self, query: str, requester: discord.abc.User, channel_id: int) -> dict | None:
        loop = asyncio.get_running_loop()

        def _extract():
            with yt_dlp.YoutubeDL(self._yt_dlp_options()) as ydl:
                info = ydl.extract_info(query, download=False)
                if info and "entries" in info:
                    info = next((entry for entry in info["entries"] if entry), None)
                if not info:
                    return None
                stream_url = info.get("url")
                if not stream_url:
                    formats = info.get("formats") or []
                    best = next((item for item in reversed(formats) if item.get("url")), None)
                    if best:
                        stream_url = best.get("url")
                if not stream_url:
                    return None
                return {
                    "title": info.get("title") or "Unknown track",
                    "web_url": info.get("webpage_url") or query,
                    "duration": info.get("duration") or 0,
                    "stream_url": stream_url,
                    "uploader": info.get("uploader") or info.get("channel") or "Unknown",
                    "thumbnail": info.get("thumbnail"),
                    "requester_id": requester.id,
                    "requester_name": getattr(requester, "display_name", requester.name),
                    "request_channel_id": channel_id,
                    "http_headers": info.get("http_headers") or {},
                }

        return await loop.run_in_executor(None, _extract)

    def _create_audio_source(self, track: dict) -> discord.AudioSource:
        if not self.ffmpeg_path:
            raise RuntimeError("FFmpeg was not found. Run install_ffmpeg.ps1 first.")
        before_options = "-reconnect 1 -reconnect_streamed 1 -reconnect_delay_max 5"
        headers = track.get("http_headers") or {}
        if headers:
            header_blob = "".join(f"{key}: {value}\r\n" for key, value in headers.items() if value)
            header_blob = header_blob.replace('"', '\\"')
            before_options += f' -headers "{header_blob}"'
        return discord.FFmpegOpusAudio(
            track["stream_url"],
            executable=self.ffmpeg_path,
            before_options=before_options,
            options="-vn",
        )

    async def enqueue(self, ctx: commands.Context, query: str) -> dict:
        voice_client = await self.ensure_voice(ctx)
        track = await self.extract_track(query, ctx.author, ctx.channel.id)
        if not track:
            raise commands.CommandError("I could not pull audio for that search.")
        queue = self.state.music_queues[ctx.guild.id]
        if len(queue) >= MAX_QUEUE_SIZE:
            raise commands.CommandError(f"The queue is full. Max size is {MAX_QUEUE_SIZE} tracks.")
        started_now = not voice_client.is_playing() and not voice_client.is_paused()
        track["started_now"] = started_now
        queue.append(track)
        if started_now:
            await self.play_next(ctx.guild)
        return track

    async def play_next(self, guild: discord.Guild):
        voice_client = guild.voice_client
        if not voice_client:
            return
        queue = self.state.music_queues[guild.id]
        if not queue:
            self.state.music_now_playing.pop(guild.id, None)
            return
        track = queue.popleft()
        self.state.music_now_playing[guild.id] = track
        source = self._create_audio_source(track)

        def after_play(error: Exception | None):
            asyncio.run_coroutine_threadsafe(self._after_playback(guild, error), self.bot.loop)

        voice_client.play(source, after=after_play)
        channel = guild.get_channel(track["request_channel_id"])
        if isinstance(channel, discord.abc.Messageable):
            with contextlib.suppress(discord.HTTPException):
                self.bot.loop.create_task(
                    channel.send(embed=build_track_embed(track, "Now Playing"))
                )

    async def _after_playback(self, guild: discord.Guild, error: Exception | None):
        current = self.state.music_now_playing.get(guild.id)
        if error and current:
            channel = guild.get_channel(current["request_channel_id"])
            if isinstance(channel, discord.abc.Messageable):
                with contextlib.suppress(discord.HTTPException):
                    await channel.send(f"Playback error: `{error}`")
        await self.play_next(guild)

    def describe_queue(self, guild_id: int) -> str:
        current = self.state.music_now_playing.get(guild_id)
        queue = list(self.state.music_queues[guild_id])
        lines = []
        if current:
            lines.append(f"Now playing: {current['title']} ({format_duration(current['duration'])})")
        if not queue:
            lines.append("Queue is empty.")
            return "\n".join(lines)
        for index, track in enumerate(queue[:10], start=1):
            lines.append(f"{index}. {track['title']} ({format_duration(track['duration'])}) - {track.get('uploader', 'Unknown')}")
        if len(queue) > 10:
            lines.append(f"...and {len(queue) - 10} more.")
        return "\n".join(lines)

    async def stop_and_disconnect(self, guild: discord.Guild) -> str:
        self.state.music_queues[guild.id].clear()
        self.state.music_now_playing.pop(guild.id, None)
        append_voice_debug(f"stop_and_disconnect start guild={guild.id}")
        voice_client = guild.voice_client
        if voice_client:
            try:
                voice_client.stop()
            except Exception as exc:
                append_voice_debug(f"stop_and_disconnect stop error: {exc}")
            try:
                await voice_client.disconnect(force=True)
                append_voice_debug("stop_and_disconnect success: disconnected via voice_client")
                return "Disconnected from voice."
            except Exception as exc:
                append_voice_debug(f"stop_and_disconnect disconnect error: {exc}")
        me = guild.me
        if me and me.voice and me.voice.channel:
            try:
                await guild.change_voice_state(channel=None, self_mute=False, self_deaf=False)
                append_voice_debug("stop_and_disconnect success: disconnected via guild.change_voice_state")
                return "Disconnected from voice."
            except Exception as exc:
                append_voice_debug(f"stop_and_disconnect fallback error: {exc}")
                return f"I tried to disconnect but Discord refused: {exc}"
        append_voice_debug("stop_and_disconnect complete: bot was not connected")
        return "I am not connected to a voice channel right now."

    def diagnose_voice(self, ctx: commands.Context) -> str:
        lines = [
            f"PyNaCl loaded: {discord.voice_client.has_nacl}",
            f"davey loaded: {getattr(discord.voice_client, 'has_dave', False)}",
            f"FFmpeg found: {bool(self.ffmpeg_path)}",
        ]
        if self.ffmpeg_path:
            lines.append(f"FFmpeg path: {self.ffmpeg_path}")
        if not ctx.guild or not isinstance(ctx.author, discord.Member):
            lines.append("Server context: missing")
            return "\n".join(lines)
        if not ctx.author.voice or not ctx.author.voice.channel:
            lines.append("Your voice state: not connected to a voice channel")
            return "\n".join(lines)
        channel = ctx.author.voice.channel
        lines.append(f"Your channel: {channel.name} ({channel.__class__.__name__})")
        if isinstance(channel, discord.StageChannel):
            lines.append("Channel type note: Stage channels can require extra speaking permissions.")
        me = ctx.guild.me
        if me:
            perms = channel.permissions_for(me)
            lines.append(
                "Bot permissions: "
                f"view={perms.view_channel} connect={perms.connect} speak={perms.speak} use_vad={perms.use_voice_activation}"
            )
            lines.append(f"Bot role top: {me.top_role.name}")
        else:
            lines.append("Bot guild member state: unavailable")
        if channel.user_limit:
            lines.append(f"Channel usage: {len(channel.members)}/{channel.user_limit}")
        voice_client = ctx.guild.voice_client
        if voice_client:
            lines.append(f"Current bot voice channel: {voice_client.channel.name if voice_client.channel else 'unknown'}")
            lines.append(f"Voice connected: {voice_client.is_connected()}")
        else:
            lines.append("Current bot voice channel: not connected")
        return "\n".join(lines)

    def diagnose_voice_compact(self, ctx: commands.Context) -> str:
        full = self.diagnose_voice(ctx).splitlines()
        keep = []
        for line in full:
            if line.startswith(("PyNaCl loaded:", "davey loaded:", "FFmpeg found:", "Your channel:", "Channel type note:", "Bot permissions:", "Channel usage:", "Current bot voice channel:", "Voice connected:")):
                keep.append(line)
        return "\n".join(keep[:8])


class SpringHelpCommand(commands.HelpCommand):
    async def send_bot_help(self, mapping):
        await self.get_destination().send(embed=build_command_guide_embed(self.context.bot))

    async def send_command_help(self, command: commands.Command):
        embed = discord.Embed(
            title=f"!{command.qualified_name}",
            description=command.help or "No details available for this command yet.",
            color=discord.Color.green(),
        )
        usage = f"!{command.qualified_name}"
        if command.signature:
            usage += f" {command.signature}"
        embed.add_field(name="Usage", value=f"`{usage}`", inline=False)
        if command.aliases:
            embed.add_field(name="Aliases", value=", ".join(f"`{alias}`" for alias in command.aliases), inline=False)
        if command.cog_name:
            embed.set_footer(text=command.cog_name)
        await self.get_destination().send(embed=embed)

    async def send_cog_help(self, cog: commands.Cog):
        embed = discord.Embed(title=cog.qualified_name, color=discord.Color.blurple())
        command_list = [f"`!{command.qualified_name}` - {command.help or 'No description.'}" for command in cog.get_commands()]
        embed.description = "\n".join(command_list[:20]) or "No commands."
        await self.get_destination().send(embed=embed)

    async def send_error_message(self, error: str):
        await self.get_destination().send(error)


class TicketView(discord.ui.View):
    def __init__(self, bot: "SpringBot"):
        super().__init__(timeout=None)
        self.bot = bot

    @discord.ui.button(label="Open Ticket", style=discord.ButtonStyle.green, custom_id="springbot:ticket_open")
    async def open_ticket(self, interaction: discord.Interaction, button: discord.ui.Button):
        if not interaction.guild or not interaction.user:
            await interaction.response.send_message("Tickets only work in a server.", ephemeral=True)
            return
        guild = interaction.guild
        owner_tag = f"ticket-owner:{interaction.user.id}"
        existing = next((channel for channel in guild.text_channels if channel.topic == owner_tag), None)
        if existing:
            await interaction.response.send_message(f"You already have a ticket: {existing.mention}", ephemeral=True)
            return
        config = self.bot.store.get_guild_config(guild.id)
        category = guild.get_channel(config.get("ticket_category_id") or 0)
        if not isinstance(category, discord.CategoryChannel):
            category = discord.utils.get(guild.categories, name=TICKET_CATEGORY_NAME)
        if category is None:
            category = await guild.create_category(TICKET_CATEGORY_NAME)
            self.bot.store.set_guild_config_value(guild.id, "ticket_category_id", category.id)
        overwrites = {
            guild.default_role: discord.PermissionOverwrite(read_messages=False),
            interaction.user: discord.PermissionOverwrite(read_messages=True, send_messages=True, attach_files=True),
            guild.me: discord.PermissionOverwrite(read_messages=True, send_messages=True, manage_channels=True),
        }
        for role in guild.roles:
            if role.name in ADMIN_ROLE_NAMES:
                overwrites[role] = discord.PermissionOverwrite(read_messages=True, send_messages=True, manage_channels=True)
        safe_name = re.sub(r"[^a-z0-9-]", "-", interaction.user.display_name.lower())[:18].strip("-") or str(interaction.user.id)
        channel = await guild.create_text_channel(
            name=f"ticket-{safe_name}",
            category=category,
            overwrites=overwrites,
            topic=owner_tag,
        )
        await channel.send(f"{interaction.user.mention} Ticket created. A staff member will be with you soon.")
        await interaction.response.send_message(f"Ticket opened: {channel.mention}", ephemeral=True)


class SpringBot(commands.Bot):
    def __init__(self):
        intents = discord.Intents.default()
        intents.guilds = True
        intents.members = True
        intents.messages = True
        intents.message_content = True
        intents.reactions = True
        intents.voice_states = True
        super().__init__(
            command_prefix=BOT_PREFIX,
            intents=intents,
            case_insensitive=True,
            help_command=SpringHelpCommand(),
            activity=discord.Game(name="!help | SpringBot"),
        )
        self.store = DataStore(DATA_DIR)
        self.state = RuntimeState()
        self.knowledge = KnowledgeService(self.store)
        self.music = MusicManager(self, self.store, self.state)
        self.giveaway_tasks: dict[int, asyncio.Task] = {}
        self.http_session: aiohttp.ClientSession | None = None

    async def setup_hook(self):
        if not self.http_session or self.http_session.closed:
            self.http_session = aiohttp.ClientSession(headers={"User-Agent": "SpringBot/2.0"})
        await self.add_cog(BrainCog(self))
        await self.add_cog(ModerationCog(self))
        await self.add_cog(ServerCog(self))
        await self.add_cog(MusicCog(self))
        await self.add_cog(EconomyCog(self))
        await self.add_cog(LevelCog(self))
        await self.add_cog(FunCog(self))
        await self.add_cog(UtilityCog(self))
        self.add_view(TicketView(self))
        await self.restore_giveaways()

    async def close(self):
        if self.http_session and not self.http_session.closed:
            await self.http_session.close()
        await super().close()

    async def search_tenor_gif(self, term: str) -> dict | None:
        if not TENOR_API_KEY:
            return None
        if not self.http_session or self.http_session.closed:
            self.http_session = aiohttp.ClientSession(headers={"User-Agent": "SpringBot/2.0"})
        params = {
            "q": term,
            "key": TENOR_API_KEY,
            "client_key": TENOR_CLIENT_KEY,
            "limit": 10,
            "media_filter": "gif,tinygif",
        }
        try:
            async with self.http_session.get(TENOR_SEARCH_URL, params=params, timeout=aiohttp.ClientTimeout(total=15)) as response:
                if response.status != 200:
                    return None
                data = await response.json()
        except Exception:
            return None
        results = data.get("results", [])
        if not results:
            return None
        choice = random.choice(results)
        media_formats = choice.get("media_formats", {})
        media = media_formats.get("gif") or media_formats.get("tinygif")
        if not media or not media.get("url"):
            return None
        return {
            "title": choice.get("content_description") or "GIF result",
            "url": media["url"],
            "item_url": choice.get("itemurl") or choice.get("url") or "",
        }

    def get_guild_settings(self, guild_id: int) -> dict:
        gid = str(guild_id)
        current = self.store.settings.get(gid)
        if not isinstance(current, dict):
            current = {
                "anti_link": bool(self.store.settings.get("anti_link", True)),
                "anti_spam": bool(self.store.settings.get("anti_spam", True)),
                "chat_enabled": bool(self.store.settings.get("chat_enabled", True)),
            }
        current.setdefault("anti_link", True)
        current.setdefault("anti_spam", True)
        current.setdefault("chat_enabled", True)
        self.store.settings[gid] = current
        return current

    async def log_to_mod_channel(self, guild: discord.Guild, title: str, description: str, color: discord.Color | None = None):
        config = self.store.get_guild_config(guild.id)
        channel = guild.get_channel(config.get("mod_log_channel_id") or 0)
        if not isinstance(channel, discord.TextChannel):
            channel = discord.utils.get(guild.text_channels, name=MOD_LOG_CHANNEL_NAME)
        if not channel:
            return
        embed = discord.Embed(title=title, description=description, color=color or discord.Color.orange())
        with contextlib.suppress(discord.HTTPException):
            await channel.send(embed=embed)

    async def restore_giveaways(self):
        now = time.time()
        for key, payload in list(self.store.giveaways.items()):
            try:
                message_id = int(key)
            except ValueError:
                continue
            if not isinstance(payload, dict) or payload.get("ended"):
                continue
            delay = max(0, payload.get("end_ts", now) - now)
            self.giveaway_tasks[message_id] = asyncio.create_task(self._wait_and_finish_giveaway(message_id, delay))

    async def _wait_and_finish_giveaway(self, message_id: int, delay: float):
        await asyncio.sleep(delay)
        await self.finish_giveaway(message_id)

    async def finish_giveaway(self, message_id: int):
        giveaway = self.store.giveaways.get(str(message_id))
        if not isinstance(giveaway, dict) or giveaway.get("ended"):
            return
        guild = self.get_guild(giveaway["guild_id"])
        if not guild:
            return
        channel = guild.get_channel(giveaway["channel_id"])
        if not isinstance(channel, discord.TextChannel):
            return
        with contextlib.suppress(discord.NotFound, discord.HTTPException):
            message = await channel.fetch_message(message_id)
            reaction = discord.utils.get(message.reactions, emoji="🎉")
            participants = []
            if reaction:
                async for user in reaction.users():
                    if not user.bot:
                        participants.append(user)
            winner = random.choice(participants) if participants else None
            prize = giveaway.get("prize", "Mystery prize")
            if winner:
                await channel.send(f"Giveaway ended. Winner: {winner.mention} | Prize: **{prize}**")
            else:
                await channel.send(f"Giveaway ended. No valid entries for **{prize}**.")
        giveaway["ended"] = True
        self.store.save("giveaways")
        self.giveaway_tasks.pop(message_id, None)

    async def on_ready(self):
        print(f"SpringBot online as {self.user} | guilds={len(self.guilds)} | proxies_cleared={CLEARED_PROXY_VARS}")

    async def on_member_join(self, member: discord.Member):
        config = self.store.get_guild_config(member.guild.id)
        role = member.guild.get_role(config.get("auto_role_id") or 0)
        if role:
            with contextlib.suppress(discord.HTTPException, discord.Forbidden):
                await member.add_roles(role, reason="SpringBot autorole")
        channel = member.guild.get_channel(config.get("welcome_channel_id") or 0)
        if not isinstance(channel, discord.TextChannel):
            channel = discord.utils.get(member.guild.text_channels, name=WELCOME_CHANNEL_NAME)
        if channel:
            with contextlib.suppress(discord.HTTPException):
                await channel.send(WELCOME_MESSAGE.format(mention=member.mention))

    async def on_raw_reaction_add(self, payload: discord.RawReactionActionEvent):
        if payload.user_id == self.user.id if self.user else None:
            return
        mapping = self.store.reaction_roles.get(str(payload.message_id), {})
        role_id = mapping.get(str(payload.emoji))
        if not role_id:
            return
        guild = self.get_guild(payload.guild_id)
        if not guild:
            return
        member = guild.get_member(payload.user_id)
        role = guild.get_role(role_id)
        if member and role:
            with contextlib.suppress(discord.HTTPException, discord.Forbidden):
                await member.add_roles(role, reason="SpringBot reaction role")

    async def on_raw_reaction_remove(self, payload: discord.RawReactionActionEvent):
        mapping = self.store.reaction_roles.get(str(payload.message_id), {})
        role_id = mapping.get(str(payload.emoji))
        if not role_id:
            return
        guild = self.get_guild(payload.guild_id)
        if not guild:
            return
        member = guild.get_member(payload.user_id)
        role = guild.get_role(role_id)
        if member and role:
            with contextlib.suppress(discord.HTTPException, discord.Forbidden):
                await member.remove_roles(role, reason="SpringBot reaction role")

    async def award_xp(self, message: discord.Message):
        if not message.guild:
            return
        key = (message.guild.id, message.author.id)
        now = time.time()
        last = self.state.xp_cooldowns.get(key, 0)
        if now - last < XP_COOLDOWN:
            return
        self.state.xp_cooldowns[key] = now
        record = self.store.get_xp_record(message.guild.id, message.author.id)
        record["xp"] += random.randint(XP_PER_MSG_MIN, XP_PER_MSG_MAX)
        while record["xp"] >= self.store.xp_for_level(record["level"]):
            record["xp"] -= self.store.xp_for_level(record["level"])
            record["level"] += 1
            with contextlib.suppress(discord.HTTPException):
                await message.channel.send(f"{message.author.mention} leveled up to **{record['level']}**.")
        self.store.save("xp")

    async def handle_afk(self, message: discord.Message):
        if not message.guild or not isinstance(message.author, discord.Member):
            return
        current_afk = self.store.get_afk(message.guild.id, message.author.id)
        if current_afk:
            self.store.clear_afk(message.guild.id, message.author.id)
            with contextlib.suppress(discord.HTTPException):
                await message.reply("AFK removed. Welcome back.", mention_author=False)
        for member in message.mentions:
            afk = self.store.get_afk(message.guild.id, member.id)
            if afk:
                with contextlib.suppress(discord.HTTPException):
                    await message.channel.send(f"{member.display_name} is AFK: {afk['reason']}")

    async def handle_trivia_answer(self, message: discord.Message) -> bool:
        session = self.state.trivia_sessions.get(message.author.id)
        if not session:
            return False
        answer = normalize_text(message.content).upper()
        option_map = {chr(65 + index): value for index, value in enumerate(session["options"])}
        choice = option_map.get(answer) or (session["options"][int(answer) - 1] if answer.isdigit() and 0 < int(answer) <= len(session["options"]) else None)
        if not choice:
            return False
        del self.state.trivia_sessions[message.author.id]
        if choice == session["answer"]:
            self.store.add_coins(message.author.id, 40)
            await message.reply(f"Correct. You earned 40 coins. Answer: **{session['answer']}**", mention_author=False)
        else:
            await message.reply(f"Not quite. Correct answer: **{session['answer']}**", mention_author=False)
        return True

    async def handle_custom_command(self, message: discord.Message) -> bool:
        if not message.guild:
            return False
        content = message.content.strip()
        if not content.startswith(BOT_PREFIX):
            return False
        command_name = content[len(BOT_PREFIX):].split()[0].lower()
        if self.get_command(command_name):
            return False
        custom = self.store.custom_commands.get(str(message.guild.id), {})
        response = custom.get(command_name)
        if not response:
            return False
        await message.channel.send(response)
        return True

    async def handle_automod(self, message: discord.Message) -> bool:
        if not message.guild or not isinstance(message.author, discord.Member):
            return False
        if message.author.guild_permissions.manage_messages:
            return False
        settings = self.get_guild_settings(message.guild.id)
        lowered = message.content.lower()
        filtered_words = self.store.get_word_filter(message.guild.id)
        if filtered_words and any(word.lower() in lowered for word in filtered_words):
            with contextlib.suppress(discord.HTTPException, discord.Forbidden):
                await message.delete()
            await self.log_to_mod_channel(message.guild, "Filtered Message", f"{message.author} used a filtered term.", discord.Color.red())
            return True
        if settings.get("anti_link") and LINK_REGEX.search(message.content):
            with contextlib.suppress(discord.HTTPException, discord.Forbidden):
                await message.delete()
            with contextlib.suppress(discord.HTTPException):
                await message.channel.send(f"{message.author.mention} links are blocked here.")
            return True
        if settings.get("anti_spam"):
            key = (message.guild.id, message.author.id)
            timestamps = self.state.spam_tracker[key]
            now = time.time()
            timestamps[:] = [value for value in timestamps if now - value < SPAM_WINDOW_SECONDS]
            timestamps.append(now)
            if len(timestamps) >= SPAM_MESSAGE_THRESHOLD:
                with contextlib.suppress(discord.HTTPException, discord.Forbidden):
                    await message.channel.send(f"{message.author.mention} slow down. You are tripping spam protection.")
                return True
        return False

    async def on_message(self, message: discord.Message):
        if message.author.bot:
            return
        if message.guild:
            settings = self.get_guild_settings(message.guild.id)
            await self.handle_afk(message)
            if await self.handle_trivia_answer(message):
                return
            if await self.handle_automod(message):
                return
            if await self.handle_custom_command(message):
                return
            await self.award_xp(message)
            if settings.get("chat_enabled", True) and self.user and self.user.mentioned_in(message) and not message.content.strip().startswith(BOT_PREFIX):
                prompt = strip_bot_mention(message.content, self.user.id)
                if not prompt:
                    reply = await asyncio.to_thread(self.knowledge.build_assistant_greeting, message.author.id)
                else:
                    reply = await asyncio.to_thread(
                        self.knowledge.build_smart_reply,
                        message.author.id,
                        prompt,
                        True,
                    )
                await message.reply(reply, mention_author=False)
                return
        await self.process_commands(message)

    async def on_command_error(self, ctx: commands.Context, error: commands.CommandError):
        if hasattr(ctx.command, "on_error"):
            return
        error = getattr(error, "original", error)
        if isinstance(error, commands.CommandNotFound):
            return
        if isinstance(error, commands.MissingRequiredArgument):
            await ctx.send(f"Missing argument: `{error.param.name}`. Try `!help {ctx.command}`.")
            return
        if isinstance(error, commands.BadArgument):
            await ctx.send("That argument did not parse cleanly. Check `!help` for the command format.")
            return
        if isinstance(error, commands.MissingPermissions):
            await ctx.send("You do not have permission for that.")
            return
        if isinstance(error, commands.NoPrivateMessage):
            await ctx.send("That command only works in a server.")
            return
        if isinstance(error, discord.ClientException):
            message = str(error)
            if "PyNaCl library needed in order to use voice" in message:
                await ctx.send("Voice support failed to initialize in that bot process. Close every SpringBot window and start it again with `start_springbot.cmd`.")
                return
            await ctx.send(message)
            return
        if isinstance(error, RuntimeError):
            message = str(error)
            if "PyNaCl library needed in order to use voice" in message or "davey library needed in order to use voice" in message:
                append_voice_debug(f"runtime voice error surfaced: {message}")
                await ctx.send("Voice support failed to initialize in that bot process. Close every SpringBot window and start it again with `start_springbot.cmd`.")
                return
            await ctx.send(message)
            return
        if isinstance(error, commands.CommandError):
            await ctx.send(str(error))
            return
        await ctx.send(f"Something broke: `{error}`")


class BrainCog(commands.Cog, name="AI & Learning"):
    def __init__(self, bot: SpringBot):
        self.bot = bot

    def _build_mood_music_query(self, request: str) -> str:
        clean = normalize_text(request)
        lowered = clean.lower()
        mood_map = {
            "calm": "calming jazz instrumental",
            "calming": "calming jazz instrumental",
            "relax": "relaxing jazz instrumental",
            "relaxing": "relaxing jazz instrumental",
            "chill": "chill lofi beats",
            "peaceful": "peaceful piano instrumental",
            "sleepy": "sleepy ambient piano",
            "sad": "sad acoustic songs",
            "happy": "happy upbeat pop mix",
            "upbeat": "upbeat feel good music",
            "focus": "focus lofi study beats",
            "study": "study lofi beats",
            "romantic": "romantic jazz playlist",
            "hype": "hype rap playlist",
            "energetic": "energetic workout mix",
        }
        style_words = [
            "jazz", "lofi", "piano", "instrumental", "acoustic", "orchestra", "classical",
            "rnb", "r&b", "soul", "hip hop", "rap", "pop", "ambient", "beats", "study",
        ]
        matched_mood = next((value for key, value in mood_map.items() if key in lowered), "")
        matched_styles = [word for word in style_words if word in lowered]
        query = clean
        fillers = [
            r"^(?:spring bot\s+)?(?:can you|could you|would you|do you think you can|please)\s+",
            r"^(?:play|put on|queue up|queue|start)\s+",
            r"^(?:me\s+)?(?:some\s+)?",
        ]
        for pattern in fillers:
            query = re.sub(pattern, "", query, flags=re.IGNORECASE)
        query = re.sub(r"\b(for me|please)\b", "", query, flags=re.IGNORECASE)
        query = normalize_text(query)
        query = re.sub(r"\b(music|song|songs|playlist)\b", "", query, flags=re.IGNORECASE)
        query = normalize_text(query)
        if query and any(token in query.lower() for token in style_words):
            if any(word in query.lower() for word in {"calm", "calming", "relax", "relaxing", "chill", "peaceful"}):
                query += " instrumental"
            return normalize_text(query)
        if query and len(query.split()) >= 2:
            return query
        if matched_mood and matched_styles:
            return normalize_text(f"{matched_mood} {' '.join(matched_styles[:2])}")
        if matched_mood:
            return matched_mood
        return normalize_text(clean) or "chill jazz instrumental"

    def _parse_assistant_music_request(self, request: str) -> tuple[str, str] | None:
        clean = normalize_text(request)
        lowered = clean.lower()
        if re.search(r"\b(pause|hold up|stop for a sec)\b", lowered):
            return ("pause", "")
        if re.search(r"\b(resume|keep going|continue the music)\b", lowered):
            return ("resume", "")
        if re.search(r"\b(skip|next song|change the song)\b", lowered):
            return ("skip", "")
        if re.search(r"\b(leave|disconnect|get out of the voice|leave the voice)\b", lowered):
            return ("leave", "")
        if re.search(r"\b(join|come to my voice|hop in the voice)\b", lowered):
            return ("join", "")
        play_patterns = [
            r"(?:can you|could you|would you|do you think you can|please)?\s*(?:play|put on|queue up|queue|start)\s+(?P<query>.+)",
            r"(?:i want|i need)\s+(?P<query>.+?)\s+(?:music|songs?)$",
        ]
        for pattern in play_patterns:
            match = re.search(pattern, clean, flags=re.IGNORECASE)
            if match:
                query = self._build_mood_music_query(match.group("query"))
                return ("play", query)
        if "music" in lowered and any(word in lowered for word in {"calm", "calming", "relax", "relaxing", "chill", "happy", "sad", "focus", "study", "jazz", "lofi"}):
            return ("play", self._build_mood_music_query(clean))
        return None

    async def _handle_assistant_music_request(self, ctx: commands.Context, request: str) -> dict | None:
        parsed = self._parse_assistant_music_request(request)
        if not parsed:
            return None
        action, query = parsed
        if action == "join":
            voice = await self.bot.music.ensure_voice(ctx)
            return {"text": f"Joined **{voice.channel.name}** and I'm ready."}
        if action == "leave":
            return {"text": await self.bot.music.stop_and_disconnect(ctx.guild)}
        if action == "pause":
            voice = ctx.guild.voice_client if ctx.guild else None
            if not voice or not voice.is_playing():
                raise commands.CommandError("Nothing is playing right now.")
            voice.pause()
            return {"text": "Paused it."}
        if action == "resume":
            voice = ctx.guild.voice_client if ctx.guild else None
            if not voice or not voice.is_paused():
                raise commands.CommandError("Nothing is paused right now.")
            voice.resume()
            return {"text": "Back on it."}
        if action == "skip":
            voice = ctx.guild.voice_client if ctx.guild else None
            if not voice or not voice.is_playing():
                raise commands.CommandError("Nothing is playing right now.")
            voice.stop()
            return {"text": "Skipped. I'll move to the next one."}
        if action == "play":
            track = await self.bot.music.enqueue(ctx, query)
            if track.get("started_now"):
                return {"text": f"Queued up **{track['title']}** and I'm starting it now."}
            return {"text": "Added it to the queue.", "embed": build_track_embed(track, "Queued")}
        return None

    def _find_role_by_name(self, guild: discord.Guild, raw_name: str) -> discord.Role | None:
        target = normalize_text(raw_name).strip("\"'")
        if not target:
            return None
        exact = discord.utils.get(guild.roles, name=target)
        if exact:
            return exact
        lowered = target.lower()
        exact_ci = next((role for role in guild.roles if role.name.lower() == lowered), None)
        if exact_ci:
            return exact_ci
        partial = [role for role in guild.roles if lowered in role.name.lower()]
        if len(partial) == 1:
            return partial[0]
        return None

    def _find_channel_by_name(self, guild: discord.Guild, raw_name: str) -> discord.abc.GuildChannel | None:
        target = normalize_text(raw_name).strip("\"'#")
        if not target:
            return None
        exact = discord.utils.get(guild.channels, name=target)
        if exact:
            return exact
        lowered = target.lower()
        exact_ci = next((channel for channel in guild.channels if channel.name.lower() == lowered), None)
        if exact_ci:
            return exact_ci
        partial = [channel for channel in guild.channels if lowered in channel.name.lower()]
        if len(partial) == 1:
            return partial[0]
        return None

    def _parse_assistant_role_rename(self, request: str) -> tuple[str, str] | None:
        clean = normalize_text(request)
        patterns = [
            r"^(?:please\s+)?(?:change|rename)\s+(?:the\s+)?(?P<old>.+?)\s+role\s+(?:name\s+)?to\s+(?P<new>.+)$",
            r"^(?:please\s+)?(?:change|rename)\s+role\s+(?P<old>.+?)\s+to\s+(?P<new>.+)$",
        ]
        for pattern in patterns:
            match = re.match(pattern, clean, flags=re.IGNORECASE)
            if match:
                old_name = normalize_text(match.group("old")).strip("\"'")
                new_name = normalize_text(match.group("new")).strip("\"'")
                if old_name and new_name:
                    return old_name, new_name
        return None

    def _parse_assistant_channel_rename(self, request: str) -> tuple[str, str] | None:
        clean = normalize_text(request)
        patterns = [
            r"^(?:please\s+)?(?:change|rename)\s+(?:the\s+)?(?P<old>.+?)\s+channel\s+(?:name\s+)?to\s+(?P<new>.+)$",
            r"^(?:please\s+)?(?:change|rename)\s+channel\s+(?P<old>.+?)\s+to\s+(?P<new>.+)$",
        ]
        for pattern in patterns:
            match = re.match(pattern, clean, flags=re.IGNORECASE)
            if match:
                old_name = normalize_text(match.group("old")).strip("\"'#")
                new_name = normalize_text(match.group("new")).strip("\"'#")
                if old_name and new_name:
                    return old_name, new_name
        return None

    async def _handle_assistant_admin_request(self, ctx: commands.Context, request: str) -> str | None:
        if not ctx.guild or not isinstance(ctx.author, discord.Member):
            return None

        server_cog = self.bot.get_cog("Server")
        role_rename = self._parse_assistant_role_rename(request)
        if role_rename:
            if not (ctx.author.guild_permissions.administrator or ctx.author.guild_permissions.manage_roles):
                return "You need `Manage Roles` or `Administrator` for that."
            old_name, new_name = role_rename
            role = self._find_role_by_name(ctx.guild, old_name)
            if not role:
                return f"I couldn't find a role named **{old_name}**."
            if isinstance(server_cog, ServerCog):
                server_cog._assert_manageable_role(ctx, role)
            updated_name = normalize_text(new_name)[:100]
            before = role.name
            await role.edit(name=updated_name, reason=f"Assistant rename requested by {ctx.author}")
            return f"Renamed role **{before}** to **{updated_name}**."

        channel_rename = self._parse_assistant_channel_rename(request)
        if channel_rename:
            if not (ctx.author.guild_permissions.administrator or ctx.author.guild_permissions.manage_channels):
                return "You need `Manage Channels` or `Administrator` for that."
            old_name, new_name = channel_rename
            channel = self._find_channel_by_name(ctx.guild, old_name)
            if not channel:
                return f"I couldn't find a channel named **{old_name}**."
            if isinstance(server_cog, ServerCog):
                safe_name = server_cog._safe_channel_name(new_name) if isinstance(channel, discord.TextChannel) else normalize_text(new_name)[:100]
            else:
                safe_name = normalize_text(new_name)[:100]
            before = channel.name
            await channel.edit(name=safe_name, reason=f"Assistant rename requested by {ctx.author}")
            return f"Renamed channel **{before}** to **{safe_name}**."

        return None

    @commands.command(name="springhelp", aliases=["helpme"], help="Show the full SpringBot command guide.")
    async def springhelp(self, ctx: commands.Context):
        await ctx.send(embed=build_command_guide_embed(self.bot))

    @commands.command(name="about", help="Show what SpringBot is built to do.")
    async def about(self, ctx: commands.Context):
        embed = discord.Embed(
            title="About SpringBot",
            description=(
                "SpringBot is your smart, chill Discord assistant. It can talk naturally, explain topics in different styles, "
                "help with studying, manage your server, and pull live info when needed."
            ),
            color=discord.Color.blurple(),
        )
        embed.add_field(
            name="Core Strengths",
            value="Conversation, learning, live lookups, server management, moderation, and music.",
            inline=False,
        )
        embed.add_field(
            name="Explanation Styles",
            value="friend, simple, technical, study, step_by_step, real_world, exam_prep",
            inline=False,
        )
        embed.add_field(
            name="Quick Start",
            value="`!assistant help`\n`!chat explain subnetting`\n`!style study`\n`!weather Chicago`\n`!news`",
            inline=False,
        )
        language = self.bot.store.get_user_prefs(ctx.author.id)["language"]
        if language != "english":
            embed.title = self.bot.knowledge.maybe_translate_for_user(ctx.author.id, embed.title)
            embed.description = self.bot.knowledge.maybe_translate_for_user(ctx.author.id, embed.description)
            translated_fields = []
            for field in embed.fields:
                translated_fields.append(
                    (
                        self.bot.knowledge.maybe_translate_for_user(ctx.author.id, field.name),
                        self.bot.knowledge.maybe_translate_for_user(ctx.author.id, field.value),
                        field.inline,
                    )
                )
            embed.clear_fields()
            for name, value, inline in translated_fields:
                embed.add_field(name=name, value=value, inline=inline)
        await ctx.send(embed=embed)

    @commands.command(name="assistant", aliases=["briefing", "assist"], help="Show your assistant briefing, or give SpringBot a request in assistant mode.")
    async def assistant(self, ctx: commands.Context, *, request: str = ""):
        if request:
            try:
                music_result = await self._handle_assistant_music_request(ctx, request)
                if music_result:
                    if music_result.get("embed"):
                        await ctx.send(music_result["text"], embed=music_result["embed"])
                    else:
                        await ctx.send(music_result["text"])
                    return
                action_result = await self._handle_assistant_admin_request(ctx, request)
            except commands.CommandError as exc:
                await ctx.send(str(exc))
                return
            except discord.Forbidden:
                await ctx.send("Discord blocked that change. Move my role higher or give me the right permissions.")
                return
            except discord.HTTPException:
                await ctx.send("Discord rejected that change before it finished.")
                return
            if action_result:
                await ctx.send(action_result)
                return
        async with ctx.typing():
            if request:
                reply = await asyncio.to_thread(self.bot.knowledge.build_smart_reply, ctx.author.id, request, True, "assistant")
            else:
                reply = await asyncio.to_thread(self.bot.knowledge.build_assistant_briefing, ctx.author.id, True)
        await ctx.send(reply)

    @commands.command(name="plan", help="Build a practical step-by-step plan for a goal.")
    async def plan(self, ctx: commands.Context, *, goal: str):
        async with ctx.typing():
            reply = await asyncio.to_thread(self.bot.knowledge.build_plan, goal, ctx.author.id)
        await ctx.send(reply)

    @commands.command(name="todo", help="Manage your task list: `!todo add <task>`, `!todo list`, `!todo done <number>`, `!todo remove <number>`, `!todo clear`, `!todo clear done`.")
    async def todo(self, ctx: commands.Context, action: str = "list", *, text: str = ""):
        key = normalize_text(action).lower()
        if key in {"list", "show", "view"}:
            await ctx.send(self.bot.knowledge.build_task_overview(ctx.author.id))
            return
        if key in {"add", "new"}:
            if not text:
                await ctx.send("Use `!todo add <task>`.")
                return
            task = self.bot.store.add_assistant_task(ctx.author.id, text)
            await ctx.send(f"Task saved: {task['text']}")
            return
        if key in {"done", "complete", "finish"}:
            if not text.isdigit():
                await ctx.send("Use `!todo done <number>`.")
                return
            task = self.bot.store.complete_assistant_task(ctx.author.id, int(text) - 1)
            if not task:
                await ctx.send("I could not find that task number.")
                return
            await ctx.send(f"Marked complete: {task['text']}")
            return
        if key in {"remove", "delete"}:
            if not text.isdigit():
                await ctx.send("Use `!todo remove <number>`.")
                return
            task = self.bot.store.remove_assistant_task(ctx.author.id, int(text) - 1)
            if not task:
                await ctx.send("I could not find that task number.")
                return
            await ctx.send(f"Removed task: {task['text']}")
            return
        if key == "clear":
            completed_only = normalize_text(text).lower() in {"done", "completed", "finished"}
            removed = self.bot.store.clear_assistant_tasks(ctx.author.id, completed_only=completed_only)
            if completed_only:
                await ctx.send(f"Cleared {removed} completed task(s).")
            else:
                await ctx.send(f"Cleared {removed} task(s).")
            return
        await ctx.send("Use `!todo add`, `!todo list`, `!todo done <number>`, `!todo remove <number>`, or `!todo clear`.")

    @commands.command(name="note", aliases=["notes"], help="Manage saved notes: `!note add <text>`, `!note list`, `!note remove <number>`, `!note clear`.")
    async def note(self, ctx: commands.Context, action: str = "list", *, text: str = ""):
        key = normalize_text(action).lower()
        if key in {"list", "show", "view"}:
            await ctx.send(self.bot.knowledge.build_note_overview(ctx.author.id))
            return
        if key in {"add", "new", "remember", "save"}:
            if not text:
                await ctx.send("Use `!note add <text>`.")
                return
            note = self.bot.store.add_assistant_note(ctx.author.id, text)
            await ctx.send(f"Note saved: {note['text']}")
            return
        if key in {"remove", "delete"}:
            if not text.isdigit():
                await ctx.send("Use `!note remove <number>`.")
                return
            note = self.bot.store.remove_assistant_note(ctx.author.id, int(text) - 1)
            if not note:
                await ctx.send("I could not find that note number.")
                return
            await ctx.send(f"Removed note: {note['text']}")
            return
        if key == "clear":
            self.bot.store.clear_assistant_notes(ctx.author.id)
            await ctx.send("Cleared your saved notes.")
            return
        await ctx.send("Use `!note add`, `!note list`, `!note remove <number>`, or `!note clear`.")

    @commands.command(name="ask", help="Ask SpringBot a question without adding it to chat memory.")
    async def ask(self, ctx: commands.Context, *, question: str):
        async with ctx.typing():
            reply = await asyncio.to_thread(self.bot.knowledge.build_smart_reply, ctx.author.id, question, False)
        await ctx.send(reply)

    @commands.command(name="tech", help="Ask a technical question and get a focused answer.")
    async def tech(self, ctx: commands.Context, *, question: str):
        async with ctx.typing():
            reply = await asyncio.to_thread(self.bot.knowledge.build_smart_reply, ctx.author.id, question, False, "tech")
        await ctx.send(reply)

    @commands.command(name="search", help="Pull live web results for a topic.")
    async def search(self, ctx: commands.Context, *, query: str):
        async with ctx.typing():
            summary, results = await asyncio.to_thread(self.bot.knowledge.build_live_context, query)
        if not summary and not results:
            await ctx.send("I could not pull live results for that right now.")
            return
        embed = discord.Embed(title=f"Search: {shorten(query, 120)}", description=shorten(summary or "Results found.", 1800), color=discord.Color.blue())
        if results:
            lines = [f"[{item['title']}]({item['url']})" for item in results[:3]]
            embed.add_field(name="Top Links", value="\n".join(lines), inline=False)
        await ctx.send(embed=embed)

    @commands.command(name="news", aliases=["headlines"], help="Show current top headlines.")
    async def news(self, ctx: commands.Context):
        async with ctx.typing():
            items = await asyncio.to_thread(self.bot.knowledge.get_news_headlines, 5)
        if not items:
            await ctx.send(self.bot.knowledge.maybe_translate_for_user(ctx.author.id, "I couldn't pull live headlines right now."))
            return
        embed = discord.Embed(title="Top Headlines", color=discord.Color.blue())
        lines = []
        for index, item in enumerate(items, start=1):
            title = item["title"]
            link = item["link"]
            if link.startswith("http"):
                lines.append(f"{index}. [{title}]({link})")
            else:
                lines.append(f"{index}. {title}")
        description = "\n".join(lines)
        if self.bot.store.get_user_prefs(ctx.author.id)["language"] != "english":
            description = self.bot.knowledge.maybe_translate_for_user(ctx.author.id, description)
            embed.title = self.bot.knowledge.maybe_translate_for_user(ctx.author.id, embed.title)
        embed.description = description
        source = items[0].get("pub_date") or "Live feed"
        footer_text = f"Source feed active | Latest item date: {source}"
        if self.bot.store.get_user_prefs(ctx.author.id)["language"] != "english":
            footer_text = self.bot.knowledge.maybe_translate_for_user(ctx.author.id, footer_text)
        embed.set_footer(text=footer_text)
        await ctx.send(embed=embed)

    @commands.command(name="weather", aliases=["forecast"], help="Show live weather for a location.")
    async def weather(self, ctx: commands.Context, *, location: str):
        async with ctx.typing():
            snapshot = await asyncio.to_thread(self.bot.knowledge.get_weather_snapshot, location)
        if not snapshot:
            await ctx.send("I couldn't pull the weather for that location right now.")
            return
        embed = discord.Embed(
            title=f"Weather: {snapshot['place']}",
            description=snapshot["condition"],
            color=discord.Color.teal(),
        )
        embed.add_field(name="Temperature", value=f"{snapshot['temp_f']} F / {snapshot['temp_c']} C", inline=True)
        embed.add_field(name="Feels Like", value=f"{snapshot['feels_f']} F", inline=True)
        embed.add_field(name="Humidity", value=f"{snapshot['humidity']}%", inline=True)
        embed.add_field(name="Wind", value=f"{snapshot['wind_mph']} mph", inline=True)
        language = self.bot.store.get_user_prefs(ctx.author.id)["language"]
        if language != "english":
            embed.title = self.bot.knowledge.maybe_translate_for_user(ctx.author.id, embed.title)
            embed.description = self.bot.knowledge.maybe_translate_for_user(ctx.author.id, embed.description)
            translated_fields = []
            for field in embed.fields:
                translated_fields.append(
                    (
                        self.bot.knowledge.maybe_translate_for_user(ctx.author.id, field.name),
                        self.bot.knowledge.maybe_translate_for_user(ctx.author.id, field.value),
                        field.inline,
                    )
                )
            embed.clear_fields()
            for name, value, inline in translated_fields:
                embed.add_field(name=name, value=value, inline=inline)
        await ctx.send(embed=embed)

    @commands.command(name="chat", help="Talk with SpringBot using memory.")
    async def chat(self, ctx: commands.Context, *, message: str):
        if ctx.guild and not self.bot.get_guild_settings(ctx.guild.id).get("chat_enabled", True):
            await ctx.send("Chat mode is disabled on this server.")
            return
        async with ctx.typing():
            reply = await asyncio.to_thread(self.bot.knowledge.build_smart_reply, ctx.author.id, message, True)
        await ctx.send(reply)

    @commands.command(name="learn", help="Browse a loaded subject pack. Use `!learn <subject> [mode] [topic]`.")
    async def learn(self, ctx: commands.Context, subject: str, mode: str = "friend", *, question: str = None):
        translated_subject, _, reply_language = self.bot.knowledge.prepare_multilingual_input(ctx.author.id, subject)
        translated_question = None
        if question:
            translated_question, _, reply_language = self.bot.knowledge.prepare_multilingual_input(ctx.author.id, question)
        subject_key = normalize_text(translated_subject).lower().replace(" ", "_")
        subject_aliases = {
            "cert": "certifications",
            "certification": "certifications",
            "tech_certifications": "certifications",
            "cyber": "cybersecurity",
            "tech": "technology",
            "funfacts": "fun_facts",
            "fun_fact": "fun_facts",
        }
        subject_key = subject_aliases.get(subject_key, subject_key)
        mode_key = normalize_mode_name(mode)
        if mode_key not in SUPPORTED_MODES:
            await ctx.send(f"Unknown mode. Options: {', '.join(SUPPORTED_MODES)}")
            return
        if subject_key not in SPRING_KNOWLEDGE_PACK:
            await ctx.send("I don't have that subject loaded yet, but I can still try to explain it.")
            return

        topic_block = SPRING_KNOWLEDGE_PACK[subject_key]
        entries = list(topic_block.items())
        if translated_question:
            query = normalize_text(translated_question).lower()
            filtered = []
            for key, value in entries:
                pretty = key.replace("_", " ").lower()
                if query in pretty or pretty in query or query in value.lower():
                    filtered.append((key, value))
            if filtered:
                entries = filtered
        lines = []
        for key, value in entries[:5]:
            label = key.replace("_", " ").title()
            explanation = explain_topic(label, value, mode_key)
            lines.append(f"**{label}** — {explanation}")
        if not lines:
            await ctx.send("I have that subject loaded, but I couldn't match that topic yet.")
            return
        intro = chill_intro() if mode_key in {"assistant", "chat", "friend", "simple"} else "Loaded study notes:"
        await ctx.send(self.bot.knowledge.maybe_translate_for_user(ctx.author.id, f"{intro}\n\n" + "\n\n".join(lines), reply_language))

    @commands.command(name="mode", help="Set your reply style: assistant, simple, friend, technical, step_by_step, real_world, exam_prep, jarvis, lore, chat, brief.")
    async def mode(self, ctx: commands.Context, name: str = None):
        if not name:
            prefs = self.bot.store.get_user_prefs(ctx.author.id)
            await ctx.send(f"Current mode: `{prefs['mode']}` | Options: {', '.join(SUPPORTED_MODES)}")
            return
        key = normalize_mode_name(name)
        if key not in SUPPORTED_MODES:
            await ctx.send(f"Unknown mode. Options: {', '.join(SUPPORTED_MODES)}")
            return
        prefs = self.bot.store.get_user_prefs(ctx.author.id)
        prefs["mode"] = key
        self.bot.store.save("user_prefs")
        await ctx.send(f"Mode set to `{key}`.")

    @commands.command(name="style", help="Set a learning/explanation style quickly: friend, simple, technical, study, or steps.")
    async def style(self, ctx: commands.Context, name: str = None):
        if not name:
            prefs = self.bot.store.get_user_prefs(ctx.author.id)
            await ctx.send(self.bot.knowledge.maybe_translate_for_user(
                ctx.author.id,
                "Explanation styles: `friend`, `simple`, `technical`, `study`, `steps`.\n"
                f"Current style: `{prefs['mode']}`."
            ))
            return
        key = normalize_mode_name(name)
        allowed = {"friend", "simple", "technical", "study", "step_by_step"}
        if key not in allowed:
            await ctx.send(self.bot.knowledge.maybe_translate_for_user(ctx.author.id, "Use one of these styles: `friend`, `simple`, `technical`, `study`, or `steps`."))
            return
        prefs = self.bot.store.get_user_prefs(ctx.author.id)
        prefs["mode"] = key
        self.bot.store.save("user_prefs")
        await ctx.send(self.bot.knowledge.maybe_translate_for_user(ctx.author.id, f"Explanation style set to `{key}`."))

    @commands.command(name="resetchat", help="Clear your saved conversation history with SpringBot.")
    async def resetchat(self, ctx: commands.Context):
        self.bot.store.clear_chat_history(ctx.author.id)
        await ctx.send("Chat memory cleared.")

    @commands.command(name="solve", help="Solve math problems step by step, including algebra, systems, derivatives, integrals, factoring, and simplification.")
    async def solve(self, ctx: commands.Context, *, problem: str):
        async with ctx.typing():
            response = await asyncio.to_thread(self.bot.knowledge.build_solver, problem, ctx.author.id)
        await ctx.send(response)

    @commands.command(name="explain", help="Explain a topic simply.")
    async def explain(self, ctx: commands.Context, *, topic: str):
        async with ctx.typing():
            response = await asyncio.to_thread(self.bot.knowledge.build_explanation, topic, ctx.author.id)
        await ctx.send(response)

    @commands.command(name="define", help="Define a word and show meaning, origin, or example when possible.")
    async def define(self, ctx: commands.Context, *, word: str):
        async with ctx.typing():
            response = await asyncio.to_thread(self.bot.knowledge.build_definition, word, ctx.author.id)
        await ctx.send(response)

    @commands.command(name="compare", help="Compare two topics. Use `topic A vs topic B`.")
    async def compare(self, ctx: commands.Context, *, topics: str):
        parts = re.split(r"\s+vs\s+|\s*\|\s*|\s*,\s*", topics, maxsplit=1, flags=re.IGNORECASE)
        if len(parts) < 2:
            await ctx.send("Use it like `!compare tcp vs udp`.")
            return
        async with ctx.typing():
            response = await asyncio.to_thread(self.bot.knowledge.build_comparison, parts[0], parts[1], ctx.author.id)
        await ctx.send(response)

    @commands.command(name="summarize", help="Summarize a block of text.")
    async def summarize(self, ctx: commands.Context, *, text: str):
        summary = self.bot.knowledge.summarize_text_block(text)
        await ctx.send(self.bot.knowledge.maybe_translate_for_user(ctx.author.id, summary))

    @commands.command(name="rewrite", help="Rewrite text in a different style. Styles: professional, casual, persuasive, formal, simple.")
    async def rewrite(self, ctx: commands.Context, style: str, *, text: str):
        async with ctx.typing():
            response = await asyncio.to_thread(self.bot.knowledge.build_rewrite, style, text, ctx.author.id)
        await ctx.send(response)

    @commands.command(name="flashcard", help="Generate 5 study flashcards for a topic.")
    async def flashcard(self, ctx: commands.Context, *, topic: str):
        async with ctx.typing():
            response = await asyncio.to_thread(self.bot.knowledge.build_flashcards, topic, ctx.author.id)
        await ctx.send(response)

    @commands.command(name="studyguide", help="Generate a compact study guide for a topic.")
    async def studyguide(self, ctx: commands.Context, *, topic: str):
        async with ctx.typing():
            response = await asyncio.to_thread(self.bot.knowledge.build_studyguide, topic, ctx.author.id)
        await ctx.send(response)

    @commands.command(name="funfact", help="Give a random fun fact or one about a specific topic.")
    async def funfact(self, ctx: commands.Context, *, topic: str = ""):
        response = await asyncio.to_thread(self.bot.knowledge.build_fun_fact, topic, ctx.author.id)
        await ctx.send(response)

    @commands.command(name="translate", aliases=["tr"], help="Translate text to another language.")
    async def translate(self, ctx: commands.Context, language: str, *, text: str):
        lang = self.bot.knowledge.resolve_language_name(language)
        if not lang:
            await ctx.send("Unknown language. Try `!languages`.")
            return
        async with ctx.typing():
            translated = await asyncio.to_thread(self.bot.knowledge.translate_text, text, lang)
        if not translated:
            await ctx.send("Translation failed right now.")
            return
        await ctx.send(f"{lang.title()}: {translated}")

    @commands.command(name="lang", help="Set your preferred reply language.")
    async def lang(self, ctx: commands.Context, *, language: str):
        lang = self.bot.knowledge.resolve_language_name(language)
        if not lang:
            await ctx.send(self.bot.knowledge.maybe_translate_for_user(ctx.author.id, "Unknown language. Try `!languages`."))
            return
        prefs = self.bot.store.get_user_prefs(ctx.author.id)
        prefs["language"] = lang
        self.bot.store.save("user_prefs")
        await ctx.send(self.bot.knowledge.maybe_translate_for_user(ctx.author.id, f"Language set to `{lang}`.", lang))

    @commands.command(name="languages", help="List supported languages for translation and replies.")
    async def languages(self, ctx: commands.Context):
        await ctx.send(self.bot.knowledge.maybe_translate_for_user(ctx.author.id, self.bot.knowledge.build_language_list()))


class ModerationCog(commands.Cog, name="Moderation"):
    def __init__(self, bot: SpringBot):
        self.bot = bot

    @commands.command(name="ban", help="Ban a member from the server.")
    @admin_only()
    async def ban(self, ctx: commands.Context, member: discord.Member, *, reason: str = "No reason provided."):
        await member.ban(reason=reason, delete_message_days=0)
        await ctx.send(f"{member} banned. {ack_line()}")
        await self.bot.log_to_mod_channel(ctx.guild, "Ban", f"{member} banned by {ctx.author}. Reason: {reason}", discord.Color.red())

    @commands.command(name="kick", help="Kick a member from the server.")
    @admin_only()
    async def kick(self, ctx: commands.Context, member: discord.Member, *, reason: str = "No reason provided."):
        await member.kick(reason=reason)
        await ctx.send(f"{member} kicked.")
        await self.bot.log_to_mod_channel(ctx.guild, "Kick", f"{member} kicked by {ctx.author}. Reason: {reason}", discord.Color.orange())

    @commands.command(name="timeout", help="Timeout a member. Example: `!timeout @user 10m spamming`.")
    @admin_only()
    async def timeout(self, ctx: commands.Context, member: discord.Member, duration: str, *, reason: str = "No reason provided."):
        seconds = parse_time_spec(duration)
        if not seconds:
            await ctx.send("Use durations like `10m`, `1h`, or `2d`.")
            return
        until = discord.utils.utcnow() + timedelta(seconds=seconds)
        await member.edit(timed_out_until=until, reason=reason)
        await ctx.send(f"{member.mention} timed out for {duration}.")
        await self.bot.log_to_mod_channel(ctx.guild, "Timeout", f"{member} timed out by {ctx.author} for {duration}. Reason: {reason}")

    @commands.command(name="untimeout", help="Remove a timeout from a member.")
    @admin_only()
    async def untimeout(self, ctx: commands.Context, member: discord.Member):
        await member.edit(timed_out_until=None, reason=f"Timeout removed by {ctx.author}")
        await ctx.send(f"Timeout removed for {member.mention}.")

    @commands.command(name="purge", help="Delete a number of messages from the current channel.")
    @admin_only()
    async def purge(self, ctx: commands.Context, amount: int):
        if not isinstance(ctx.channel, discord.TextChannel):
            await ctx.send("Use that in a text channel.")
            return
        deleted = await ctx.channel.purge(limit=max(1, min(amount, 100)) + 1)
        notice = await ctx.send(f"Deleted {max(len(deleted) - 1, 0)} messages.")
        await asyncio.sleep(3)
        with contextlib.suppress(discord.HTTPException):
            await notice.delete()

    @commands.command(name="move", help="Move a member to another voice channel.")
    @admin_only()
    async def move_member(self, ctx: commands.Context, member: discord.Member, *, channel: discord.VoiceChannel = None):
        target = channel or (ctx.author.voice.channel if isinstance(ctx.author, discord.Member) and ctx.author.voice else None)
        if not target:
            await ctx.send("Pick a voice channel or join one yourself first.")
            return
        await member.move_to(target, reason=f"Moved by {ctx.author}")
        await ctx.send(f"Moved {member.mention} to **{target.name}**.")

    @commands.command(name="disconnect", help="Disconnect a member from voice.")
    @admin_only()
    async def disconnect_member(self, ctx: commands.Context, member: discord.Member):
        await member.move_to(None, reason=f"Disconnected by {ctx.author}")
        await ctx.send(f"Disconnected {member.mention}.")

    @commands.command(name="warn", help="Warn a member and store the warning.")
    @admin_only()
    async def warn(self, ctx: commands.Context, member: discord.Member, *, reason: str = "No reason provided."):
        store = self.bot.store.get_warning_store(ctx.guild.id)
        warnings = store.setdefault(str(member.id), [])
        warnings.append({"reason": reason, "moderator": ctx.author.id, "ts": int(time.time())})
        self.bot.store.save("warnings")
        await ctx.send(f"{member.mention} warned. Total warnings: {len(warnings)}")
        await self.bot.log_to_mod_channel(ctx.guild, "Warn", f"{member} warned by {ctx.author}. Reason: {reason}")

    @commands.command(name="warnings", help="Show warnings for a member.")
    @admin_only()
    async def warnings(self, ctx: commands.Context, member: discord.Member):
        store = self.bot.store.get_warning_store(ctx.guild.id)
        warnings = store.get(str(member.id), [])
        if not warnings:
            await ctx.send(f"{member.mention} has no warnings.")
            return
        lines = [f"{index}. {item['reason']}" for index, item in enumerate(warnings[-10:], start=1)]
        await ctx.send(f"Warnings for {member.mention}:\n" + "\n".join(lines))

    @commands.command(name="clearwarnings", help="Clear all stored warnings for a member.")
    @admin_only()
    async def clearwarnings(self, ctx: commands.Context, member: discord.Member):
        store = self.bot.store.get_warning_store(ctx.guild.id)
        if str(member.id) in store:
            del store[str(member.id)]
            self.bot.store.save("warnings")
        await ctx.send(f"Warnings cleared for {member.mention}.")

    @commands.command(name="lock", help="Lock a text channel.")
    @admin_only()
    async def lock(self, ctx: commands.Context, channel: discord.TextChannel = None):
        target = channel or ctx.channel
        if not isinstance(target, discord.TextChannel):
            await ctx.send("That is not a text channel.")
            return
        overwrite = target.overwrites_for(ctx.guild.default_role)
        overwrite.send_messages = False
        await target.set_permissions(ctx.guild.default_role, overwrite=overwrite)
        await ctx.send(f"{target.mention} locked.")

    @commands.command(name="unlock", help="Unlock a text channel.")
    @admin_only()
    async def unlock(self, ctx: commands.Context, channel: discord.TextChannel = None):
        target = channel or ctx.channel
        if not isinstance(target, discord.TextChannel):
            await ctx.send("That is not a text channel.")
            return
        overwrite = target.overwrites_for(ctx.guild.default_role)
        overwrite.send_messages = None
        await target.set_permissions(ctx.guild.default_role, overwrite=overwrite)
        await ctx.send(f"{target.mention} unlocked.")

    @commands.command(name="slowmode", help="Set channel slowmode in seconds.")
    @admin_only()
    async def slowmode(self, ctx: commands.Context, seconds: int, channel: discord.TextChannel = None):
        target = channel or ctx.channel
        if not isinstance(target, discord.TextChannel):
            await ctx.send("That is not a text channel.")
            return
        await target.edit(slowmode_delay=max(0, min(seconds, 21600)))
        await ctx.send(f"Slowmode set to {seconds}s in {target.mention}.")

    @commands.command(name="announce", help="Send an announcement to a channel.")
    @admin_only()
    async def announce(self, ctx: commands.Context, channel: discord.TextChannel, *, message: str):
        await channel.send(message, allowed_mentions=discord.AllowedMentions.none())
        await ctx.send(f"Announcement sent to {channel.mention}.")

    @commands.command(name="nick", help="Change a member nickname.")
    @admin_only()
    async def nick(self, ctx: commands.Context, member: discord.Member, *, nickname: str = None):
        await member.edit(nick=nickname, reason=f"Nickname updated by {ctx.author}")
        await ctx.send(f"Nickname updated for {member.mention}.")

    @commands.command(name="filter", help="Manage the word filter. `!filter add word`, `!filter remove word`, `!filter list`, `!filter clear`.")
    @admin_only()
    async def filter(self, ctx: commands.Context, action: str = "list", *words: str):
        key = str(ctx.guild.id)
        current = self.bot.store.word_filter.setdefault(key, [])
        action = action.lower()
        if action == "list":
            await ctx.send("Filtered words: " + (", ".join(current) if current else "none"))
            return
        if action == "clear":
            self.bot.store.word_filter[key] = []
            self.bot.store.save("word_filter")
            await ctx.send("Word filter cleared.")
            return
        values = [normalize_text(word).lower() for word in words if normalize_text(word)]
        if not values:
            await ctx.send("Add at least one word.")
            return
        if action == "add":
            for word in values:
                if word not in current:
                    current.append(word)
            self.bot.store.word_filter[key] = sorted(set(current))
            self.bot.store.save("word_filter")
            await ctx.send("Added to filter: " + ", ".join(values))
            return
        if action == "remove":
            self.bot.store.word_filter[key] = [word for word in current if word not in values]
            self.bot.store.save("word_filter")
            await ctx.send("Removed from filter: " + ", ".join(values))
            return
        await ctx.send("Use `add`, `remove`, `list`, or `clear`.")


class ServerCog(commands.Cog, name="Server"):
    def __init__(self, bot: SpringBot):
        self.bot = bot

    def _assert_manageable_role(self, ctx: commands.Context, role: discord.Role):
        me = ctx.guild.me
        if role.is_default():
            raise commands.CommandError("I cannot directly manage the @everyone role.")
        if role.managed:
            raise commands.CommandError("That role is managed by Discord or another integration.")
        if me and role >= me.top_role:
            raise commands.CommandError(f"Move my role above **{role.name}** so I can manage it.")
        if isinstance(ctx.author, discord.Member) and ctx.author != ctx.guild.owner and role >= ctx.author.top_role:
            raise commands.CommandError(f"That role is above your highest role, so Discord will not let me manage it for you.")

    def _safe_channel_name(self, name: str) -> str:
        return normalize_text(name).replace("/", "-").replace("\\", "-")[:100]

    async def _find_or_create_category(self, guild: discord.Guild, name: str) -> tuple[discord.CategoryChannel, bool]:
        category = discord.utils.get(guild.categories, name=name)
        if category:
            return category, False
        return await guild.create_category(name), True

    async def _ensure_text_channel(self, guild: discord.Guild, category: discord.CategoryChannel, name: str) -> tuple[discord.TextChannel, bool]:
        existing = discord.utils.get(category.text_channels, name=name)
        if existing:
            return existing, False
        return await guild.create_text_channel(name=name, category=category), True

    async def _ensure_voice_channel(self, guild: discord.Guild, category: discord.CategoryChannel, name: str) -> tuple[discord.VoiceChannel, bool]:
        existing = discord.utils.get(category.voice_channels, name=name)
        if existing:
            return existing, False
        return await guild.create_voice_channel(name=name, category=category), True

    async def _apply_preset(self, guild: discord.Guild, preset_name: str) -> tuple[int, list[str]]:
        preset = SERVER_PRESETS[preset_name]
        created = 0
        notes: list[str] = []
        for category_name, channel_map in preset.items():
            category, made_category = await self._find_or_create_category(guild, category_name)
            if made_category:
                created += 1
                notes.append(f"category:{category.name}")
            for text_name in channel_map.get("text", []):
                channel, made = await self._ensure_text_channel(guild, category, self._safe_channel_name(text_name))
                if made:
                    created += 1
                    notes.append(f"text:{channel.name}")
            for voice_name in channel_map.get("voice", []):
                channel, made = await self._ensure_voice_channel(guild, category, voice_name[:100])
                if made:
                    created += 1
                    notes.append(f"voice:{channel.name}")
        return created, notes

    @commands.command(name="settings", help="Show the current SpringBot server settings.")
    @admin_only()
    async def settings(self, ctx: commands.Context):
        flags = self.bot.get_guild_settings(ctx.guild.id)
        config = self.bot.store.get_guild_config(ctx.guild.id)
        embed = discord.Embed(title="SpringBot Settings", color=discord.Color.blurple())
        embed.add_field(name="Anti Link", value=str(flags.get("anti_link", True)), inline=True)
        embed.add_field(name="Anti Spam", value=str(flags.get("anti_spam", True)), inline=True)
        embed.add_field(name="Chat Mode", value=str(flags.get("chat_enabled", True)), inline=True)
        embed.add_field(name="Filtered Words", value=str(len(self.bot.store.get_word_filter(ctx.guild.id))), inline=True)
        embed.add_field(name="Custom Commands", value=str(len(self.bot.store.custom_commands.get(str(ctx.guild.id), {}))), inline=True)
        embed.add_field(name="Welcome Channel", value=f"<#{config['welcome_channel_id']}>" if config.get("welcome_channel_id") else "Not set", inline=True)
        embed.add_field(name="Mod Log", value=f"<#{config['mod_log_channel_id']}>" if config.get("mod_log_channel_id") else "Not set", inline=True)
        embed.add_field(name="Autorole", value=f"<@&{config['auto_role_id']}>" if config.get("auto_role_id") else "Not set", inline=True)
        embed.add_field(name="Ticket Category", value=f"<#{config['ticket_category_id']}>" if config.get("ticket_category_id") else "Not set", inline=True)
        await ctx.send(embed=embed)

    @commands.command(name="togglechat", help="Toggle mention chat and !chat replies on or off for this server.")
    @admin_only()
    async def togglechat(self, ctx: commands.Context):
        flags = self.bot.get_guild_settings(ctx.guild.id)
        new_value = not flags.get("chat_enabled", True)
        flags["chat_enabled"] = new_value
        self.bot.store.save("settings")
        state = "ON" if new_value else "OFF"
        await ctx.send(f"Chat mode is now **{state}**.")

    @commands.command(name="toggleantilink", help="Quick-toggle anti-link protection for this server.")
    @admin_only()
    async def toggleantilink(self, ctx: commands.Context):
        flags = self.bot.get_guild_settings(ctx.guild.id)
        new_value = not flags.get("anti_link", True)
        flags["anti_link"] = new_value
        self.bot.store.save("settings")
        state = "ON" if new_value else "OFF"
        await ctx.send(f"Anti-link is now **{state}**.")

    @commands.command(name="toggleantispam", help="Quick-toggle anti-spam protection for this server.")
    @admin_only()
    async def toggleantispam(self, ctx: commands.Context):
        flags = self.bot.get_guild_settings(ctx.guild.id)
        new_value = not flags.get("anti_spam", True)
        flags["anti_spam"] = new_value
        self.bot.store.save("settings")
        state = "ON" if new_value else "OFF"
        await ctx.send(f"Anti-spam is now **{state}**.")

    @commands.command(name="serveraudit", help="Audit the server and show what SpringBot can manage.")
    @admin_only()
    async def serveraudit(self, ctx: commands.Context):
        me = ctx.guild.me
        perms = ctx.channel.permissions_for(me) if me else None
        config = self.bot.store.get_guild_config(ctx.guild.id)
        embed = discord.Embed(title=f"Server Audit: {ctx.guild.name}", color=discord.Color.gold())
        embed.add_field(name="Members", value=str(ctx.guild.member_count), inline=True)
        embed.add_field(name="Text Channels", value=str(len(ctx.guild.text_channels)), inline=True)
        embed.add_field(name="Voice Channels", value=str(len(ctx.guild.voice_channels)), inline=True)
        embed.add_field(name="Roles", value=str(len(ctx.guild.roles)), inline=True)
        embed.add_field(name="Bot Admin", value=str(me.guild_permissions.administrator if me else False), inline=True)
        embed.add_field(name="Manage Channels", value=str(perms.manage_channels if perms else False), inline=True)
        embed.add_field(name="Manage Roles", value=str(perms.manage_roles if perms else False), inline=True)
        missing = []
        if not config.get("welcome_channel_id"):
            missing.append("welcome channel")
        if not config.get("mod_log_channel_id"):
            missing.append("mod log channel")
        if not config.get("auto_role_id"):
            missing.append("autorole")
        if not config.get("ticket_category_id"):
            missing.append("ticket category")
        embed.add_field(name="Missing Config", value=", ".join(missing) if missing else "Nothing major missing.", inline=False)
        await ctx.send(embed=embed)

    @commands.command(name="setupserver", help="Create the common SpringBot channels, role, and ticket category.")
    @admin_only()
    async def setupserver(self, ctx: commands.Context):
        guild = ctx.guild
        created = []
        welcome = discord.utils.get(guild.text_channels, name=WELCOME_CHANNEL_NAME)
        if not welcome:
            welcome = await guild.create_text_channel(WELCOME_CHANNEL_NAME)
            created.append(welcome.name)
        modlog = discord.utils.get(guild.text_channels, name=MOD_LOG_CHANNEL_NAME)
        if not modlog:
            modlog = await guild.create_text_channel(MOD_LOG_CHANNEL_NAME)
            created.append(modlog.name)
        tickets = discord.utils.get(guild.categories, name=TICKET_CATEGORY_NAME)
        if not tickets:
            tickets = await guild.create_category(TICKET_CATEGORY_NAME)
            created.append(tickets.name)
        auto_role = discord.utils.get(guild.roles, name=AUTO_ROLE_NAME)
        if not auto_role:
            auto_role = await guild.create_role(name=AUTO_ROLE_NAME, mentionable=False)
            created.append(auto_role.name)
        self.bot.store.set_guild_config_value(guild.id, "welcome_channel_id", welcome.id)
        self.bot.store.set_guild_config_value(guild.id, "mod_log_channel_id", modlog.id)
        self.bot.store.set_guild_config_value(guild.id, "ticket_category_id", tickets.id)
        self.bot.store.set_guild_config_value(guild.id, "auto_role_id", auto_role.id)
        await ctx.send("Setup finished. Created: " + (", ".join(created) if created else "nothing new"))

    @commands.command(name="serverpreset", help="Build a channel layout preset. Options: community, gaming, study, business.")
    @admin_only()
    async def serverpreset(self, ctx: commands.Context, preset: str):
        key = normalize_text(preset).lower()
        if key not in SERVER_PRESETS:
            raise commands.CommandError(f"Unknown preset. Options: {', '.join(SERVER_PRESETS)}")
        created, notes = await self._apply_preset(ctx.guild, key)
        await ctx.send(
            f"Preset `{key}` applied. Created `{created}` new items."
            + (f"\nRecent additions: {', '.join(notes[:12])}" if notes else "\nEverything in that preset already existed.")
        )

    @commands.command(name="setwelcome", help="Set the welcome channel.")
    @admin_only()
    async def setwelcome(self, ctx: commands.Context, channel: discord.TextChannel):
        self.bot.store.set_guild_config_value(ctx.guild.id, "welcome_channel_id", channel.id)
        await ctx.send(f"Welcome channel set to {channel.mention}.")

    @commands.command(name="setmodlog", help="Set the moderation log channel.")
    @admin_only()
    async def setmodlog(self, ctx: commands.Context, channel: discord.TextChannel):
        self.bot.store.set_guild_config_value(ctx.guild.id, "mod_log_channel_id", channel.id)
        await ctx.send(f"Mod log channel set to {channel.mention}.")

    @commands.command(name="setautorole", help="Set the autorole for new members.")
    @admin_only()
    async def setautorole(self, ctx: commands.Context, role: discord.Role):
        self._assert_manageable_role(ctx, role)
        self.bot.store.set_guild_config_value(ctx.guild.id, "auto_role_id", role.id)
        await ctx.send(f"Autorole set to {role.mention}.")

    @commands.command(name="setticketcategory", help="Set the ticket category.")
    @admin_only()
    async def setticketcategory(self, ctx: commands.Context, category: discord.CategoryChannel):
        self.bot.store.set_guild_config_value(ctx.guild.id, "ticket_category_id", category.id)
        await ctx.send(f"Ticket category set to **{category.name}**.")

    @commands.command(name="lockdownall", help="Lock all text channels for @everyone.")
    @admin_only()
    async def lockdownall(self, ctx: commands.Context):
        state = {}
        for channel in ctx.guild.text_channels:
            overwrite = channel.overwrites_for(ctx.guild.default_role)
            state[str(channel.id)] = serialize_perm_value(overwrite.send_messages)
            overwrite.send_messages = False
            await channel.set_permissions(ctx.guild.default_role, overwrite=overwrite)
        self.bot.store.set_guild_config_value(ctx.guild.id, "lockdown_state", state)
        await ctx.send("Server-wide lockdown enabled.")

    @commands.command(name="unlockdownall", help="Restore all channel send permissions after lockdown.")
    @admin_only()
    async def unlockdownall(self, ctx: commands.Context):
        config = self.bot.store.get_guild_config(ctx.guild.id)
        lockdown_state = config.get("lockdown_state", {})
        for channel in ctx.guild.text_channels:
            overwrite = channel.overwrites_for(ctx.guild.default_role)
            previous = deserialize_perm_value(lockdown_state.get(str(channel.id)))
            overwrite.send_messages = previous
            await channel.set_permissions(ctx.guild.default_role, overwrite=overwrite)
        self.bot.store.set_guild_config_value(ctx.guild.id, "lockdown_state", {})
        await ctx.send("Lockdown lifted.")

    @commands.command(name="createchannel", help="Create a text, voice, or category channel. Example: `!createchannel voice General VC`.")
    @admin_only()
    async def createchannel(self, ctx: commands.Context, kind: str = "text", *, name: str):
        kind = kind.lower()
        if kind == "voice":
            channel = await ctx.guild.create_voice_channel(self._safe_channel_name(name))
        elif kind == "category":
            channel = await ctx.guild.create_category(self._safe_channel_name(name))
        else:
            channel = await ctx.guild.create_text_channel(self._safe_channel_name(name))
        await ctx.send(f"Created channel: {channel.mention if hasattr(channel, 'mention') else channel.name}")

    @commands.command(name="deletechannel", help="Delete the current text channel or a tagged text channel.")
    @admin_only()
    async def deletechannel(self, ctx: commands.Context, channel: discord.TextChannel = None):
        target = channel or (ctx.channel if isinstance(ctx.channel, discord.TextChannel) else None)
        if not target:
            await ctx.send("Use that in the text channel you want removed or mention a text channel.")
            return
        name = target.name
        await ctx.send(f"Deleting **{name}**.")
        await target.delete(reason=f"Deleted by {ctx.author}")

    @commands.command(name="renametext", aliases=["renamechannel"], help="Rename a text channel.")
    @admin_only()
    async def renametext(self, ctx: commands.Context, channel: discord.TextChannel, *, new_name: str):
        safe_name = self._safe_channel_name(new_name).lower().replace(" ", "-")
        await channel.edit(name=safe_name, reason=f"Renamed by {ctx.author}")
        await ctx.send(f"Renamed text channel to {channel.mention}.")

    @commands.command(name="movetext", aliases=["textcategory"], help="Move a text channel into a category.")
    @admin_only()
    async def movetext(self, ctx: commands.Context, channel: discord.TextChannel, category: discord.CategoryChannel):
        await channel.edit(category=category, reason=f"Moved by {ctx.author}")
        await ctx.send(f"Moved {channel.mention} into **{category.name}**.")

    @commands.command(name="clonechannel", help="Clone a text channel, optionally with a new name.")
    @admin_only()
    async def clonechannel(self, ctx: commands.Context, channel: discord.TextChannel, *, new_name: str = ""):
        clone = await channel.clone(name=self._safe_channel_name(new_name).lower().replace(" ", "-") if new_name else None, reason=f"Cloned by {ctx.author}")
        await ctx.send(f"Cloned {channel.mention} into {clone.mention}.")

    @commands.command(name="channelposition", help="Set the position of a text channel.")
    @admin_only()
    async def channelposition(self, ctx: commands.Context, channel: discord.TextChannel, position: int):
        if position < 0:
            raise commands.CommandError("Position must be zero or greater.")
        await channel.edit(position=position, reason=f"Reordered by {ctx.author}")
        await ctx.send(f"Moved {channel.mention} to position `{position}`.")

    @commands.command(name="channeltopic", aliases=["settopic"], help="Set a text channel topic.")
    @admin_only()
    async def channeltopic(self, ctx: commands.Context, channel: discord.TextChannel, *, topic: str):
        await channel.edit(topic=shorten(topic, 1024), reason=f"Topic updated by {ctx.author}")
        await ctx.send(f"Updated the topic for {channel.mention}.")

    @commands.command(name="rolelock", help="Block a role from sending messages in a text channel.")
    @admin_only()
    async def rolelock(self, ctx: commands.Context, channel: discord.TextChannel, role: discord.Role):
        self._assert_manageable_role(ctx, role)
        overwrite = channel.overwrites_for(role)
        overwrite.send_messages = False
        await channel.set_permissions(role, overwrite=overwrite)
        await ctx.send(f"Locked {role.mention} in {channel.mention}.")

    @commands.command(name="roleunlock", help="Restore a role's send permission in a text channel.")
    @admin_only()
    async def roleunlock(self, ctx: commands.Context, channel: discord.TextChannel, role: discord.Role):
        self._assert_manageable_role(ctx, role)
        overwrite = channel.overwrites_for(role)
        overwrite.send_messages = None
        await channel.set_permissions(role, overwrite=overwrite)
        await ctx.send(f"Unlocked {role.mention} in {channel.mention}.")

    @commands.command(name="createrole", help="Create a role. Optional color hex is supported.")
    @admin_only()
    async def createrole(self, ctx: commands.Context, name: str, color_hex: str = None):
        color = discord.Color.default()
        if color_hex:
            with contextlib.suppress(ValueError):
                color = discord.Color(int(color_hex.replace("#", ""), 16))
        role = await ctx.guild.create_role(name=name, color=color)
        await ctx.send(f"Created role {role.mention}.")

    @commands.command(name="deleterole", help="Delete a role.")
    @admin_only()
    async def deleterole(self, ctx: commands.Context, role: discord.Role):
        self._assert_manageable_role(ctx, role)
        name = role.name
        await role.delete(reason=f"Deleted by {ctx.author}")
        await ctx.send(f"Deleted role **{name}**.")

    @commands.command(name="renamerole", help="Rename a role.")
    @admin_only()
    async def renamerole(self, ctx: commands.Context, role: discord.Role, *, new_name: str):
        self._assert_manageable_role(ctx, role)
        updated_name = normalize_text(new_name)[:100]
        before = role.name
        await role.edit(name=updated_name, reason=f"Renamed by {ctx.author}")
        await ctx.send(f"Renamed role **{before}** to **{updated_name}**.")

    @commands.command(name="giverole", aliases=["addrole"], help="Assign a role to a member.")
    @admin_only()
    async def giverole(self, ctx: commands.Context, member: discord.Member, role: discord.Role):
        self._assert_manageable_role(ctx, role)
        await member.add_roles(role, reason=f"Role assigned by {ctx.author}")
        await ctx.send(f"Gave {role.mention} to {member.mention}.")

    @commands.command(name="removerole", aliases=["takerole"], help="Remove a role from a member.")
    @admin_only()
    async def removerole(self, ctx: commands.Context, member: discord.Member, role: discord.Role):
        self._assert_manageable_role(ctx, role)
        await member.remove_roles(role, reason=f"Role removed by {ctx.author}")
        await ctx.send(f"Removed {role.mention} from {member.mention}.")

    @commands.command(name="rolecolor", help="Change a role color with a hex code like `#ff8800`.")
    @admin_only()
    async def rolecolor(self, ctx: commands.Context, role: discord.Role, color_hex: str):
        self._assert_manageable_role(ctx, role)
        try:
            color = discord.Color(int(color_hex.replace("#", ""), 16))
        except ValueError as exc:
            raise commands.CommandError("Use a valid hex color like `#ff8800`.") from exc
        await role.edit(color=color, reason=f"Role color changed by {ctx.author}")
        await ctx.send(f"Updated color for {role.mention}.")

    @commands.command(name="roleprops", help="Set whether a role is hoisted and mentionable. Use `!roleprops @role true false`.")
    @admin_only()
    async def roleprops(self, ctx: commands.Context, role: discord.Role, hoist: bool, mentionable: bool):
        self._assert_manageable_role(ctx, role)
        await role.edit(hoist=hoist, mentionable=mentionable, reason=f"Role properties updated by {ctx.author}")
        await ctx.send(f"Updated {role.mention}: hoist={hoist}, mentionable={mentionable}.")

    @commands.command(name="createvoice", aliases=["makevoice"], help="Create a voice channel.")
    @admin_only()
    async def createvoice(self, ctx: commands.Context, *, name: str):
        channel = await ctx.guild.create_voice_channel(self._safe_channel_name(name), reason=f"Created by {ctx.author}")
        await ctx.send(f"Created voice channel {channel.mention}.")

    @commands.command(name="deletevoice", help="Delete a voice channel.")
    @admin_only()
    async def deletevoice(self, ctx: commands.Context, channel: discord.VoiceChannel):
        name = channel.name
        await channel.delete(reason=f"Deleted by {ctx.author}")
        await ctx.send(f"Deleted voice channel **{name}**.")

    @commands.command(name="renamevoice", help="Rename a voice channel.")
    @admin_only()
    async def renamevoice(self, ctx: commands.Context, channel: discord.VoiceChannel, *, new_name: str):
        await channel.edit(name=self._safe_channel_name(new_name), reason=f"Renamed by {ctx.author}")
        await ctx.send(f"Renamed voice channel to **{channel.name}**.")

    @commands.command(name="voicecap", help="Set a voice channel user limit. Use `0` for no limit.")
    @admin_only()
    async def voicecap(self, ctx: commands.Context, channel: discord.VoiceChannel, limit: int):
        if limit < 0 or limit > 99:
            raise commands.CommandError("Voice channel user limit must be between 0 and 99.")
        await channel.edit(user_limit=limit, reason=f"Voice cap changed by {ctx.author}")
        await ctx.send(f"Set user limit for **{channel.name}** to `{limit}`.")

    @commands.command(name="voicebitrate", help="Set a voice channel bitrate in kbps.")
    @admin_only()
    async def voicebitrate(self, ctx: commands.Context, channel: discord.VoiceChannel, bitrate_kbps: int):
        bitrate = bitrate_kbps * 1000
        if bitrate < 8000:
            raise commands.CommandError("Bitrate must be at least 8 kbps.")
        await channel.edit(bitrate=bitrate, reason=f"Voice bitrate changed by {ctx.author}")
        await ctx.send(f"Set bitrate for **{channel.name}** to `{bitrate_kbps}` kbps.")

    @commands.command(name="voicecategory", help="Move a voice channel into a category.")
    @admin_only()
    async def voicecategory(self, ctx: commands.Context, channel: discord.VoiceChannel, category: discord.CategoryChannel):
        await channel.edit(category=category, reason=f"Voice channel reorganized by {ctx.author}")
        await ctx.send(f"Moved **{channel.name}** into **{category.name}**.")

    @commands.command(name="voiceposition", help="Set the position of a voice channel in the server list.")
    @admin_only()
    async def voiceposition(self, ctx: commands.Context, channel: discord.VoiceChannel, position: int):
        if position < 0:
            raise commands.CommandError("Position must be zero or greater.")
        await channel.edit(position=position, reason=f"Voice channel reordered by {ctx.author}")
        await ctx.send(f"Moved **{channel.name}** to position `{position}`.")

    @commands.command(name="voiceperm", help="Lock or unlock a voice channel for @everyone. Use `connect on` or `connect off`.")
    @admin_only()
    async def voiceperm(self, ctx: commands.Context, channel: discord.VoiceChannel, setting: str):
        lowered = normalize_text(setting).lower()
        if lowered not in {"connect on", "connect off", "on", "off", "allow", "deny"}:
            raise commands.CommandError("Use `on`/`allow` or `off`/`deny`.")
        overwrite = channel.overwrites_for(ctx.guild.default_role)
        overwrite.connect = lowered in {"connect on", "on", "allow"}
        await channel.set_permissions(ctx.guild.default_role, overwrite=overwrite)
        state = "allowed" if overwrite.connect else "blocked"
        await ctx.send(f"Voice connect is now {state} for @everyone in **{channel.name}**.")

    @commands.command(name="ticketpanel", help="Post the ticket panel.")
    @admin_only()
    async def ticketpanel(self, ctx: commands.Context):
        embed = discord.Embed(title="Support Tickets", description="Press the button below to open a ticket.", color=discord.Color.green())
        await ctx.send(embed=embed, view=TicketView(self.bot))

    @commands.command(name="closeticket", help="Close the current ticket channel.")
    @admin_only()
    async def closeticket(self, ctx: commands.Context):
        if not isinstance(ctx.channel, discord.TextChannel) or not (ctx.channel.name.startswith("ticket-") or (ctx.channel.topic or "").startswith("ticket-owner:")):
            await ctx.send("Use this inside a ticket channel.")
            return
        await ctx.send("Closing ticket in 3 seconds.")
        await asyncio.sleep(3)
        await ctx.channel.delete(reason=f"Closed by {ctx.author}")

    @commands.command(name="reactionrole", help="Bind an emoji reaction on a message to a role. Use it in the channel containing the message.")
    @admin_only()
    async def reactionrole(self, ctx: commands.Context, message_id: int, emoji: str, role: discord.Role):
        if not isinstance(ctx.channel, discord.TextChannel):
            await ctx.send("Use that in a text channel.")
            return
        message = await ctx.channel.fetch_message(message_id)
        mapping = self.bot.store.reaction_roles.setdefault(str(message_id), {})
        mapping[str(emoji)] = role.id
        self.bot.store.save("reaction_roles")
        await message.add_reaction(emoji)
        await ctx.send(f"Reaction role linked: {emoji} -> {role.mention}")

    @commands.command(name="addcmd", help="Add a custom command. Example: `!addcmd rules Be respectful.`")
    @admin_only()
    async def addcmd(self, ctx: commands.Context, name: str, *, response: str):
        key = str(ctx.guild.id)
        self.bot.store.custom_commands.setdefault(key, {})
        self.bot.store.custom_commands[key][name.lower()] = response
        self.bot.store.save("custom_commands")
        await ctx.send(f"Custom command `!{name.lower()}` added.")

    @commands.command(name="delcmd", help="Delete a custom command.")
    @admin_only()
    async def delcmd(self, ctx: commands.Context, name: str):
        key = str(ctx.guild.id)
        commands_map = self.bot.store.custom_commands.setdefault(key, {})
        if name.lower() in commands_map:
            del commands_map[name.lower()]
            self.bot.store.save("custom_commands")
            await ctx.send(f"Custom command `!{name.lower()}` deleted.")
            return
        await ctx.send("That custom command does not exist.")

    @commands.command(name="listcmds", help="List custom commands for this server.")
    @admin_only()
    async def listcmds(self, ctx: commands.Context):
        commands_map = self.bot.store.custom_commands.get(str(ctx.guild.id), {})
        await ctx.send("Custom commands: " + (", ".join(f"`!{name}`" for name in sorted(commands_map)) if commands_map else "none"))

    @commands.command(name="giveaway", help="Start a giveaway. Example: `!giveaway 30m Nitro`.")
    @admin_only()
    async def giveaway(self, ctx: commands.Context, duration: str, *, prize: str):
        seconds = parse_time_spec(duration)
        if not seconds:
            await ctx.send("Use a duration like `30m`, `2h`, or `1d`.")
            return
        end_ts = time.time() + seconds
        embed = discord.Embed(title="Giveaway", description=f"Prize: **{prize}**\nReact with 🎉 to enter.\nEnds in {duration}.", color=discord.Color.purple())
        message = await ctx.send(embed=embed)
        await message.add_reaction("🎉")
        payload = {
            "guild_id": ctx.guild.id,
            "channel_id": ctx.channel.id,
            "host_id": ctx.author.id,
            "prize": prize,
            "end_ts": end_ts,
            "ended": False,
        }
        self.bot.store.giveaways[str(message.id)] = payload
        self.bot.store.save("giveaways")
        self.bot.giveaway_tasks[message.id] = asyncio.create_task(self.bot._wait_and_finish_giveaway(message.id, seconds))
        await ctx.send(f"Giveaway started for **{prize}**.")

    @commands.command(name="greroll", help="Reroll a giveaway by message ID.")
    @admin_only()
    async def greroll(self, ctx: commands.Context, message_id: int):
        payload = self.bot.store.giveaways.get(str(message_id))
        if not isinstance(payload, dict):
            await ctx.send("Giveaway not found.")
            return
        channel = ctx.guild.get_channel(payload["channel_id"])
        if not isinstance(channel, discord.TextChannel):
            await ctx.send("Giveaway channel no longer exists.")
            return
        message = await channel.fetch_message(message_id)
        reaction = discord.utils.get(message.reactions, emoji="🎉")
        if not reaction:
            await ctx.send("No entries found.")
            return
        users = []
        async for user in reaction.users():
            if not user.bot:
                users.append(user)
        if not users:
            await ctx.send("No valid entries found.")
            return
        winner = random.choice(users)
        await ctx.send(f"Reroll winner: {winner.mention} | Prize: **{payload['prize']}**")


class MusicCog(commands.Cog, name="Music"):
    def __init__(self, bot: SpringBot):
        self.bot = bot

    @commands.command(name="join", help="Join your current voice channel.")
    async def join(self, ctx: commands.Context):
        try:
            voice = await self.bot.music.ensure_voice(ctx)
        except commands.CommandError as exc:
            append_voice_debug(f"join command failed: {exc}")
            details = self.bot.music.diagnose_voice_compact(ctx)
            await ctx.send(f"{exc}\n```text\n{details}\n```")
            return
        await ctx.send(f"Connected to **{voice.channel.name}** and ready to play.")

    @commands.command(name="play", help="Queue and play a song from YouTube or a search term.")
    async def play(self, ctx: commands.Context, *, query: str):
        try:
            async with ctx.typing():
                track = await self.bot.music.enqueue(ctx, query)
        except commands.CommandError as exc:
            append_voice_debug(f"play command failed: {exc} | query={query}")
            details = self.bot.music.diagnose_voice_compact(ctx)
            await ctx.send(f"{exc}\n```text\n{details}\n```")
            return
        if track.get("started_now"):
            await ctx.send("Locked in. Loading your track now.")
            return
        await ctx.send(embed=build_track_embed(track, "Queued"))

    @commands.command(name="pause", help="Pause the current track.")
    async def pause(self, ctx: commands.Context):
        voice = ctx.guild.voice_client if ctx.guild else None
        if not voice or not voice.is_playing():
            await ctx.send("Nothing is playing.")
            return
        voice.pause()
        await ctx.send("Playback paused.")

    @commands.command(name="resume", help="Resume the paused track.")
    async def resume(self, ctx: commands.Context):
        voice = ctx.guild.voice_client if ctx.guild else None
        if not voice or not voice.is_paused():
            await ctx.send("Nothing is paused.")
            return
        voice.resume()
        await ctx.send("Playback resumed.")

    @commands.command(name="skip", help="Skip the current track.")
    async def skip(self, ctx: commands.Context):
        voice = ctx.guild.voice_client if ctx.guild else None
        if not voice or not voice.is_playing():
            await ctx.send("Nothing is playing.")
            return
        voice.stop()
        await ctx.send("Track skipped.")

    @commands.command(name="queue", help="Show the current music queue.")
    async def queue(self, ctx: commands.Context):
        await ctx.send(self.bot.music.describe_queue(ctx.guild.id))

    @commands.command(name="voicecheck", aliases=["musiccheck"], help="Show SpringBot voice diagnostics for your current channel.")
    async def voicecheck(self, ctx: commands.Context):
        await ctx.send(f"```text\n{self.bot.music.diagnose_voice(ctx)}\n```")

    @commands.command(name="voicelog", help="Show the latest local voice debug lines.")
    @admin_only()
    async def voicelog(self, ctx: commands.Context):
        if not VOICE_DEBUG_LOG.exists():
            await ctx.send("No voice debug log yet.")
            return
        lines = VOICE_DEBUG_LOG.read_text(encoding="utf-8", errors="replace").splitlines()[-12:]
        await ctx.send(f"```text\n" + "\n".join(lines) + "\n```")

    @commands.command(name="leave", aliases=["stopmusic", "leavevc"], help="Clear the queue and leave voice.")
    async def leave(self, ctx: commands.Context):
        message = await self.bot.music.stop_and_disconnect(ctx.guild)
        await ctx.send(message)

    @commands.command(name="setcookies", help="Attach a cookies.txt file to improve music source access.")
    @admin_only()
    async def setcookies(self, ctx: commands.Context):
        if not ctx.message.attachments:
            await ctx.send("Attach a `cookies.txt` file to this command message.")
            return
        attachment = ctx.message.attachments[0]
        content = (await attachment.read()).decode("utf-8", errors="replace")
        self.bot.store.paths["cookies"].write_text(content, encoding="utf-8")
        await ctx.send("Cookies file saved.")

    @commands.command(name="cookiestatus", help="Check whether a music cookies file is saved.")
    async def cookiestatus(self, ctx: commands.Context):
        path = self.bot.store.paths["cookies"]
        if path.exists():
            await ctx.send(f"Cookies file found at `{path}`.")
            return
        await ctx.send("No cookies file saved.")

    @commands.command(name="clearcookies", help="Delete the saved cookies file.")
    @admin_only()
    async def clearcookies(self, ctx: commands.Context):
        path = self.bot.store.paths["cookies"]
        if path.exists():
            path.unlink()
            await ctx.send("Cookies file cleared.")
            return
        await ctx.send("No cookies file was saved.")


class EconomyCog(commands.Cog, name="Economy"):
    def __init__(self, bot: SpringBot):
        self.bot = bot

    @commands.command(name="balance", aliases=["bal"], help="Show your coin balance.")
    async def balance(self, ctx: commands.Context, member: discord.Member = None):
        target = member or ctx.author
        coins = self.bot.store.get_economy(target.id)["coins"]
        await ctx.send(f"{target.display_name} has **{coins}** coins.")

    @commands.command(name="daily", help="Claim your daily coins.")
    async def daily(self, ctx: commands.Context):
        record = self.bot.store.get_economy(ctx.author.id)
        now = time.time()
        remaining = 86400 - (now - record.get("daily_ts", 0))
        if remaining > 0:
            await ctx.send(f"Daily already claimed. Try again in {format_duration(remaining)}.")
            return
        record["daily_ts"] = now
        record["coins"] += DAILY_AMOUNT
        self.bot.store.save("economy")
        await ctx.send(f"Daily claimed. You earned **{DAILY_AMOUNT}** coins.")

    @commands.command(name="work", help="Work for a random number of coins.")
    async def work(self, ctx: commands.Context):
        record = self.bot.store.get_economy(ctx.author.id)
        now = time.time()
        remaining = WORK_COOLDOWN - (now - record.get("work_ts", 0))
        if remaining > 0:
            await ctx.send(f"Work cooldown active. Try again in {format_duration(remaining)}.")
            return
        earned = random.randint(WORK_MIN, WORK_MAX)
        record["work_ts"] = now
        record["coins"] += earned
        self.bot.store.save("economy")
        await ctx.send(f"You worked hard and earned **{earned}** coins.")

    @commands.command(name="pay", help="Pay another member some of your coins.")
    async def pay(self, ctx: commands.Context, member: discord.Member, amount: int):
        if member.id == ctx.author.id:
            await ctx.send("Paying yourself is not the flex you think it is.")
            return
        if amount <= 0:
            await ctx.send("Use a positive amount.")
            return
        sender = self.bot.store.get_economy(ctx.author.id)
        if sender["coins"] < amount:
            await ctx.send("You do not have enough coins.")
            return
        sender["coins"] -= amount
        receiver = self.bot.store.get_economy(member.id)
        receiver["coins"] += amount
        self.bot.store.save("economy")
        await ctx.send(f"Transferred **{amount}** coins to {member.mention}.")

    @commands.command(name="richest", help="Show the richest members in this server.")
    async def richest(self, ctx: commands.Context):
        ranking = []
        for member in ctx.guild.members:
            if member.bot:
                continue
            ranking.append((self.bot.store.get_economy(member.id)["coins"], member.display_name))
        ranking.sort(reverse=True)
        lines = [f"{index}. {name} - {coins} coins" for index, (coins, name) in enumerate(ranking[:10], start=1)]
        await ctx.send("Richest members:\n" + ("\n".join(lines) if lines else "Nobody has coins yet."))


class LevelCog(commands.Cog, name="XP & Levels"):
    def __init__(self, bot: SpringBot):
        self.bot = bot

    @commands.command(name="rank", help="Show your rank card data.")
    async def rank(self, ctx: commands.Context, member: discord.Member = None):
        target = member or ctx.author
        record = self.bot.store.get_xp_record(ctx.guild.id, target.id)
        needed = self.bot.store.xp_for_level(record["level"])
        await ctx.send(
            f"{target.display_name} | Level **{record['level']}** | XP **{record['xp']} / {needed}**"
        )

    @commands.command(name="leaderboard", help="Show the top XP members in this server.")
    async def leaderboard(self, ctx: commands.Context):
        guild_data = self.bot.store.xp.get(str(ctx.guild.id), {})
        ranking = []
        for user_id, record in guild_data.items():
            member = ctx.guild.get_member(int(user_id))
            if member:
                score = record.get("level", 1) * 100000 + record.get("xp", 0)
                ranking.append((score, member.display_name, record))
        ranking.sort(reverse=True)
        lines = [
            f"{index}. {name} - Level {record.get('level', 1)} ({record.get('xp', 0)} XP)"
            for index, (_, name, record) in enumerate(ranking[:10], start=1)
        ]
        await ctx.send("Leaderboard:\n" + ("\n".join(lines) if lines else "No XP data yet."))


class FunCog(commands.Cog, name="Fun"):
    def __init__(self, bot: SpringBot):
        self.bot = bot
        self.jokes = [
            "Why do programmers prefer dark mode? Because light attracts bugs.",
            "I would tell you a UDP joke, but I do not know if you would get it.",
            "A SQL query walks into a bar, walks up to two tables, and asks: can I join you?",
            "There are 10 kinds of people: those who understand binary and those who do not.",
        ]

    @commands.command(name="8ball", help="Ask the magic 8-ball a question.")
    async def eight_ball(self, ctx: commands.Context, *, question: str):
        await ctx.send(f"Question: {question}\nAnswer: {random.choice(EIGHT_BALL_RESPONSES)}")

    @commands.command(name="coinflip", help="Flip a coin.")
    async def coinflip(self, ctx: commands.Context):
        await ctx.send(random.choice(["Heads.", "Tails."]))

    @commands.command(name="dice", help="Roll a die. Example: `!dice 20`.")
    async def dice(self, ctx: commands.Context, sides: int = 6):
        sides = max(2, min(sides, 1000))
        await ctx.send(f"You rolled **{random.randint(1, sides)}** on a d{sides}.")

    @commands.command(name="rps", help="Play rock paper scissors.")
    async def rps(self, ctx: commands.Context, choice: str):
        user_choice = normalize_text(choice).lower()
        if user_choice not in {"rock", "paper", "scissors"}:
            await ctx.send("Choose rock, paper, or scissors.")
            return
        bot_choice = random.choice(["rock", "paper", "scissors"])
        outcomes = {
            ("rock", "scissors"),
            ("paper", "rock"),
            ("scissors", "paper"),
        }
        if user_choice == bot_choice:
            result = "Tie."
        elif (user_choice, bot_choice) in outcomes:
            result = "You win."
        else:
            result = "You lose."
        await ctx.send(f"You: {user_choice}\nMe: {bot_choice}\n{result}")

    @commands.command(name="trivia", help="Start a trivia question. Answer by sending A, B, C, or D.")
    async def trivia(self, ctx: commands.Context):
        async with ctx.typing():
            payload = await asyncio.to_thread(self.bot.knowledge.fetch_trivia)
        if not payload:
            await ctx.send("Trivia service is sleeping on the job.")
            return
        self.bot.state.trivia_sessions[ctx.author.id] = payload
        lines = [f"{chr(65 + index)}. {option}" for index, option in enumerate(payload["options"])]
        await ctx.send(
            f"Trivia: {payload['question']}\nCategory: {payload['category']} | Difficulty: {payload['difficulty']}\n"
            + "\n".join(lines)
            + "\nReply with A, B, C, or D."
        )

    @commands.command(name="choose", help="Choose between options separated by `|` or commas.")
    async def choose(self, ctx: commands.Context, *, options: str):
        items = [normalize_text(item) for item in re.split(r"\s*\|\s*|\s*,\s*", options) if normalize_text(item)]
        if len(items) < 2:
            await ctx.send("Give me at least two options.")
            return
        await ctx.send(f"I choose: **{random.choice(items)}**")

    @commands.command(name="meme", help="Grab a meme without needing an API key.")
    async def meme(self, ctx: commands.Context):
        async with ctx.typing():
            meme = await asyncio.to_thread(self.bot.knowledge.fetch_meme)
        if not meme:
            await ctx.send("I couldn't pull a meme right now.")
            return
        embed = discord.Embed(title=shorten(meme["title"], 200), url=meme["link"], color=discord.Color.random())
        embed.set_image(url=meme["url"])
        footer = f"Ups: {meme['ups']}"
        if meme.get("subreddit"):
            footer += f" | r/{meme['subreddit']}"
        embed.set_footer(text=footer)
        await ctx.send(embed=embed)

    @commands.command(name="gif", help="Find a GIF without needing an API key.")
    async def gif(self, ctx: commands.Context, *, term: str):
        async with ctx.typing():
            result = await asyncio.to_thread(self.bot.knowledge.fetch_gif, term)
        if not result:
            await ctx.send("I couldn't find a GIF for that search right now.")
            return
        embed = discord.Embed(
            title=f"GIF: {shorten(result['title'], 200)}",
            description=f"Source: r/{result['subreddit']}" if result.get("subreddit") else "Source: public Reddit feed",
            url=result["item_url"] if result.get("item_url", "").startswith("http") else discord.Embed.Empty,
            color=discord.Color.orange(),
        )
        embed.set_image(url=result["url"])
        await ctx.send(embed=embed)

    @commands.command(name="joke", help="Tell a joke.")
    async def joke(self, ctx: commands.Context):
        await ctx.send(random.choice(self.jokes))

    @commands.command(name="poll", help="Create a poll. Use `question | option1 | option2`.")
    async def poll(self, ctx: commands.Context, *, text: str):
        parts = [normalize_text(part) for part in text.split("|") if normalize_text(part)]
        if len(parts) < 3:
            await ctx.send("Use `!poll Question | option 1 | option 2`.")
            return
        question, options = parts[0], parts[1:10]
        emoji_list = ["1️⃣", "2️⃣", "3️⃣", "4️⃣", "5️⃣", "6️⃣", "7️⃣", "8️⃣", "9️⃣"]
        lines = [f"{emoji_list[index]} {option}" for index, option in enumerate(options)]
        embed = discord.Embed(title="Poll", description=f"{question}\n\n" + "\n".join(lines), color=discord.Color.teal())
        message = await ctx.send(embed=embed)
        for emoji in emoji_list[: len(options)]:
            await message.add_reaction(emoji)

    @commands.command(name="roast", help="Roast a member or just get a roast line.")
    async def roast(self, ctx: commands.Context, member: discord.Member = None):
        if member:
            await ctx.send(f"{member.mention} {roast_line()}")
            return
        await ctx.send(roast_line())


class UtilityCog(commands.Cog, name="Utility"):
    def __init__(self, bot: SpringBot):
        self.bot = bot

    async def _send_reminder(self, channel: discord.abc.Messageable, user: discord.abc.User, delay: int, message: str):
        await asyncio.sleep(delay)
        with contextlib.suppress(discord.HTTPException):
            await channel.send(f"{user.mention} reminder: {message}")

    @commands.command(name="avatar", help="Show a user's avatar.")
    async def avatar(self, ctx: commands.Context, member: discord.Member = None):
        target = member or ctx.author
        await ctx.send(target.display_avatar.url)

    @commands.command(name="userinfo", help="Show information about a member.")
    async def userinfo(self, ctx: commands.Context, member: discord.Member = None):
        target = member or ctx.author
        embed = discord.Embed(title=str(target), color=discord.Color.blurple())
        embed.set_thumbnail(url=target.display_avatar.url)
        embed.add_field(name="ID", value=str(target.id), inline=False)
        embed.add_field(name="Joined", value=str(target.joined_at)[:19] if target.joined_at else "Unknown", inline=True)
        embed.add_field(name="Created", value=str(target.created_at)[:19], inline=True)
        embed.add_field(name="Top Role", value=target.top_role.mention if isinstance(target, discord.Member) and target.top_role else "None", inline=False)
        await ctx.send(embed=embed)

    @commands.command(name="serverinfo", help="Show information about the current server.")
    async def serverinfo(self, ctx: commands.Context):
        guild = ctx.guild
        embed = discord.Embed(title=guild.name, color=discord.Color.green())
        if guild.icon:
            embed.set_thumbnail(url=guild.icon.url)
        embed.add_field(name="Members", value=str(guild.member_count), inline=True)
        embed.add_field(name="Text Channels", value=str(len(guild.text_channels)), inline=True)
        embed.add_field(name="Voice Channels", value=str(len(guild.voice_channels)), inline=True)
        embed.add_field(name="Roles", value=str(len(guild.roles)), inline=True)
        embed.add_field(name="Owner", value=str(guild.owner), inline=True)
        embed.add_field(name="Created", value=str(guild.created_at)[:19], inline=True)
        await ctx.send(embed=embed)

    @commands.command(name="calc", help="Evaluate a basic math expression.")
    async def calc(self, ctx: commands.Context, *, expression: str):
        await ctx.send(f"Result: {safe_eval(expression)}")

    @commands.command(name="remind", help="Set a reminder. Example: `!remind 10m check printer queue`.")
    async def remind(self, ctx: commands.Context, duration: str, *, text: str):
        seconds = parse_time_spec(duration)
        if not seconds:
            await ctx.send("Use a duration like `10m`, `2h`, or `1d`.")
            return
        asyncio.create_task(self._send_reminder(ctx.channel, ctx.author, seconds, text))
        await ctx.send(f"Reminder set for {duration}.")

    @commands.command(name="afk", help="Mark yourself AFK with an optional reason.")
    async def afk(self, ctx: commands.Context, *, reason: str = "AFK"):
        self.bot.store.set_afk(ctx.guild.id, ctx.author.id, reason)
        await ctx.send(f"AFK set: {reason}")


def main():
    acquire_instance_lock(INSTANCE_LOCK_PATH)
    token = load_discord_token(ROOT_DIR)
    if not token:
        release_instance_lock()
        raise RuntimeError("No Discord token found. Use set_token.ps1 or set DISCORD_TOKEN.")
    bot = SpringBot()
    try:
        bot.run(token)
    finally:
        release_instance_lock()


if __name__ == "__main__":
    main()
