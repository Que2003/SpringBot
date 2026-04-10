import os
import aiohttp
import discord
from discord.ext import commands

LANGUAGETOOL_URL = os.getenv("LANGUAGETOOL_URL", "https://api.languagetool.org/v2/check")
AUTO_GRAMMAR_CHANNELS = {int(x.strip()) for x in os.getenv("AUTO_GRAMMAR_CHANNELS", "").split(",") if x.strip().isdigit()}

class Writing(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    async def check_text(self, text: str, language: str = "en-US"):
        async with aiohttp.ClientSession() as session:
            async with session.post(LANGUAGETOOL_URL, data={"text": text, "language": language}) as resp:
                if resp.status != 200:
                    raise RuntimeError("Grammar service is unavailable.")
                return await resp.json()

    def apply_replacements(self, text: str, matches: list) -> str:
        chars = list(text)
        offset_shift = 0
        for match in sorted(matches, key=lambda m: m.get("offset", 0)):
            replacements = match.get("replacements", [])
            if not replacements:
                continue
            replacement = replacements[0].get("value", "")
            start = match.get("offset", 0) + offset_shift
            end = start + match.get("length", 0)
            chars[start:end] = list(replacement)
            offset_shift += len(replacement) - (end - start)
        return "".join(chars)

    def summarize_matches(self, matches: list) -> str:
        lines = []
        for match in matches[:8]:
            msg = match.get("message", "Issue found.")
            rule = match.get("rule", {}).get("category", {}).get("name", "General")
            repl = ", ".join(r.get("value", "") for r in match.get("replacements", [])[:3]) or "No suggestion"
            lines.append(f"- **{rule}**: {msg} | Suggestions: {repl}")
        return "\n".join(lines) if lines else "No issues found."

    @commands.command(name="grammar")
    async def grammar(self, ctx, *, text: str):
        data = await self.check_text(text)
        matches = data.get("matches", [])
        corrected = self.apply_replacements(text, matches)
        embed = discord.Embed(title="Grammar Check")
        embed.add_field(name="Original", value=text[:1024], inline=False)
        embed.add_field(name="Suggested correction", value=corrected[:1024], inline=False)
        embed.add_field(name="Notes", value=self.summarize_matches(matches)[:1024], inline=False)
        await ctx.send(embed=embed)

    @commands.command(name="betterphrase")
    async def betterphrase(self, ctx, *, text: str):
        data = await self.check_text(text)
        corrected = self.apply_replacements(text, data.get("matches", []))
        stronger = corrected.replace(" really ", " ").replace(" very ", " ")
        concise = " ".join(corrected.split()[:25])
        await ctx.send(f"**Cleaned version:** {corrected}\n\n**Stronger version:** {stronger}\n\n**More concise:** {concise}"[:1900])

    @commands.command(name="rewrite")
    async def rewrite(self, ctx, *, raw: str):
        if "|" not in raw:
            await ctx.send("Use: `!rewrite professional | your text here`")
            return
        tone, text = [x.strip() for x in raw.split("|", 1)]
        data = await self.check_text(text)
        corrected = self.apply_replacements(text, data.get("matches", []))
        tone_key = tone.lower()
        if tone_key == "professional":
            alt = corrected.replace("can't", "cannot").replace("won't", "will not")
        elif tone_key == "friendly":
            alt = corrected.replace("therefore", "so").replace("cannot", "can't")
        elif tone_key == "confident":
            alt = corrected.replace("I think", "I believe").replace("maybe", "")
        elif tone_key == "formal":
            alt = corrected.replace("can't", "cannot").replace("a lot", "significantly")
        else:
            alt = corrected
        embed = discord.Embed(title=f"Rewrite: {tone.title()}")
        embed.add_field(name="Suggested rewrite", value=alt[:1024], inline=False)
        await ctx.send(embed=embed)

    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        if message.author.bot or not message.guild:
            return
        if message.channel.id not in AUTO_GRAMMAR_CHANNELS:
            return
        content = message.content.strip()
        if not content or content.startswith(("!", "/")) or len(content) < 12:
            return
        try:
            data = await self.check_text(content)
        except Exception:
            return
        corrected = self.apply_replacements(content, data.get("matches", []))
        if corrected != content:
            await message.reply(f"**Suggested correction:**\n{corrected}", mention_author=False)

async def setup(bot):
    await bot.add_cog(Writing(bot))
