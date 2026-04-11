import os
import json
import asyncio
from datetime import datetime, timezone

import discord
from discord.ext import commands, tasks
import feedparser


class News(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.feed_url = os.getenv("NEWS_FEED_URL", "https://apnews.com/index.rss")
        self.state_file = "news_state.json"
        self.posted_links = self.load_state()
        self.news_poster.start()

    def cog_unload(self):
        self.news_poster.cancel()

    def load_state(self):
        if not os.path.exists(self.state_file):
            return []
        try:
            with open(self.state_file, "r", encoding="utf-8") as f:
                data = json.load(f)
            if isinstance(data, list):
                return data[-200:]
            return []
        except Exception:
            return []

    def save_state(self):
        with open(self.state_file, "w", encoding="utf-8") as f:
            json.dump(self.posted_links[-200:], f, indent=2)

    async def fetch_feed(self):
        loop = asyncio.get_running_loop()
        return await loop.run_in_executor(None, lambda: feedparser.parse(self.feed_url))

    def build_embed(self, entry):
        title = getattr(entry, "title", "Untitled story")
        link = getattr(entry, "link", None)
        summary = getattr(entry, "summary", "")
        published = getattr(entry, "published", None)

        if len(summary) > 400:
            summary = summary[:397] + "..."

        embed = discord.Embed(
            title=title,
            url=link,
            description=summary or "New article posted.",
            color=discord.Color.blue(),
            timestamp=datetime.now(timezone.utc)
        )

        embed.set_author(name="SpringBot Live News")
        embed.set_footer(text="Source feed update")

        if published:
            embed.add_field(name="Published", value=published, inline=False)

        return embed

    @tasks.loop(minutes=10)
    async def news_poster(self):
        channel_id = getattr(self.bot, "news_channel_id", 0)
        if not channel_id:
            return

        channel = self.bot.get_channel(channel_id)
        if channel is None:
            return

        feed = await self.fetch_feed()
        entries = getattr(feed, "entries", [])

        if not entries:
            return

        new_entries = []
        for entry in entries[:10]:
            link = getattr(entry, "link", None)
            if link and link not in self.posted_links:
                new_entries.append(entry)

        if not new_entries:
            return

        for entry in reversed(new_entries):
            link = getattr(entry, "link", None)
            embed = self.build_embed(entry)
            await channel.send(embed=embed)
            if link:
                self.posted_links.append(link)

        self.posted_links = self.posted_links[-200:]
        self.save_state()

    @news_poster.before_loop
    async def before_news_poster(self):
        await self.bot.wait_until_ready()

    @commands.command(help="Shows the current live news feed URL.")
    async def newsfeed(self, ctx):
        await ctx.send(f"Current feed: **{self.feed_url}**")

    @commands.command(help="Tests the news feed and posts the newest headline in this channel.")
    async def newstest(self, ctx):
        feed = await self.fetch_feed()
        entries = getattr(feed, "entries", [])

        if not entries:
            await ctx.send("No news entries were found.")
            return

        entry = entries[0]
        embed = self.build_embed(entry)
        await ctx.send("News feed test successful.")
        await ctx.send(embed=embed)

    @commands.command(help="Sets this channel as the live news channel.")
    @commands.has_permissions(manage_guild=True)
    async def setnewschannel(self, ctx):
        self.bot.news_channel_id = ctx.channel.id
        await ctx.send(f"This channel is now the live news channel.\nChannel ID: **{ctx.channel.id}**")

    @commands.command(help="Shows the currently configured news channel ID.")
    async def newschannel(self, ctx):
        channel_id = getattr(self.bot, "news_channel_id", 0)
        if not channel_id:
            await ctx.send("No live news channel is configured.")
            return
        await ctx.send(f"Current live news channel ID: **{channel_id}**")

    @commands.command(help="Shows all news commands.")
    async def newshelp(self, ctx):
        await ctx.send(
            "**News Commands**\n"
            "!newsfeed - Show current feed URL\n"
            "!newstest - Test the feed in the current channel\n"
            "!setnewschannel - Set the current channel as the live news channel\n"
            "!newschannel - Show current configured news channel ID\n"
            "!newshelp - Show news commands"
        )


async def setup(bot):
    await bot.add_cog(News(bot))