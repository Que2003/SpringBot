import random
from discord.ext import commands


class Fun(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

        self.jokes = [
            "I told my Wi-Fi we needed to talk. Now we have no connection.",
            "My computer has one job and still acts like it deserves a lunch break.",
            "I asked the bot to be smarter. Now it judges me in 4K.",
            "I cleaned my room once. The government called it a historical event.",
            "My sleep schedule is basically a cyberattack on my body.",
            "Some people chase dreams. I hit snooze and let them escape.",
            "I am not lazy. I am in power-saving mode.",
            "I tried to be productive today. My bed said absolutely not.",
            "I opened one tab to study and now I somehow know the history of forklifts.",
            "My motivation and I are currently in a long-distance relationship.",
            "I did not fail. I just discovered another way not to do it.",
            "My brain has 47 tabs open and all of them are buffering.",
            "I’m not behind in life. I’m just loading in slowly.",
            "The group project always has one person doing all the work and three people discovering oxygen.",
            "I’m built different. Unfortunately, different from success.",
            "My wallet is on a diet I never agreed to.",
            "I wanted peace. Life sent notifications instead.",
            "I make jokes because therapy costs money.",
            "My attention span got up and left mid-sentence.",
            "I don’t procrastinate. I let the pressure marinate."
        ]

        self.roasts = [
            "You bring a lot to the table. Mostly confusion.",
            "You are not useless. You can always serve as a bad example.",
            "Your logic has the structural integrity of wet bread.",
            "You type like your keyboard owes you money.",
            "You move through life like a software update nobody asked for.",
            "Your plan had potential. Then you showed up.",
            "You’re proof that autopilot can still crash.",
            "You make confidence look suspicious.",
            "You’ve got the energy of a dying phone at 2 percent.",
            "You are the human version of a terms and conditions page."
        ]

        self.fake_motivation = [
            "Believe in yourself. Even when the evidence says otherwise.",
            "You can do anything. Not well. But technically, you can do it.",
            "Every failure is progress in a very embarrassing direction.",
            "Dream big, panic bigger, survive somehow.",
            "Success is just confusion that lasted longer than quitting.",
            "Stand tall. Unless you are wrong. Then sit down quietly.",
            "Keep going. Spite is a valid fuel source.",
            "You are capable of amazing things. Mostly accidents, but still.",
            "Lock in. Or at least pretend hard enough to scare people.",
            "The grind never stops. Mostly because you forgot how to rest."
        ]

        self.excuses = [
            "I would have finished, but destiny said not today.",
            "My bad, the vibes were off.",
            "I was on the verge of greatness, then I got hungry.",
            "The mission failed due to unforeseen laziness.",
            "I had a plan. It just died young.",
            "I was absolutely going to do it until I remembered I didn’t want to.",
            "My brain entered airplane mode.",
            "I got distracted by something deeply irrelevant but spiritually important.",
            "The schedule collapsed under emotional pressure.",
            "Honestly, it sounded better in my head."
        ]

        self.bro_said_lines = [
            "Bro said 'trust the process' and the process filed for bankruptcy.",
            "Bro said 'I got this' and immediately made it worse.",
            "Bro said 'one more game' like time is not a real thing.",
            "Bro said 'I’m different' and proved it in the worst way possible.",
            "Bro said 'easy work' and started sweating instantly.",
            "Bro said 'I don’t miss' and missed morally, mentally, and physically.",
            "Bro said 'watch this' and now everybody is traumatized.",
            "Bro said 'I work better under pressure' and folded like a lawn chair.",
            "Bro said 'I know a shortcut' and got the whole squad lost.",
            "Bro said 'let me cook' and burned the timeline."
        ]

        self.pickup_parody = [
            "Are you a software bug? Because now everything is broken and I’m still interested.",
            "Are you my GPA? Because I should be paying more attention to you.",
            "Are you a loading screen? Because this is taking forever but I’m still here.",
            "Are you a pop quiz? Because you showed up uninvited and ruined my mood.",
            "Are you bad decisions? Because somehow I keep coming back.",
            "Are you my charger? Because without you I’m at 1 percent."
        ]

    @commands.command(help="Tells a genuinely funny random joke.")
    async def joke(self, ctx):
        await ctx.send(random.choice(self.jokes))

    @commands.command(help="Hits you with a random roast.")
    async def roast(self, ctx, member=None):
        target = member if member else ctx.author.mention
        await ctx.send(f"{target} — {random.choice(self.roasts)}")

    @commands.command(help="Fake motivational quote that sounds helpful but really is not.")
    async def motivate(self, ctx):
        await ctx.send(random.choice(self.fake_motivation))

    @commands.command(help="Gives a hilarious excuse.")
    async def excuse(self, ctx):
        await ctx.send(random.choice(self.excuses))

    @commands.command(help="Bro said style joke.")
    async def brosaid(self, ctx):
        await ctx.send(random.choice(self.bro_said_lines))

    @commands.command(help="Funny fake pickup line.")
    async def pickup(self, ctx):
        await ctx.send(random.choice(self.pickup_parody))

    @commands.command(help="Flips a coin.")
    async def coinflip(self, ctx):
        await ctx.send(f"The coin landed on: **{random.choice(['Heads', 'Tails'])}**")

    @commands.command(help="Rolls a six-sided die.")
    async def roll(self, ctx):
        await ctx.send(f"You rolled a **{random.randint(1, 6)}**")

    @commands.command(help="Repeats your message.")
    async def say(self, ctx, *, message):
        await ctx.send(message)

    @commands.command(help="Answers like a chaotic 8-ball.")
    async def eightball(self, ctx, *, question):
        responses = [
            "Yes, and it will be messy.",
            "No. Absolutely not.",
            "Maybe, but you’re going to regret finding out.",
            "Without a doubt.",
            "The signs say yes, which is concerning.",
            "Ask again when your decisions improve.",
            "Technically yes. Spiritually no.",
            "I would not bet money on it."
        ]
        await ctx.send(
            f"Question: {question}\nAnswer: **{random.choice(responses)}**"
        )

    @commands.command(help="Shows all comedy commands.")
    async def funhelp(self, ctx):
        await ctx.send(
            "**Comedy Commands**\n"
            "!joke - random funny joke\n"
            "!roast [@user] - random roast\n"
            "!motivate - fake motivation\n"
            "!excuse - random funny excuse\n"
            "!brosaid - bro said joke\n"
            "!pickup - parody pickup line\n"
            "!coinflip - flip a coin\n"
            "!roll - roll a die\n"
            "!say <message> - make the bot repeat you\n"
            "!eightball <question> - chaotic magic 8-ball\n"
            "!funhelp - show this list"
        )


async def setup(bot):
    await bot.add_cog(Fun(bot))