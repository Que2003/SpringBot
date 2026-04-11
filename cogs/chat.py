import os
import json
import asyncio
import urllib.request
import urllib.error
from discord.ext import commands


class Chat(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.state_file = "chat_settings.json"
        self.state = self.load_state()

        self.openai_api_key = os.getenv("OPENAI_API_KEY", "").strip()
        self.openai_model = os.getenv("OPENAI_MODEL", "gpt-4.1-mini").strip()

        self.system_instructions = (
            "You are SpringBot, a highly intelligent Discord assistant. "
            "Be warm, emotionally supportive, conversational, and insightful. "
            "Speak like a best friend when the user is casual, like a professor when they want learning, "
            "and like a calm supportive coach when they are stressed. "
            "Be helpful, direct, and easy to understand. "
            "You can explain things simply or deeply depending on the user's tone. "
            "Do not be robotic. "
            "Do not claim to be a licensed therapist, doctor, lawyer, or other professional. "
            "You may be emotionally supportive, but if a user seems in crisis or at risk of self-harm, "
            "encourage them to contact emergency services or a crisis line immediately. "
            "Keep replies natural and useful. "
            "Remember recent conversation context when available."
        )

    def load_state(self):
        default_state = {
            "chat_channel_id": 0,
            "autochat": False,
            "memory": {}
        }

        if not os.path.exists(self.state_file):
            return default_state

        try:
            with open(self.state_file, "r", encoding="utf-8") as f:
                data = json.load(f)

            if not isinstance(data, dict):
                return default_state

            data.setdefault("chat_channel_id", 0)
            data.setdefault("autochat", False)
            data.setdefault("memory", {})
            return data
        except Exception:
            return default_state

    def save_state(self):
        with open(self.state_file, "w", encoding="utf-8") as f:
            json.dump(self.state, f, indent=2)

    def get_memory_key(self, message):
        guild_id = message.guild.id if message.guild else 0
        channel_id = message.channel.id
        user_id = message.author.id
        return f"{guild_id}:{channel_id}:{user_id}"

    def should_reply(self, message):
        if message.author.bot:
            return False

        content = (message.content or "").strip()
        if not content:
            return False

        if content.startswith(("!", "/", ".", "?")):
            return False

        if self.bot.user and self.bot.user in message.mentions:
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

    def extract_response_text(self, data):
        if isinstance(data.get("output_text"), str) and data["output_text"].strip():
            return data["output_text"].strip()

        output = data.get("output", [])
        for item in output:
            if item.get("type") == "message":
                content = item.get("content", [])
                for part in content:
                    if part.get("type") == "output_text":
                        text = part.get("text", "").strip()
                        if text:
                            return text

        return "I’m here, but I couldn’t generate a proper reply."

    async def query_openai(self, user_text, memory_key, safety_identifier):
        if not self.openai_api_key:
            raise RuntimeError("Missing OPENAI_API_KEY in Railway variables.")

        previous_response_id = self.state.get("memory", {}).get(memory_key)

        payload = {
            "model": self.openai_model,
            "instructions": self.system_instructions,
            "input": user_text,
            "temperature": 0.8,
            "max_output_tokens": 350,
            "store": True,
            "safety_identifier": str(safety_identifier),
        }

        if previous_response_id:
            payload["previous_response_id"] = previous_response_id

        body = json.dumps(payload).encode("utf-8")
        headers = {
            "Authorization": f"Bearer {self.openai_api_key}",
            "Content-Type": "application/json",
        }

        request = urllib.request.Request(
            "https://api.openai.com/v1/responses",
            data=body,
            headers=headers,
            method="POST",
        )

        def run_request():
            with urllib.request.urlopen(request, timeout=45) as response:
                return json.loads(response.read().decode("utf-8"))

        loop = asyncio.get_running_loop()
        try:
            data = await loop.run_in_executor(None, run_request)
        except urllib.error.HTTPError as e:
            try:
                details = e.read().decode("utf-8")
            except Exception:
                details = str(e)
            raise RuntimeError(f"OpenAI HTTP {e.code}: {details}")
        except urllib.error.URLError as e:
            raise RuntimeError(f"OpenAI connection error: {e.reason}")
        except Exception as e:
            raise RuntimeError(f"OpenAI request failed: {e}")

        response_id = data.get("id")
        if response_id:
            self.state["memory"][memory_key] = response_id
            self.save_state()

        return self.extract_response_text(data)

    @commands.Cog.listener()
    async def on_message(self, message):
        if not self.should_reply(message):
            return

        user_text = self.clean_content(message)
        if not user_text:
            return

        memory_key = self.get_memory_key(message)

        try:
            async with message.channel.typing():
                reply = await self.query_openai(
                    user_text=user_text,
                    memory_key=memory_key,
                    safety_identifier=message.author.id,
                )
        except Exception as e:
            await message.channel.send(f"Chat failed: {e}")
            return

        if len(reply) > 1900:
            reply = reply[:1900] + "..."

        await message.channel.send(reply)

    @commands.command(help="Set this channel as the normal AI chat channel.")
    @commands.has_permissions(manage_guild=True)
    async def setchat(self, ctx):
        self.state["chat_channel_id"] = ctx.channel.id
        self.save_state()
        await ctx.send(
            f"This channel is now the AI chat channel.\n"
            f"Channel ID: **{ctx.channel.id}**"
        )

    @commands.command(help="Turn no-command AI chat on or off in the saved chat channel.")
    @commands.has_permissions(manage_guild=True)
    async def autochat(self, ctx, mode: str):
        mode = mode.lower().strip()

        if mode not in ["on", "off"]:
            await ctx.send("Use `!autochat on` or `!autochat off`.")
            return

        self.state["autochat"] = (mode == "on")
        self.save_state()
        await ctx.send(f"Auto chat is now **{mode.upper()}**.")

    @commands.command(help="Show current AI chat settings.")
    async def chatstatus(self, ctx):
        channel_id = self.state.get("chat_channel_id", 0)
        autochat = self.state.get("autochat", False)
        model = self.openai_model
        key_present = bool(self.openai_api_key)

        await ctx.send(
            f"Chat channel ID: **{channel_id}**\n"
            f"Auto chat: **{autochat}**\n"
            f"OpenAI key present: **{key_present}**\n"
            f"Model: **{model}**\n"
            "The bot will also reply when mentioned."
        )

    @commands.command(help="Clear your AI conversation memory in this channel.")
    async def clearchat(self, ctx):
        memory_key = f"{ctx.guild.id if ctx.guild else 0}:{ctx.channel.id}:{ctx.author.id}"

        if memory_key in self.state.get("memory", {}):
            del self.state["memory"][memory_key]
            self.save_state()
            await ctx.send("Your chat memory for this channel has been cleared.")
            return

        await ctx.send("There was no saved chat memory for you in this channel.")

    @commands.command(help="Show chat commands.")
    async def chathelp(self, ctx):
        await ctx.send(
            "**AI Chat Commands**\n"
            "!setchat - Set this channel as the AI chat channel\n"
            "!autochat on - Enable no-command AI chat in that channel\n"
            "!autochat off - Disable no-command AI chat\n"
            "!chatstatus - Show AI chat settings\n"
            "!clearchat - Clear your memory in this channel\n"
            "!chathelp - Show this list\n\n"
            "You can also mention the bot anywhere to talk normally."
        )


async def setup(bot):
    await bot.add_cog(Chat(bot))