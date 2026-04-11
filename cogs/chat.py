import os
import json
import math
import re
import random
from discord.ext import commands


class Chat(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.state_file = "chat_settings.json"
        self.state = self.load_state()

    def load_state(self):
        if not os.path.exists(self.state_file):
            return {"chat_channel_id": 0, "autochat": False}

        try:
            with open(self.state_file, "r", encoding="utf-8") as f:
                data = json.load(f)

            if not isinstance(data, dict):
                return {"chat_channel_id": 0, "autochat": False}

            data.setdefault("chat_channel_id", 0)
            data.setdefault("autochat", False)
            return data
        except Exception:
            return {"chat_channel_id": 0, "autochat": False}

    def save_state(self):
        with open(self.state_file, "w", encoding="utf-8") as f:
            json.dump(self.state, f, indent=2)

    def should_reply(self, message):
        if message.author.bot:
            return False

        content = (message.content or "").strip()
        if not content:
            return False

        if content.startswith(tuple(["!", "?", ".", "/"])):
            return False

        if self.bot.user in message.mentions:
            return True

        if self.state.get("autochat", False):
            chat_channel_id = int(self.state.get("chat_channel_id", 0) or 0)
            if chat_channel_id and message.channel.id == chat_channel_id:
                return True

        return False

    def clean_content(self, message):
        text = message.content or ""
        if self.bot.user:
            text = text.replace(f"<@{self.bot.user.id}>", "")
            text = text.replace(f"<@!{self.bot.user.id}>", "")
        return text.strip()

    def try_math(self, text):
        safe = text.lower().strip()
        safe = safe.replace("^", "**")

        if not re.fullmatch(r"[0-9\.\+\-\*\/\(\)\%\s\*]+", safe):
            return None

        try:
            result = eval(safe, {"__builtins__": {}}, {})
            return f"The answer is **{result}**."
        except Exception:
            return None

    def get_response(self, text):
        lower = text.lower().strip()

        math_result = self.try_math(lower)
        if math_result:
            return math_result

        if lower in ["hi", "hello", "hey", "yo", "sup", "what's up", "whats up"]:
            return random.choice([
                "Hey. What do you need?",
                "Yo. I'm here.",
                "What's up?",
                "Hey, talk to me."
            ])

        if "who are you" in lower:
            return "I'm SpringBot. I can chat normally, run commands, help with tech, math, study topics, and more."

        if "what can you do" in lower or "what do you do" in lower:
            return (
                "I can chat normally, do math, help with tech and networking, explain cybersecurity topics, "
                "run moderation commands, and handle music and news features."
            )

        if "help" == lower or "help me" in lower:
            return (
                "You can talk to me normally here, or use commands like "
                "`!mathhelp`, `!musichelp`, `!newshelp`, `!dns`, `!packet`, `!aihistory`, and more."
            )

        if "math" in lower:
            return "I can do math. Try talking to me naturally like `2+2` or use `!mathhelp` for the full list."

        if "music" in lower:
            return "For music, use commands like `!join`, `!play`, `!pause`, `!resume`, and `!musichelp`."

        if "news" in lower:
            return "For news, use `!newshelp`, `!newstest`, and `!setnewschannel`."

        if "dns" in lower:
            return "DNS translates names like google.com into IP addresses so devices can find the right server."

        if "dhcp" in lower:
            return "DHCP automatically gives devices network settings like IP address, subnet mask, gateway, and DNS."

        if "tcp" in lower and "udp" in lower:
            return "TCP is reliable and connection-based. UDP is faster and connectionless."

        if "packet" in lower:
            return "A packet is a small piece of data sent across a network. It usually contains a header and a payload."

        if "osi" in lower:
            return "The OSI model explains how data moves through layers. The ones people usually care about most are layers 2, 3, and 4."

        if "crowdstrike" in lower:
            return "The CrowdStrike issue was caused by an input mismatch that triggered an out-of-bounds read and crashed systems."

        if "ai history" in lower or "history of ai" in lower:
            return "AI history includes the Turing Test, ELIZA, neural networks, AI winters, the Transformer breakthrough, and the GPT timeline."

        if "gpt" in lower:
            return "GPT models grew from GPT-1 to GPT-2 to GPT-3, and ChatGPT made the model feel much more conversational."

        if "thank you" in lower or "thanks" in lower:
            return random.choice([
                "No problem.",
                "You got it.",
                "Anytime.",
                "Glad to help."
            ])

        if "bye" in lower or "goodbye" in lower:
            return random.choice([
                "Later.",
                "Alright, see you.",
                "Catch you later."
            ])

        return random.choice([
            "I hear you. Be more specific and I’ll help better.",
            "Say a little more.",
            "I can help with that. Ask me directly.",
            "Try asking me about math, tech, networking, cybersecurity, music, or news.",
            "I’m listening."
        ])

    @commands.Cog.listener()
    async def on_message(self, message):
        if not self.should_reply(message):
            return

        text = self.clean_content(message)
        if not text:
            return

        response = self.get_response(text)
        if response:
            await message.channel.send(response)

    @commands.command(help="Set this channel as the normal conversation channel.")
    @commands.has_permissions(manage_guild=True)
    async def setchat(self, ctx):
        self.state["chat_channel_id"] = ctx.channel.id
        self.save_state()
        await ctx.send(f"This channel is now the normal chat channel.\nChannel ID: **{ctx.channel.id}**")

    @commands.command(help="Turn normal no-command chat on or off in the saved chat channel.")
    @commands.has_permissions(manage_guild=True)
    async def autochat(self, ctx, mode: str):
        mode = mode.lower().strip()

        if mode not in ["on", "off"]:
            await ctx.send("Use `!autochat on` or `!autochat off`.")
            return

        self.state["autochat"] = mode == "on"
        self.save_state()

        await ctx.send(f"Auto chat is now **{mode.upper()}**.")

    @commands.command(help="Show current chat settings.")
    async def chatstatus(self, ctx):
        channel_id = self.state.get("chat_channel_id", 0)
        autochat = self.state.get("autochat", False)

        await ctx.send(
            f"Chat channel ID: **{channel_id}**\n"
            f"Auto chat: **{autochat}**\n"
            "The bot will also reply when mentioned."
        )

    @commands.command(help="Show chat commands.")
    async def chathelp(self, ctx):
        await ctx.send(
            "**Chat Commands**\n"
            "!setchat - Set this channel as the no-command chat channel\n"
            "!autochat on - Enable normal talking in that channel\n"
            "!autochat off - Disable normal talking in that channel\n"
            "!chatstatus - Show current chat settings\n"
            "!chathelp - Show chat commands\n\n"
            "The bot also replies when mentioned anywhere."
        )


async def setup(bot):
    await bot.add_cog(Chat(bot))