import os
import json
import asyncio
import urllib.request
import urllib.error
import urllib.parse
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
            "When discussing books, authors, countries, or regions, be factual and grounded. "
            "Keep replies clear, useful, and human."
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

    def shorten(self, text, limit=450):
        if not text:
            return "No summary available."
        text = " ".join(str(text).split())
        if len(text) <= limit:
            return text
        return text[:limit - 3] + "..."

    async def fetch_json(self, url, headers=None):
        headers = headers or {}
        request = urllib.request.Request(url, headers=headers, method="GET")

        def run_request():
            with urllib.request.urlopen(request, timeout=30) as response:
                return json.loads(response.read().decode("utf-8"))

        loop = asyncio.get_running_loop()
        try:
            return await loop.run_in_executor(None, run_request)
        except urllib.error.HTTPError as e:
            raise RuntimeError(f"HTTP {e.code} from source.")
        except urllib.error.URLError as e:
            raise RuntimeError(f"Connection error: {e.reason}")
        except Exception as e:
            raise RuntimeError(f"Request failed: {e}")

    def detect_book_request(self, text: str):
        lower = text.lower().strip()

        patterns = [
            "tell me about the book ",
            "what is the book ",
            "book summary of ",
            "summarize the book ",
            "who wrote ",
            "tell me about author ",
            "who is author ",
            "tell me about ",
        ]

        for p in patterns:
            if lower.startswith(p):
                return text[len(p):].strip()

        if " book " in lower or lower.startswith("book "):
            return text.replace("book", "", 1).strip()

        return None

    def detect_country_request(self, text: str):
        lower = text.lower().strip()

        patterns = [
            "tell me about ",
            "what do you know about ",
            "what is ",
            "where is ",
            "explain ",
            "what region is ",
            "what country is ",
        ]

        geo_words = [
            "country", "region", "capital", "population", "currency",
            "language", "subregion", "continent"
        ]

        if any(word in lower for word in geo_words):
            for p in patterns:
                if lower.startswith(p):
                    return text[len(p):].strip()

        return None

    async def lookup_book(self, query: str):
        encoded = urllib.parse.quote(query)
        google_url = f"https://www.googleapis.com/books/v1/volumes?q={encoded}&maxResults=3"
        data = await self.fetch_json(google_url)

        items = data.get("items", [])
        if not items:
            return None

        book = items[0]
        info = book.get("volumeInfo", {})

        title = info.get("title", "Unknown title")
        subtitle = info.get("subtitle", "")
        authors = ", ".join(info.get("authors", [])) or "Unknown"
        published = info.get("publishedDate", "Unknown")
        publisher = info.get("publisher", "Unknown")
        categories = ", ".join(info.get("categories", [])) or "Unknown"
        description = self.shorten(info.get("description", "No description available."), 500)
        info_link = info.get("infoLink") or info.get("previewLink") or "No link"

        return (
            f"**Book:** {title}"
            + (f" — {subtitle}" if subtitle else "")
            + "\n"
            f"**Author(s):** {authors}\n"
            f"**Published:** {published}\n"
            f"**Publisher:** {publisher}\n"
            f"**Categories:** {categories}\n"
            f"**Summary:** {description}\n"
            f"**Source:** Google Books\n"
            f"{info_link}"
        )

    async def lookup_author(self, query: str):
        encoded = urllib.parse.quote(query)
        url = f"https://openlibrary.org/search/authors.json?q={encoded}"
        data = await self.fetch_json(url)

        docs = data.get("docs", [])
        if not docs:
            return None

        author = docs[0]
        name = author.get("name", "Unknown")
        top_work = author.get("top_work", "Unknown")
        work_count = author.get("work_count", "Unknown")
        birth_date = author.get("birth_date", "Unknown")
        top_subjects = ", ".join(author.get("top_subjects", [])[:5]) or "Unknown"
        key = author.get("key", "")
        link = f"https://openlibrary.org{key}" if key else "No profile link"

        return (
            f"**Author:** {name}\n"
            f"**Birth date:** {birth_date}\n"
            f"**Top work:** {top_work}\n"
            f"**Work count:** {work_count}\n"
            f"**Common subjects:** {top_subjects}\n"
            f"**Source:** Open Library\n"
            f"{link}"
        )

    async def lookup_country(self, query: str):
        encoded = urllib.parse.quote(query)
        restcountries_url = f"https://restcountries.com/v3.1/name/{encoded}"
        country_data = await self.fetch_json(restcountries_url)

        if not isinstance(country_data, list) or not country_data:
            return None

        country = country_data[0]

        name = country.get("name", {}).get("common", "Unknown")
        official = country.get("name", {}).get("official", "Unknown")
        capital = ", ".join(country.get("capital", [])) or "Unknown"
        population = country.get("population", "Unknown")
        region = country.get("region", "Unknown")
        subregion = country.get("subregion", "Unknown")

        languages_obj = country.get("languages", {})
        languages = ", ".join(languages_obj.values()) if languages_obj else "Unknown"

        currencies_obj = country.get("currencies", {})
        if currencies_obj:
            currency_names = []
            for _, value in currencies_obj.items():
                currency_names.append(value.get("name", "Unknown currency"))
            currencies = ", ".join(currency_names)
        else:
            currencies = "Unknown"

        cca2 = country.get("cca2", "")
        world_bank_text = ""
        if cca2:
            wb_url = f"https://api.worldbank.org/v2/country/{cca2}?format=json"
            try:
                wb_data = await self.fetch_json(wb_url)
                if isinstance(wb_data, list) and len(wb_data) > 1 and wb_data[1]:
                    wb = wb_data[1][0]
                    wb_region = wb.get("region", {}).get("value", "Unknown")
                    wb_admin = wb.get("adminregion", {}).get("value", "Unknown")
                    wb_income = wb.get("incomeLevel", {}).get("value", "Unknown")
                    world_bank_text = (
                        f"\n**World Bank region:** {wb_region}"
                        f"\n**Admin region:** {wb_admin}"
                        f"\n**Income level:** {wb_income}"
                    )
            except Exception:
                world_bank_text = "\n**World Bank region:** Unavailable right now."

        return (
            f"**Country/Region Entry:** {name}\n"
            f"**Official name:** {official}\n"
            f"**Capital:** {capital}\n"
            f"**Population:** {population}\n"
            f"**Region:** {region}\n"
            f"**Subregion:** {subregion}\n"
            f"**Languages:** {languages}\n"
            f"**Currencies:** {currencies}"
            f"{world_bank_text}\n"
            f"**Sources:** REST Countries + World Bank"
        )

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
        lower = user_text.lower().strip()

        try:
            async with message.channel.typing():
                if lower.startswith("who wrote "):
                    author_query = user_text[10:].strip()
                    reply = await self.lookup_author(author_query)
                    if not reply:
                        reply = "I could not find a reliable author result for that."
                elif any(x in lower for x in ["book", "novel", "author", "writer", "published by"]):
                    book_query = self.detect_book_request(user_text) or user_text
                    reply = await self.lookup_book(book_query)
                    if not reply:
                        reply = await self.lookup_author(book_query)
                    if not reply:
                        reply = "I could not find a reliable book or author result for that."
                elif any(x in lower for x in ["country", "region", "capital", "population", "currency", "subregion", "language"]):
                    country_query = self.detect_country_request(user_text) or user_text
                    reply = await self.lookup_country(country_query)
                    if not reply:
                        reply = "I could not find a reliable country or region result for that."
                else:
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
            "The bot also replies when mentioned.\n"
            "Books use Google Books / Open Library.\n"
            "Countries and regions use REST Countries / World Bank."
        )


async def setup(bot):
    await bot.add_cog(Chat(bot))