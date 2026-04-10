import random
import discord
from discord.ext import commands

SUPPORTIVE_OPENERS = [
    "I hear you.",
    "That sounds heavy.",
    "That sounds frustrating.",
    "I'm glad you said something.",
    "You're not weak for feeling that way.",
]

COMFORT_LINES = [
    "Take one thing at a time.",
    "You do not have to solve everything in one moment.",
    "Breathe. Slow is still progress.",
    "You have made it through hard days before.",
    "It is okay to pause and reset.",
]

ENCOURAGEMENT = [
    "You're building, even when it feels slow.",
    "Consistency beats random bursts.",
    "You are allowed to improve without being perfect.",
    "Small wins count.",
    "You can regroup and keep moving.",
]

NEGATIVE_WORDS = {
    "sad","depressed","angry","mad","upset","hurt","stressed",
    "anxious","anxiety","lonely","tired","broken","crying",
    "frustrated","overwhelmed","worthless","miserable"
}

POSITIVE_WORDS = {
    "happy","good","great","amazing","excited","proud",
    "better","calm","strong","hopeful","motivated","winning"
}

def mood_score(text: str) -> int:
    words = {w.strip(".,!?;:()[]{}\\\"'").lower() for w in text.split()}
    score = 0
    for word in words:
        if word in POSITIVE_WORDS:
            score += 1
        if word in NEGATIVE_WORDS:
            score -= 1
    return score

class Empathy(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.command(name="comfort")
    async def comfort(self, ctx):
        await ctx.send(f"{random.choice(SUPPORTIVE_OPENERS)} {random.choice(COMFORT_LINES)}")

    @commands.command(name="encourage")
    async def encourage(self, ctx):
        await ctx.send(random.choice(ENCOURAGEMENT))

    @commands.command(name="checkin")
    async def checkin(self, ctx):
        embed = discord.Embed(
            title="Quick Check-In",
            description="How are you feeling right now?\nReply with one word or one short sentence."
        )
        await ctx.send(embed=embed)

    @commands.command(name="vent")
    async def vent(self, ctx, *, message: str):
        score = mood_score(message)
        if score <= -2:
            reply = f"{random.choice(SUPPORTIVE_OPENERS)} What you said sounds really rough. {random.choice(COMFORT_LINES)}"
        elif score == -1:
            reply = f"Sounds like you're carrying some pressure right now. {random.choice(COMFORT_LINES)}"
        elif score >= 2:
            reply = "I can feel the positive energy in that. Hold onto that momentum."
        else:
            reply = "Thanks for saying it out loud. Sometimes naming the feeling helps."
        await ctx.send(reply)

async def setup(bot):
    await bot.add_cog(Empathy(bot))
