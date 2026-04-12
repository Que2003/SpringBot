import os
import json
import random
import discord
from discord.ext import commands


class Quotes(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.file_path = "quotes.json"
        self.data = self.load_data()

    def load_data(self):
        if not os.path.exists(self.file_path):
            return {}

        try:
            with open(self.file_path, "r", encoding="utf-8") as f:
                data = json.load(f)
            return data if isinstance(data, dict) else {}
        except Exception:
            return {}

    def save_data(self):
        with open(self.file_path, "w", encoding="utf-8") as f:
            json.dump(self.data, f, indent=2)

    def get_guild_quotes(self, guild_id: int):
        key = str(guild_id)
        if key not in self.data:
            self.data[key] = []
        return self.data[key]

    def next_quote_id(self, guild_id: int):
        quotes = self.get_guild_quotes(guild_id)
        if not quotes:
            return 1
        return max(q.get("id", 0) for q in quotes) + 1

    @commands.command(help="Save a custom quote. Example: !quoteadd something funny")
    async def quoteadd(self, ctx, *, text: str):
        quotes = self.get_guild_quotes(ctx.guild.id)
        quote_id = self.next_quote_id(ctx.guild.id)

        quotes.append({
            "id": quote_id,
            "text": text,
            "author_id": ctx.author.id,
            "author_name": str(ctx.author),
            "quoted_user_id": None,
            "quoted_user_name": str(ctx.author)
        })

        self.save_data()
        await ctx.send(f"Saved quote **#{quote_id}**.")

    @commands.command(help="Save a quote from a replied message.")
    async def savequote(self, ctx):
        if not ctx.message.reference or not ctx.message.reference.message_id:
            await ctx.send("Reply to a message and use `!savequote`.")
            return

        try:
            referenced = await ctx.channel.fetch_message(ctx.message.reference.message_id)
        except Exception:
            await ctx.send("Could not fetch that message.")
            return

        if not referenced.content:
            await ctx.send("That message has no text to quote.")
            return

        quotes = self.get_guild_quotes(ctx.guild.id)
        quote_id = self.next_quote_id(ctx.guild.id)

        quotes.append({
            "id": quote_id,
            "text": referenced.content,
            "author_id": ctx.author.id,
            "author_name": str(ctx.author),
            "quoted_user_id": referenced.author.id,
            "quoted_user_name": str(referenced.author)
        })

        self.save_data()
        await ctx.send(f"Saved quote **#{quote_id}** from **{referenced.author}**.")

    @commands.command(help="Show a random quote, or a random quote from a user.")
    async def quote(self, ctx, member: discord.Member = None):
        quotes = self.get_guild_quotes(ctx.guild.id)

        if not quotes:
            await ctx.send("There are no saved quotes yet.")
            return

        pool = quotes
        if member:
            pool = [q for q in quotes if q.get("quoted_user_id") == member.id]
            if not pool:
                await ctx.send("No quotes found for that user.")
                return

        quote = random.choice(pool)

        await ctx.send(
            f"**Quote #{quote['id']}**\n"
            f"“{quote['text']}”\n"
            f"— {quote.get('quoted_user_name', 'Unknown')}"
        )

    @commands.command(help="Show all quotes saved for a user.")
    async def quotes(self, ctx, member: discord.Member = None):
        quotes = self.get_guild_quotes(ctx.guild.id)

        if member:
            quotes = [q for q in quotes if q.get("quoted_user_id") == member.id]

        if not quotes:
            await ctx.send("No matching quotes found.")
            return

        lines = []
        for q in quotes[:10]:
            lines.append(f"#{q['id']} — {q.get('quoted_user_name', 'Unknown')}: {q['text']}")

        output = "\n".join(lines)
        if len(output) > 1900:
            output = output[:1900] + "..."

        await ctx.send("**Saved Quotes**\n" + output)

    @commands.command(help="Show a random quote from the server.")
    async def randomquote(self, ctx):
        quotes = self.get_guild_quotes(ctx.guild.id)

        if not quotes:
            await ctx.send("There are no saved quotes yet.")
            return

        quote = random.choice(quotes)
        await ctx.send(
            f"**Quote #{quote['id']}**\n"
            f"“{quote['text']}”\n"
            f"— {quote.get('quoted_user_name', 'Unknown')}"
        )

    @commands.command(help="Delete a quote by ID.")
    @commands.has_permissions(manage_messages=True)
    async def quotedelete(self, ctx, quote_id: int):
        quotes = self.get_guild_quotes(ctx.guild.id)

        for i, q in enumerate(quotes):
            if q.get("id") == quote_id:
                removed = quotes.pop(i)
                self.save_data()
                await ctx.send(f"Deleted quote **#{removed['id']}**.")
                return

        await ctx.send("That quote ID does not exist.")

    @commands.command(help="Show quote commands.")
    async def quotehelp(self, ctx):
        await ctx.send(
            "**Quote Commands**\n"
            "!quoteadd <text>\n"
            "!savequote\n"
            "!quote [@user]\n"
            "!quotes [@user]\n"
            "!randomquote\n"
            "!quotedelete <id>\n"
            "!quotehelp"
        )


async def setup(bot):
    await bot.add_cog(Quotes(bot))