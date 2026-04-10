import random
from discord.ext import commands
import discord

QUIZ_BANK = {
    "tech": [
        {"q": "What port does HTTPS use by default?", "a": "443"},
        {"q": "What does DNS do?", "a": "It translates domain names into IP addresses."},
        {"q": "What does RAM store?", "a": "Short-term working data for active tasks."},
    ],
    "science": [
        {"q": "What planet is known as the Red Planet?", "a": "Mars"},
        {"q": "What gas do plants absorb?", "a": "Carbon dioxide"},
    ],
    "history": [
        {"q": "What year did World War II end?", "a": "1945"},
        {"q": "Who was the first U.S. president?", "a": "George Washington"},
    ],
}
FLASHCARDS = [
    ("CIA Triad", "Confidentiality, Integrity, Availability"),
    ("Phishing", "A social engineering attack that tricks users into revealing information"),
    ("Firewall", "A control that filters network traffic"),
]
STUDY_TIPS = [
    "Use active recall instead of passive rereading.",
    "Study in focused 25-minute blocks.",
    "Explain the topic out loud like you are teaching it.",
    "Mix quizzes, flashcards, and summaries.",
]

class Education(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.command(name="quiz")
    async def quiz(self, ctx, topic: str = "tech"):
        topic = topic.lower()
        if topic not in QUIZ_BANK:
            await ctx.send(f"Available topics: {', '.join(QUIZ_BANK.keys())}")
            return
        item = random.choice(QUIZ_BANK[topic])
        embed = discord.Embed(title=f"{topic.title()} Quiz")
        embed.add_field(name="Question", value=item["q"], inline=False)
        embed.add_field(name="Answer", value=f"||{item['a']}||", inline=False)
        await ctx.send(embed=embed)

    @commands.command(name="flashcard")
    async def flashcard(self, ctx):
        term, definition = random.choice(FLASHCARDS)
        embed = discord.Embed(title="Flashcard")
        embed.add_field(name="Term", value=term, inline=False)
        embed.add_field(name="Definition", value=f"||{definition}||", inline=False)
        await ctx.send(embed=embed)

    @commands.command(name="studytip")
    async def studytip(self, ctx):
        await ctx.send(f"📘 Study tip: {random.choice(STUDY_TIPS)}")

    @commands.command(name="explain")
    async def explain(self, ctx, *, topic: str):
        await ctx.send(
            f"**Simple explanation for:** {topic}\n"
            f"- What it is: the core idea behind `{topic}`.\n"
            f"- Why it matters: understanding basics makes advanced topics easier.\n"
            f"- Best next step: ask a more specific follow-up on `{topic}`."
        )

async def setup(bot):
    await bot.add_cog(Education(bot))
