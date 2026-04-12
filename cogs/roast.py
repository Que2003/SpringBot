import random
import discord
from discord.ext import commands

# Keep these funny, not hateful or discriminatory.
LIGHT_ROASTS = [
    "You have strong tutorial NPC energy.",
    "You look like you ask the teacher if homework is due.",
    "You are not lagging, this is just your natural speed.",
    "You bring confusion to very simple situations.",
    "You have the confidence of somebody who did not read the instructions.",
    "You talk like your thoughts are buffering.",
    "You are built like a phone on 3 percent.",
    "You are the human version of a typo.",
    "You always look one step away from asking, 'Wait, what happened?'",
    "You have side quest energy.",
]

SAVAGE_ROASTS = [
    "You have the confidence of a main character and the skill set of a loading screen.",
    "You talk big for somebody built like a weak Wi-Fi signal.",
    "You are the human version of a software trial.",
    "Your comebacks move slower than hotel internet.",
    "You bring chaos to places that were already organized.",
    "Even autocorrect gives up on you.",
    "You have villain confidence with side-character results.",
    "You are proof that free will comes with bugs.",
    "You move like your brain is still installing updates.",
    "You are built like a missed call from a scam number.",
]

MIC_DROP_ENDINGS = [
    "Mic dropped. Somebody sweep that up.",
    "That was disrespectful even by my standards.",
    "Call tech support. They just crashed.",
    "I would apologize, but that was accurate.",
    "That one is going in the server history books.",
]

COMPLIMENTS = [
    "You are actually solid. Respect.",
    "You have real main character energy.",
    "You are smarter than you let on.",
    "You have elite potential. Do not waste it.",
    "You bring good energy to the server.",
    "You are built for better things than arguing in chat.",
    "You are genuinely cooler than most people here.",
    "You have rare W energy.",
]

NPC_ROASTS = [
    "You walk around like you only repeat three lines of dialogue.",
    "You look like you say, 'The weather is nice today,' every 10 seconds.",
    "You have side-character pathing issues.",
    "You act like your whole life is waiting for the player to press X.",
    "You give quest marker but no useful information.",
]

VILLAIN_ROASTS = [
    "Pathetic. Your ambition exceeds your actual ability.",
    "You dare challenge me with that level of incompetence?",
    "Your failure was predetermined the moment you arrived.",
    "You possess an astonishing amount of confidence for someone this unprepared.",
    "Even your dramatic entrance lacked impact.",
]

GENZ_ROASTS = [
    "You are not him. Not even close.",
    "Your whole vibe is expired.",
    "You are moving extremely NPC right now.",
    "That take was so bad the algorithm looked away.",
    "You got cooked before you even loaded in.",
]

OLDSCHOOL_ROASTS = [
    "You could not pour water out of a boot with instructions on the heel.",
    "You are all hat and no cattle.",
    "You are running on fumes and bad decisions.",
    "You have a lot to say for someone bringing very little to the table.",
    "You are a few cards short of a full deck.",
]


def pick_roast(target_name: str, roast_list: list[str]) -> str:
    return f"{target_name}, {random.choice(roast_list)}"


class Roast(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @commands.command(name="roast")
    async def roast(self, ctx: commands.Context, member: discord.Member = None):
        if member is None:
            member = ctx.author
        if member.bot:
            await ctx.send("I am not starting a robot civil war.")
            return
        await ctx.send(pick_roast(member.mention, LIGHT_ROASTS + SAVAGE_ROASTS))

    @commands.command(name="lightroast")
    async def lightroast(self, ctx: commands.Context, member: discord.Member = None):
        if member is None:
            member = ctx.author
        if member.bot:
            await ctx.send("I roast gently, but not bots.")
            return
        await ctx.send(pick_roast(member.mention, LIGHT_ROASTS))

    @commands.command(name="savageroast")
    async def savageroast(self, ctx: commands.Context, member: discord.Member = None):
        if member is None:
            member = ctx.author
        if member.bot:
            await ctx.send("Bots are off-limits. Flesh only.")
            return
        await ctx.send(pick_roast(member.mention, SAVAGE_ROASTS))

    @commands.command(name="roastme")
    async def roastme(self, ctx: commands.Context):
        await ctx.send(pick_roast(ctx.author.mention, LIGHT_ROASTS + SAVAGE_ROASTS))

    @commands.command(name="selfroast")
    async def selfroast(self, ctx: commands.Context):
        await ctx.send(pick_roast(ctx.author.mention, SAVAGE_ROASTS))

    @commands.command(name="complimentorroast")
    async def compliment_or_roast(self, ctx: commands.Context, member: discord.Member = None):
        if member is None:
            member = ctx.author

        if random.choice([True, False]):
            await ctx.send(f"{member.mention}, {random.choice(COMPLIMENTS)}")
        else:
            await ctx.send(pick_roast(member.mention, LIGHT_ROASTS + SAVAGE_ROASTS))

    @commands.command(name="micdrop")
    async def micdrop(self, ctx: commands.Context, member: discord.Member = None):
        if member is None:
            member = ctx.author
        if member.bot:
            await ctx.send("That target is protected by the machine union.")
            return

        roast_line = pick_roast(member.mention, SAVAGE_ROASTS)
        ending = random.choice(MIC_DROP_ENDINGS)
        await ctx.send(f"{roast_line}\n**{ending}**")

    @commands.command(name="pack")
    async def pack(self, ctx: commands.Context, member: discord.Member = None):
        if member is None:
            member = ctx.author
        if member.bot:
            await ctx.send("I am not jumping a bot in chat.")
            return

        roasts = random.sample(LIGHT_ROASTS + SAVAGE_ROASTS, k=3)
        lines = "\n".join([f"• {member.mention}, {r}" for r in roasts])
        await ctx.send(f"**Roast Pack Incoming:**\n{lines}")

    @commands.command(name="friendlyfire")
    async def friendlyfire(self, ctx: commands.Context):
        members = [m for m in ctx.guild.members if not m.bot]
        if not members:
            await ctx.send("No valid targets found.")
            return

        target = random.choice(members)
        await ctx.send(f"**Friendly Fire Activated**\n{pick_roast(target.mention, LIGHT_ROASTS + SAVAGE_ROASTS)}")

    @commands.command(name="duel")
    async def duel(self, ctx: commands.Context, member: discord.Member = None):
        if member is None:
            await ctx.send("Usage: `!duel @user`")
            return

        if member.bot:
            await ctx.send("No roast battle against bots.")
            return

        author_roast = random.choice(LIGHT_ROASTS + SAVAGE_ROASTS)
        member_roast = random.choice(LIGHT_ROASTS + SAVAGE_ROASTS)

        await ctx.send(
            f"**Roast Duel**\n"
            f"{ctx.author.mention}: {author_roast}\n"
            f"{member.mention}: {member_roast}\n"
            f"**Winner:** {random.choice([ctx.author.mention, member.mention])}"
        )

    @commands.command(name="aitalksmack")
    async def aitalksmack(self, ctx: commands.Context, member: discord.Member = None):
        if member is None:
            member = ctx.author
        if member.bot:
            await ctx.send("AI does not beef with its own kind.")
            return

        ai_lines = [
            "My analysis is complete: your trash talk has low processing power.",
            "After reviewing the data, you are 92 percent confidence and 8 percent results.",
            "I ran the numbers. You are all output, no performance.",
            "My neural networks agree: that was not your best moment.",
            "You are operating with deluxe confidence and budget execution.",
        ]
        await ctx.send(f"{member.mention}, {random.choice(ai_lines)}")

    @commands.command(name="npcroast")
    async def npcroast(self, ctx: commands.Context, member: discord.Member = None):
        if member is None:
            member = ctx.author
        if member.bot:
            await ctx.send("This bot already knows it is scripted.")
            return
        await ctx.send(pick_roast(member.mention, NPC_ROASTS))

    @commands.command(name="villainroast")
    async def villainroast(self, ctx: commands.Context, member: discord.Member = None):
        if member is None:
            member = ctx.author
        if member.bot:
            await ctx.send("Even villains leave bots alone.")
            return
        await ctx.send(pick_roast(member.mention, VILLAIN_ROASTS))

    @commands.command(name="genzroast")
    async def genzroast(self, ctx: commands.Context, member: discord.Member = None):
        if member is None:
            member = ctx.author
        if member.bot:
            await ctx.send("That target is giving mechanical immunity.")
            return
        await ctx.send(pick_roast(member.mention, GENZ_ROASTS))

    @commands.command(name="oldschoolroast")
    async def oldschoolroast(self, ctx: commands.Context, member: discord.Member = None):
        if member is None:
            member = ctx.author
        if member.bot:
            await ctx.send("Old school rules say no roasting bots.")
            return
        await ctx.send(pick_roast(member.mention, OLDSCHOOL_ROASTS))


async def setup(bot: commands.Bot):
    await bot.add_cog(Roast(bot))