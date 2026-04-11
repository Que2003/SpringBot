import os
import json
import asyncio
import urllib.request
import urllib.error

from discord.ext import commands


class Search(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.api_key = os.getenv("TAVILY_API_KEY", "").strip()
        self.endpoint = "https://api.tavily.com/search"

    async def tavily_search(
        self,
        query: str,
        *,
        topic: str = "general",
        search_depth: str = "basic",
        max_results: int = 5,
        include_answer=False,
    ):
        if not self.api_key:
            raise RuntimeError("Missing TAVILY_API_KEY in Railway variables.")

        payload = {
            "query": query,
            "topic": topic,
            "search_depth": search_depth,
            "max_results": max_results,
            "include_answer": include_answer,
            "include_favicon": False,
            "include_images": False,
        }

        body = json.dumps(payload).encode("utf-8")
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }

        request = urllib.request.Request(
            self.endpoint,
            data=body,
            headers=headers,
            method="POST",
        )

        def run_request():
            with urllib.request.urlopen(request, timeout=30) as response:
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

    def format_results(self, results, limit=3):
        if not results:
            return "No source results were returned."

        lines = []
        for idx, result in enumerate(results[:limit], start=1):
            title = result.get("title", "Untitled")
            url = result.get("url", "No URL")
            content = (result.get("content") or "").replace("\n", " ").strip()
            if len(content) > 180:
                content = content[:177] + "..."
            lines.append(f"{idx}. **{title}**\n{url}\n{content}")
        return "\n\n".join(lines)

    @commands.command(help="Search the web. Example: !search latest cybersecurity news")
    async def search(self, ctx, *, query: str):
        try:
            data = await self.tavily_search(
                query,
                topic="general",
                search_depth="basic",
                max_results=5,
                include_answer="basic",
            )
        except Exception as e:
            await ctx.send(f"Search failed: {e}")
            return

        answer = data.get("answer") or "No direct answer was generated."
        results = data.get("results", [])

        await ctx.send(
            f"**Search:** {query}\n"
            f"**Answer:** {answer}\n\n"
            f"**Top Sources**\n{self.format_results(results, 3)}"
        )

    @commands.command(help="Get a short direct answer. Example: !fact what is zero trust")
    async def fact(self, ctx, *, query: str):
        try:
            data = await self.tavily_search(
                query,
                topic="general",
                search_depth="basic",
                max_results=3,
                include_answer="basic",
            )
        except Exception as e:
            await ctx.send(f"Fact lookup failed: {e}")
            return

        answer = data.get("answer") or "No direct answer was returned."
        results = data.get("results", [])

        text = f"**Question:** {query}\n**Answer:** {answer}"
        if results:
            text += f"\n\n**Source:**\n{self.format_results(results, 1)}"

        await ctx.send(text)

    @commands.command(help="Do a deeper web search. Example: !research best home lab firewall options")
    async def research(self, ctx, *, query: str):
        try:
            data = await self.tavily_search(
                query,
                topic="general",
                search_depth="advanced",
                max_results=5,
                include_answer="advanced",
            )
        except Exception as e:
            await ctx.send(f"Research failed: {e}")
            return

        answer = data.get("answer") or "No research summary was returned."
        results = data.get("results", [])

        if len(answer) > 1200:
            answer = answer[:1197] + "..."

        await ctx.send(
            f"**Research:** {query}\n"
            f"**Summary:** {answer}\n\n"
            f"**Top Sources**\n{self.format_results(results, 4)}"
        )

    @commands.command(help="Search recent news. Example: !newssearch microsoft security update")
    async def newssearch(self, ctx, *, query: str):
        try:
            data = await self.tavily_search(
                query,
                topic="news",
                search_depth="basic",
                max_results=5,
                include_answer="basic",
            )
        except Exception as e:
            await ctx.send(f"News search failed: {e}")
            return

        answer = data.get("answer") or "No news summary was returned."
        results = data.get("results", [])

        await ctx.send(
            f"**News Search:** {query}\n"
            f"**Summary:** {answer}\n\n"
            f"**Top News Sources**\n{self.format_results(results, 3)}"
        )

    @commands.command(help="Show top links only. Example: !toplinks best laptops for college")
    async def toplinks(self, ctx, *, query: str):
        try:
            data = await self.tavily_search(
                query,
                topic="general",
                search_depth="basic",
                max_results=5,
                include_answer=False,
            )
        except Exception as e:
            await ctx.send(f"Top links search failed: {e}")
            return

        results = data.get("results", [])
        if not results:
            await ctx.send("No links found.")
            return

        lines = []
        for idx, result in enumerate(results[:5], start=1):
            title = result.get("title", "Untitled")
            url = result.get("url", "No URL")
            lines.append(f"{idx}. **{title}**\n{url}")

        await ctx.send(f"**Top Links for:** {query}\n\n" + "\n\n".join(lines))

    @commands.command(help="Show search commands.")
    async def searchhelp(self, ctx):
        await ctx.send(
            "**Search Commands**\n"
            "!search <query> - web search with answer and sources\n"
            "!fact <query> - short answer with source\n"
            "!research <query> - deeper search and fuller summary\n"
            "!newssearch <query> - recent news search\n"
            "!toplinks <query> - top result links only\n"
            "!searchhelp - show this list"
        )


async def setup(bot):
    await bot.add_cog(Search(bot))