import os
import json
import asyncio
import urllib.request
import urllib.error
from datetime import datetime, timezone

import discord
from discord.ext import commands, tasks


class News(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.api_key = (os.getenv("TAVILY_API_KEY") or "").strip()
        self.state_file = "news_state.json"
        self.state = self.load_state()
        self.live_news_loop.start()

    def cog_unload(self):
        self.live_news_loop.cancel()

    def default_state(self):
        return {
            "news_channel_id": 0,
            "live_news_enabled": False,
            "news_query": "breaking news",
            "posted_urls": []
        }

    def load_state(self):
        if not os.path.exists(self.state_file):
            return self.default_state()

        try:
            with open(self.state_file, "r", encoding="utf-8") as f:
                data = json.load(f)

            default = self.default_state()
            for key, value in default.items():
                data.setdefault(key, value)

            if not isinstance(data.get("posted_urls"), list):
                data["posted_urls"] = []

            data["posted_urls"] = data["posted_urls"][-300:]
            return data
        except Exception:
            return self.default_state()

    def save_state(self):
        self.state["posted_urls"] = self.state.get("posted_urls", [])[-300:]
        with open(self.state_file, "w", encoding="utf-8") as f:
            json.dump(self.state, f, indent=2)

    async def tavily_news_search(self, query, max_results=5):
        if not self.api_key:
            raise RuntimeError("Missing TAVILY_API_KEY in Railway variables.")

        payload = {
            "query": query,
            "topic": "news",
            "search_depth": "advanced",
            "max_results": max_results,
            "include_answer": "advanced",
            "include_favicon": False,
            "include_images": False,
        }

        body = json.dumps(payload).encode("utf-8")
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }

        request = urllib.request.Request(
            "https://api.tavily.com/search",
            data=body,
            headers=headers,
            method="POST"
        )

        def run_request():
            with urllib.request.urlopen(request, timeout=45) as response:
                return json.loads(response.read().decode("utf-8"))

        loop = asyncio.get_running_loop()
        try:
            return await loop.run_in_executor(None, run_request)
        except urllib.error.HTTPError as e:
            try:
                details = e.read().decode("utf-8")
            except Exception:
                details = str(e)
            raise RuntimeError(f"Tavily HTTP {e.code}: {details}")
        except urllib.error.URLError as e:
            raise RuntimeError(f"Tavily connection error: {e.reason}")
        except Exception as e:
            raise RuntimeError(f"Tavily request failed: {e}")

    def build_embed(self, result, index_label=None):
        title = result.get("title", "Untitled")
        url = result.get("url", "")
        content = (result.get("content") or "").strip()
        if len(content) > 350:
            content = content[:347] + "..."

        embed = discord.Embed(
            title=title,
            url=url if url else None,
            description=content or "No summary available.",
            color=discord.Color.blue(),
            timestamp=datetime.now(timezone.utc)
        )

        embed.set_author(name="SpringBot Live News")
        if index_label:
            embed.add_field(name="Result", value=index_label, inline=True)

        published_date = result.get("published_date") or result.get("published")
        if published_date:
            embed.add_field(name="Published", value=str(published_date), inline=True)

        source = result.get("url", "No URL")
        embed.add_field(name="Source", value=source, inline=False)
        embed.set_footer(text="Powered by Tavily News Search")
        return embed

    def extract_new_results(self, results):
        posted = set(self.state.get("posted_urls", []))
        fresh = []

        for result in results:
            url = result.get("url")
            if not url:
                continue
            if url in posted:
                continue
            fresh.append(result)

        return fresh

    @tasks.loop(minutes=15)
    async def live_news_loop(self):
        if not self.state.get("live_news_enabled", False):
            return

        channel_id = int(self.state.get("news_channel_id", 0) or 0)
        if not channel_id:
            return

        channel = self.bot.get_channel(channel_id)
        if channel is None:
            return

        query = self.state.get("news_query", "breaking news")

        try:
            data = await self.tavily_news_search(query, max_results=6)
        except Exception as e:
            print(f"Live news loop failed: {e}")
            return

        results = data.get("results", [])
        fresh_results = self.extract_new_results(results)

        if not fresh_results:
            return

        for result in reversed(fresh_results[:3]):
            embed = self.build_embed(result)
            await channel.send(embed=embed)
            url = result.get("url")
            if url:
                self.state["posted_urls"].append(url)

        self.save_state()

    @live_news_loop.before_loop
    async def before_live_news_loop(self):
        await self.bot.wait_until_ready()

    @commands.command(help="Search current news.")
    async def newssearch(self, ctx, *, query: str):
        try:
            data = await self.tavily_news_search(query, max_results=5)
        except Exception as e:
            await ctx.send(f"News search failed: {e}")
            return

        answer = data.get("answer") or "No summary returned."
        results = data.get("results", [])

        if len(answer) > 900:
            answer = answer[:897] + "..."

        await ctx.send(f"**News Search:** {query}\n**Summary:** {answer}")

        if not results:
            await ctx.send("No news results found.")
            return

        for i, result in enumerate(results[:3], start=1):
            embed = self.build_embed(result, index_label=str(i))
            await ctx.send(embed=embed)

    @commands.command(help="Show trending or breaking news.")
    async def trendingnews(self, ctx):
        try:
            data = await self.tavily_news_search("breaking news", max_results=5)
        except Exception as e:
            await ctx.send(f"Trending news failed: {e}")
            return

        answer = data.get("answer") or "No summary returned."
        results = data.get("results", [])

        if len(answer) > 900:
            answer = answer[:897] + "..."

        await ctx.send(f"**Trending News Summary:** {answer}")

        if not results:
            await ctx.send("No trending news results found.")
            return

        for i, result in enumerate(results[:3], start=1):
            embed = self.build_embed(result, index_label=str(i))
            await ctx.send(embed=embed)

    @commands.command(help="Read the latest news summary in text form.")
    async def readnews(self, ctx):
        query = self.state.get("news_query", "breaking news")

        try:
            data = await self.tavily_news_search(query, max_results=3)
        except Exception as e:
            await ctx.send(f"Read news failed: {e}")
            return

        answer = data.get("answer") or "No summary returned."
        if len(answer) > 1200:
            answer = answer[:1197] + "..."

        await ctx.send(f"**Latest News Summary:**\n{answer}")

    @commands.command(help="Show the latest headline only.")
    async def latestheadline(self, ctx):
        query = self.state.get("news_query", "breaking news")

        try:
            data = await self.tavily_news_search(query, max_results=1)
        except Exception as e:
            await ctx.send(f"Latest headline failed: {e}")
            return

        results = data.get("results", [])
        if not results:
            await ctx.send("No headline found.")
            return

        first = results[0]
        await ctx.send(f"**Latest Headline:** {first.get('title', 'Untitled')}\n{first.get('url', '')}")

    @commands.command(help="Test the live news system in this channel.")
    async def newstest(self, ctx):
        query = self.state.get("news_query", "breaking news")

        try:
            data = await self.tavily_news_search(query, max_results=3)
        except Exception as e:
            await ctx.send(f"News test failed: {e}")
            return

        results = data.get("results", [])
        if not results:
            await ctx.send("No test news results found.")
            return

        await ctx.send(f"News test successful for query: **{query}**")
        embed = self.build_embed(results[0], index_label="Test")
        await ctx.send(embed=embed)

    @commands.command(help="Set this channel as the live news channel.")
    @commands.has_permissions(manage_guild=True)
    async def setnewschannel(self, ctx):
        self.state["news_channel_id"] = ctx.channel.id
        self.save_state()
        await ctx.send(
            f"This channel is now the live news channel.\n"
            f"Channel ID: **{ctx.channel.id}**"
        )

    @commands.command(help="Turn live news posting on.")
    @commands.has_permissions(manage_guild=True)
    async def liveon(self, ctx):
        if not self.state.get("news_channel_id"):
            self.state["news_channel_id"] = ctx.channel.id

        self.state["live_news_enabled"] = True
        self.save_state()
        await ctx.send("Live news posting is now **ON**.")

    @commands.command(help="Turn live news posting off.")
    @commands.has_permissions(manage_guild=True)
    async def liveoff(self, ctx):
        self.state["live_news_enabled"] = False
        self.save_state()
        await ctx.send("Live news posting is now **OFF**.")

    @commands.command(help="Set the live news topic query. Example: !setnewsquery cybersecurity")
    @commands.has_permissions(manage_guild=True)
    async def setnewsquery(self, ctx, *, query: str):
        self.state["news_query"] = query.strip()
        self.save_state()
        await ctx.send(f"Live news query set to: **{self.state['news_query']}**")

    @commands.command(help="Show current news settings.")
    async def newschannel(self, ctx):
        channel_id = self.state.get("news_channel_id", 0)
        live_enabled = self.state.get("live_news_enabled", False)
        query = self.state.get("news_query", "breaking news")

        await ctx.send(
            f"News channel ID: **{channel_id}**\n"
            f"Live news enabled: **{live_enabled}**\n"
            f"Live news query: **{query}**"
        )

    @commands.command(help="Clear stored posted news links so live posting can start fresh.")
    @commands.has_permissions(manage_guild=True)
    async def clearnewsmemory(self, ctx):
        self.state["posted_urls"] = []
        self.save_state()
        await ctx.send("Stored news memory cleared.")

    @commands.command(help="Show all news commands.")
    async def newshelp(self, ctx):
        await ctx.send(
            "**News Commands**\n"
            "!newssearch <query> - search live news\n"
            "!trendingnews - show trending or breaking news\n"
            "!readnews - read the latest news summary\n"
            "!latestheadline - show the latest headline\n"
            "!newstest - test the news system here\n"
            "!setnewschannel - make this the live news channel\n"
            "!liveon - turn live news posting on\n"
            "!liveoff - turn live news posting off\n"
            "!setnewsquery <query> - set the topic for live news\n"
            "!newschannel - show current news settings\n"
            "!clearnewsmemory - clear stored posted news links\n"
            "!newshelp - show this list"
        )


async def setup(bot):
    await bot.add_cog(News(bot))