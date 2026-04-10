import aiohttp
import feedparser
import discord
from discord.ext import commands

FEEDS = {
    "world": "https://feeds.bbci.co.uk/news/world/rss.xml",
    "tech": "https://feeds.arstechnica.com/arstechnica/technology-lab",
    "science": "https://www.sciencedaily.com/rss/top/science.xml",
    "gaming": "https://www.gamespot.com/feeds/mashup/",
}

class News(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    async def get_feed(self, category: str):
        url = FEEDS.get(category.lower())
        if not url:
            raise RuntimeError("Available categories: " + ", ".join(FEEDS.keys()))
        async with aiohttp.ClientSession() as session:
            async with session.get(url, timeout=20) as resp:
                text = await resp.text()
        return feedparser.parse(text)

    @commands.command(name="news")
    async def news(self, ctx, category: str = "tech"):
        feed = await self.get_feed(category)
        entries = feed.entries[:5]
        if not entries:
            await ctx.send("No headlines found.")
            return
        embed = discord.Embed(title=f"{category.title()} News")
        for item in entries:
            embed.add_field(name=item.get("title", "Untitled"), value=item.get("link", "No link"), inline=False)
        await ctx.send(embed=embed)

    @commands.command(name="headlines")
    async def headlines(self, ctx):
        await self.news(ctx, "world")

async def setup(bot):
    await bot.add_cog(News(bot))
