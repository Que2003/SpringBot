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

        self.openrouter_api_key = (os.getenv("OPENROUTER_API_KEY") or "").strip()
        self.openrouter_model = (os.getenv("OPENROUTER_MODEL") or "openrouter/free").strip()

        self.system_instructions = (
            "You are SpringBot, a highly intelligent Discord assistant. "
            "Be warm, conversational, supportive, and insightful. "
            "Talk like a best friend when the user is casual, like a professor when they want to learn, "
            "and like a calm supportive coach when they are stressed. "
            "Be natural, not robotic. "
            "Do not claim to be a licensed therapist, doctor, or lawyer. "
            "You may be emotionally supportive, but if a user seems in crisis or at risk of self-harm, "
            "urge them to contact emergency services or a crisis line right away. "
            "Keep replies clear, helpful, and human."
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

    def trim_memory(self, history, max_items=12):
        return history[-max_items:]

    async def query_openrouter(self, user_text, memory_key):
        if not self.openrouter_api_key:
            raise RuntimeError("Missing OPENROUTER_API_KEY in Railway variables.")

        memory = self.state.get("memory", {})
        history = memory.get(memory_key, [])

        messages = [{"role": "system", "content": self.system_instructions}]
        messages.extend(history)
        messages.append({"role": "user", "content": user_text})

        payload = {
            "model": self.openrouter_model,
            "messages": messages,
            "temperature": 0.8,
            "max_tokens": 350
        }

        body = json.dumps(payload).encode("utf-8")
        headers = {
            "Authorization": f"Bearer {self.openrouter_api_key}",
            "Content-Type": "application/json",
            "HTTP-Referer": "https://springbot.local",
            "X-Title": "SpringBot"
        }

        request = urllib.request.Request(
            "https://openrouter.ai/api/v1/chat/completions",
            data=body,
            headers=headers,
            method="POST"
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
            raise RuntimeError(f"OpenRouter HTTP {e.code}: {details}")
        except urllib.error.URLError as e:
            raise RuntimeError(f"OpenRouter connection error: {e.reason}")
        except Exception as e:
            raise RuntimeError(f"OpenRouter request failed: {e}")

        choices = data.get("choices", [])
        if not choices:
            raise RuntimeError("No response choices returned.")

        reply = choices[0].get("message", {}).get("content", "").strip()
        if not reply:
            raise RuntimeError("OpenRouter returned an empty reply.")

        history.append({"role": "user", "content": user_text})
        history.append({"role": "assistant", "content": reply})
        memory[memory_key] = self.trim_memory(history)
        self.state["memory"] = memory
        self.save_state()

        return reply

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
                reply = await self.query_openrouter(user_text, memory_key)
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
        await ctx.send(f"This channel is now the AI chat channel.\nChannel ID: **{ctx.channel.id}**")

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
        key_present = bool(self.openrouter_api_key)

        await ctx.send(
            f"Chat channel ID: **{channel_id}**\n"
            f"Auto chat: **{autochat}**\n"
            f"OpenRouter key present: **{key_present}**\n"
            f"Model: **{self.openrouter_model}**\n"
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