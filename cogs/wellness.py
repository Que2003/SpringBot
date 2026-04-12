import random
from discord.ext import commands


class Wellness(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

        self.affirmations = [
            "You do not need to have everything figured out today.",
            "Progress counts even when it feels small.",
            "You are allowed to rest without calling it failure.",
            "You have survived every hard day up to this point.",
            "One rough moment does not define your whole life.",
            "You can be overwhelmed and still move forward.",
            "You do not need perfection to make progress.",
            "Your effort matters, even when nobody sees it."
        ]

        self.breathing = [
            "Try this: breathe in for 4 seconds, hold for 4, exhale for 6. Repeat 5 times.",
            "Try box breathing: in 4, hold 4, out 4, hold 4. Do it slowly.",
            "Take one deep breath through your nose, then a slower exhale through your mouth.",
            "Relax your shoulders, unclench your jaw, and take 5 slow breaths."
        ]

        self.grounding = [
            "Use the 5-4-3-2-1 method: 5 things you see, 4 you feel, 3 you hear, 2 you smell, 1 you taste.",
            "Name 3 things around you right now and focus on their details.",
            "Put both feet on the floor and notice the pressure holding you in place.",
            "Look around the room and name objects one by one until your breathing settles."
        ]

        self.sleep_tips = [
            "Dim lights an hour before bed and get off your phone if you can.",
            "Keep your room cool, dark, and quiet for better sleep.",
            "Try a consistent sleep time, even on weekends.",
            "Avoid caffeine late in the day if sleep has been rough."
        ]

        self.study_tips = [
            "Study in short focused blocks instead of marathon sessions.",
            "Quiz yourself instead of only rereading notes.",
            "Teach the topic out loud to see what you actually know.",
            "Work in 25-minute focus rounds, then take a 5-minute break."
        ]

    @commands.command(help="A supportive message.")
    async def affirm(self, ctx):
        await ctx.send(random.choice(self.affirmations))

    @commands.command(help="Breathing exercise help.")
    async def breathe(self, ctx):
        await ctx.send(random.choice(self.breathing))

    @commands.command(help="Grounding exercise help.")
    async def ground(self, ctx):
        await ctx.send(random.choice(self.grounding))

    @commands.command(help="Basic sleep help.")
    async def sleephelp(self, ctx):
        await ctx.send(random.choice(self.sleep_tips))

    @commands.command(help="Quick stress relief suggestions.")
    async def stress(self, ctx):
        await ctx.send(
            "Try this in order:\n"
            "1. Take 5 slow breaths.\n"
            "2. Unclench your shoulders and jaw.\n"
            "3. Drink some water.\n"
            "4. Break the problem into one next step.\n"
            "5. Do only that one next step."
        )

    @commands.command(help="A supportive check-in.")
    async def checkin(self, ctx):
        await ctx.send(
            "Pause for a second.\n"
            "What are you feeling right now?\n"
            "What is the biggest thing stressing you?\n"
            "What is one small thing you can control in the next 10 minutes?"
        )

    @commands.command(help="Simple wellness suggestions.")
    async def wellness(self, ctx):
        await ctx.send(
            "Quick wellness checklist:\n"
            "- Drink water\n"
            "- Move around for 5 minutes\n"
            "- Take a real breath\n"
            "- Eat something if you have not\n"
            "- Get sunlight if possible\n"
            "- Sleep before trying to solve your whole life"
        )

    @commands.command(help="Supportive conversation starter.")
    async def support(self, ctx, *, message: str = ""):
        text = message.lower().strip()

        if any(word in text for word in ["panic", "anxious", "anxiety", "overwhelmed"]):
            await ctx.send(
                "I’m with you.\n"
                "Slow it down.\n"
                "Breathe in for 4, hold 4, out for 6.\n"
                "Tell me the one thing making you spiral the most."
            )
            return

        if any(word in text for word in ["sad", "depressed", "empty", "down"]):
            await ctx.send(
                "I’m sorry you’re carrying that right now.\n"
                "You do not have to solve everything tonight.\n"
                "Tell me what happened, or tell me what today has felt like."
            )
            return

        if any(word in text for word in ["angry", "mad", "frustrated"]):
            await ctx.send(
                "That sounds heavy.\n"
                "Before reacting, step back for a minute.\n"
                "What exactly set you off?"
            )
            return

        if any(word in text for word in ["tired", "burned out", "burnout", "exhausted"]):
            await ctx.send(
                "That sounds like burnout, not laziness.\n"
                "What has been draining you most lately?"
            )
            return

        if any(word in text for word in ["suicide", "kill myself", "end it", "self harm", "hurt myself"]):
            await ctx.send(
                "I’m really sorry you’re dealing with this. You need real immediate support right now.\n"
                "Call or text **988** if you are in the U.S. or contact local emergency services now.\n"
                "If there is a trusted person near you, tell them immediately and do not stay alone."
            )
            return

        await ctx.send(
            "I’m here with you.\n"
            "Tell me what is going on, and I’ll help you think through it one step at a time."
        )

    @commands.command(help="Shows wellness/support commands.")
    async def wellnesshelp(self, ctx):
        await ctx.send(
            "**Wellness Commands**\n"
            "!affirm\n"
            "!breathe\n"
            "!ground\n"
            "!sleephelp\n"
            "!stress\n"
            "!checkin\n"
            "!wellness\n"
            "!support <how you feel>\n"
            "!wellnesshelp"
        )


async def setup(bot):
    await bot.add_cog(Wellness(bot))