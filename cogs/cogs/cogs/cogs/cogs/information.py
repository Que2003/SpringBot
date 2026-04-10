import os
import aiohttp
import urllib.parse
from zoneinfo import ZoneInfo
from datetime import datetime
import discord
from discord.ext import commands

WIKI_API = "https://en.wikipedia.org/api/rest_v1/page/summary/"
MW_API = "https://www.dictionaryapi.com/api/v3/references/collegiate/json/"
TIMEZONES = {
    "houston": "America/Chicago",
    "chicago": "America/Chicago",
    "newyork": "America/New_York",
    "losangeles": "America/Los_Angeles",
    "london": "Europe/London",
    "tokyo": "Asia/Tokyo",
    "paris": "Europe/Paris",
}

class Information(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.mw_key = os.getenv("MERRIAM_WEBSTER_API_KEY", "").strip()

    @commands.command(name="wiki")
    async def wiki(self, ctx, *, topic: str):
        async with aiohttp.ClientSession() as session:
            async with session.get(WIKI_API + urllib.parse.quote(topic)) as resp:
                if resp.status != 200:
                    await ctx.send("No Wikipedia summary found.")
                    return
                data = await resp.json()
        embed = discord.Embed(title=data.get("title", topic), description=data.get("extract", "No summary available.")[:3500])
        url = data.get("content_urls", {}).get("desktop", {}).get("page")
        if url:
            embed.add_field(name="Read more", value=url, inline=False)
        thumbnail = data.get("thumbnail", {}).get("source")
        if thumbnail:
            embed.set_thumbnail(url=thumbnail)
        await ctx.send(embed=embed)

    @commands.command(name="define")
    async def define(self, ctx, *, word: str):
        if not self.mw_key:
            await ctx.send("Add `MERRIAM_WEBSTER_API_KEY` to use the official dictionary lookup.")
            return
        url = f"{MW_API}{urllib.parse.quote(word)}?key={self.mw_key}"
        async with aiohttp.ClientSession() as session:
            async with session.get(url) as resp:
                if resp.status != 200:
                    await ctx.send("Dictionary lookup failed.")
                    return
                data = await resp.json()
        if not data:
            await ctx.send("Definition not found.")
            return
        if isinstance(data[0], str):
            await ctx.send("No exact match. Suggestions: " + ", ".join(data[:8]))
            return
        entry = data[0]
        hw = entry.get("hwi", {}).get("hw", word).replace("*", "·")
        shortdef = entry.get("shortdef", [])
        embed = discord.Embed(title=f"Definition: {hw}")
        embed.add_field(name="Part of speech", value=entry.get("fl", "unknown"), inline=False)
        embed.add_field(name="Definition(s)", value="\\n".join(f"{i+1}. {d}" for i, d in enumerate(shortdef[:3])) or "No definition found.", inline=False)
        await ctx.send(embed=embed)

    @commands.command(name="timein")
    async def timein(self, ctx, *, city: str):
        key = city.lower().replace(" ", "")
        tz = TIMEZONES.get(key)
        if not tz:
            await ctx.send("Known cities: " + ", ".join(TIMEZONES.keys()))
            return
        now = datetime.now(ZoneInfo(tz))
        await ctx.send(f"🕒 Current time in **{city.title()}**: `{now.strftime('%Y-%m-%d %I:%M %p')}`")

    @commands.command(name="math")
    async def math(self, ctx, *, expression: str):
        allowed = "0123456789+-*/(). %"
        if not all(c in allowed for c in expression):
            await ctx.send("Only basic math symbols are allowed.")
            return
        try:
            result = eval(expression, {"__builtins__": {}}, {})
        except Exception:
            await ctx.send("Invalid math expression.")
            return
        await ctx.send(f"`{expression} = {result}`")

async def setup(bot):
    await bot.add_cog(Information(bot))
