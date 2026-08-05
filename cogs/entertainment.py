import asyncio
import hashlib
import random
import re
from datetime import date

import discord
from discord.ext import commands

TRIVIA = [
    ("tech", "What does CPU stand for?", ["Central Processing Unit", "Computer Power Utility", "Core Program User", "Central Program Upload"], "A"),
    ("tech", "Which protocol translates domain names into IP addresses?", ["DHCP", "DNS", "FTP", "SSH"], "B"),
    ("movies", "In The Matrix, which color pill does Neo take?", ["Blue", "Red", "Green", "White"], "B"),
    ("movies", "Which city is Batman most associated with?", ["Metropolis", "Gotham City", "Star City", "Central City"], "B"),
    ("music", "How many strings does a standard guitar usually have?", ["4", "5", "6", "8"], "C"),
    ("gaming", "Which game series features Master Chief?", ["Halo", "Fallout", "Doom", "Mass Effect"], "A"),
    ("gaming", "What material builds a Nether portal frame in Minecraft?", ["Bedrock", "Obsidian", "Quartz", "Blackstone"], "B"),
    ("general", "Which planet is known as the Red Planet?", ["Venus", "Mars", "Jupiter", "Mercury"], "B"),
    ("general", "How many days are in a leap year?", ["364", "365", "366", "367"], "C"),
    ("general", "What is the largest ocean on Earth?", ["Atlantic", "Indian", "Arctic", "Pacific"], "D"),
]

WOULD_YOU_RATHER = [
    "have the ability to pause time or rewind time?",
    "explore deep space or the deepest parts of the ocean?",
    "always have perfect Wi-Fi or always have a fully charged phone?",
    "be able to fly or become invisible?",
    "live in your favorite movie universe or favorite game universe?",
    "know every language or master every musical instrument?",
]

JOKES = [
    "Why did the computer go to therapy? It had too many unresolved issues.",
    "I told my Wi-Fi we needed space. Now we are disconnected.",
    "Why do programmers prefer dark mode? Because light attracts bugs.",
    "My password is 'incorrect.' Whenever I forget it, the computer reminds me.",
    "Why was the keyboard calm? It had plenty of space.",
]

TRUTHS = [
    "What is a goal you have not told many people about?",
    "What is your funniest embarrassing moment?",
    "What habit would you most like to improve?",
    "What fictional character do you relate to most?",
]

DARES = [
    "Send a compliment to someone in this server.",
    "Speak in movie quotes for the next five minutes.",
    "Post your best harmless meme.",
    "Use only emojis in your next three messages.",
]

EIGHT_BALL = [
    "It is certain.", "Very likely.", "Signs point to yes.", "Ask again later.",
    "The answer is unclear right now.", "Do not count on it.", "My sources say no.",
]


class Entertainment(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @commands.command(name="entertainment", aliases=["enthelp", "funhelp"])
    async def entertainment(self, ctx: commands.Context) -> None:
        embed = discord.Embed(
            title="🎉 SpringBot Entertainment",
            description="Games, trivia, jokes, and party commands.",
            color=discord.Color.blurple(),
        )
        embed.add_field(name="Games", value="`!trivia [category]` · `!rps <choice>` · `!guess` · `!slots`", inline=False)
        embed.add_field(name="Random Fun", value="`!wyr` · `!8ball <question>` · `!joke` · `!coinflip` · `!roll 2d6`", inline=False)
        embed.add_field(name="Party", value="`!truth` · `!dare` · `!choose pizza | tacos` · `!vibe [person]`", inline=False)
        embed.set_footer(text="Trivia: tech, movies, music, gaming, general")
        await ctx.send(embed=embed)

    @commands.command(name="trivia")
    @commands.cooldown(1, 12, commands.BucketType.user)
    async def trivia(self, ctx: commands.Context, category: str = "random") -> None:
        category = category.lower().strip()
        categories = sorted({item[0] for item in TRIVIA})
        if category != "random" and category not in categories:
            await ctx.send("Choose `tech`, `movies`, `music`, `gaming`, `general`, or `random`.")
            return
        pool = TRIVIA if category == "random" else [item for item in TRIVIA if item[0] == category]
        picked_category, question, options, correct = random.choice(pool)
        lines = [f"**{chr(65 + i)}.** {option}" for i, option in enumerate(options)]
        embed = discord.Embed(
            title=f"🧠 Trivia — {picked_category.title()}",
            description=f"{question}\n\n" + "\n".join(lines),
            color=discord.Color.gold(),
        )
        embed.set_footer(text="Reply A, B, C, or D within 20 seconds")
        await ctx.send(embed=embed)

        def check(message: discord.Message) -> bool:
            return message.author.id == ctx.author.id and message.channel.id == ctx.channel.id and message.content.strip().upper() in {"A", "B", "C", "D"}

        try:
            response = await self.bot.wait_for("message", timeout=20, check=check)
        except asyncio.TimeoutError:
            await ctx.send(f"⌛ Time is up. The answer was **{correct}. {options[ord(correct) - 65]}**.")
            return
        answer = response.content.strip().upper()
        if answer == correct:
            await ctx.send(f"✅ Correct, {ctx.author.mention}!")
        else:
            await ctx.send(f"❌ The answer was **{correct}. {options[ord(correct) - 65]}**.")

    @commands.command(name="wyr", aliases=["wouldyourather"])
    async def wyr(self, ctx: commands.Context) -> None:
        await ctx.send(f"🤔 **Would you rather** {random.choice(WOULD_YOU_RATHER)}")

    @commands.command(name="eightball", aliases=["8ball", "magic8"])
    @commands.cooldown(1, 4, commands.BucketType.user)
    async def eightball(self, ctx: commands.Context, *, question: str = "") -> None:
        if not question.strip():
            await ctx.send("Ask a question, such as `!8ball Will I pass my exam?`")
            return
        await ctx.send(f"🎱 **Question:** {question[:300]}\n**Answer:** {random.choice(EIGHT_BALL)}")

    @commands.command(name="rps")
    async def rps(self, ctx: commands.Context, choice: str = "") -> None:
        choice = {"r": "rock", "p": "paper", "s": "scissors"}.get(choice.lower(), choice.lower())
        if choice not in {"rock", "paper", "scissors"}:
            await ctx.send("Choose `rock`, `paper`, or `scissors`.")
            return
        bot_choice = random.choice(["rock", "paper", "scissors"])
        wins = {("rock", "scissors"), ("paper", "rock"), ("scissors", "paper")}
        result = "Tie!" if choice == bot_choice else "You win!" if (choice, bot_choice) in wins else "SpringBot wins!"
        emoji = {"rock": "🪨", "paper": "📄", "scissors": "✂️"}
        await ctx.send(f"You: {emoji[choice]} **{choice.title()}**\nSpringBot: {emoji[bot_choice]} **{bot_choice.title()}**\n**{result}**")

    @commands.command(name="roll", aliases=["dice"])
    async def roll(self, ctx: commands.Context, notation: str = "1d6") -> None:
        match = re.fullmatch(r"(\d{1,2})d(\d{1,4})([+-]\d{1,5})?", notation.lower())
        if not match:
            await ctx.send("Use `!roll 2d6`, `!roll 1d20`, or `!roll 2d8+3`.")
            return
        count, sides, modifier = int(match.group(1)), int(match.group(2)), int(match.group(3) or 0)
        if not 1 <= count <= 20 or not 2 <= sides <= 1000:
            await ctx.send("Use 1–20 dice with 2–1000 sides each.")
            return
        rolls = [random.randint(1, sides) for _ in range(count)]
        await ctx.send(f"🎲 Rolls: `{', '.join(map(str, rolls))}`\n**Total: {sum(rolls) + modifier}**")

    @commands.command(name="coinflip", aliases=["flip"])
    async def coinflip(self, ctx: commands.Context) -> None:
        await ctx.send(f"🪙 **{random.choice(['Heads', 'Tails'])}!**")

    @commands.command(name="joke")
    async def joke(self, ctx: commands.Context) -> None:
        await ctx.send(f"😄 {random.choice(JOKES)}")

    @commands.command(name="truth")
    async def truth(self, ctx: commands.Context) -> None:
        await ctx.send(f"💬 **Truth:** {random.choice(TRUTHS)}")

    @commands.command(name="dare")
    async def dare(self, ctx: commands.Context) -> None:
        await ctx.send(f"🔥 **Dare:** {random.choice(DARES)}")

    @commands.command(name="choose", aliases=["pick"])
    async def choose(self, ctx: commands.Context, *, choices: str = "") -> None:
        items = [item.strip() for item in choices.split("|") if item.strip()]
        if not 2 <= len(items) <= 20:
            await ctx.send("Separate 2–20 choices with `|`, such as `!choose pizza | tacos`.")
            return
        await ctx.send(f"🎯 I choose: **{random.choice(items)[:300]}**")

    @commands.command(name="slots", aliases=["slot"])
    @commands.cooldown(1, 5, commands.BucketType.user)
    async def slots(self, ctx: commands.Context) -> None:
        result = [random.choice(["🍒", "🍋", "🍇", "🔔", "⭐", "7️⃣"]) for _ in range(3)]
        message = "Jackpot!" if len(set(result)) == 1 else "Nice pair!" if len(set(result)) == 2 else "Try again!"
        await ctx.send(f"🎰 │ {' │ '.join(result)} │\n**{message}**")

    @commands.command(name="guess")
    @commands.cooldown(1, 45, commands.BucketType.user)
    async def guess(self, ctx: commands.Context) -> None:
        answer = random.randint(1, 20)
        await ctx.send("🔢 I picked a number from **1 to 20**. You have three guesses.")

        def check(message: discord.Message) -> bool:
            return message.author.id == ctx.author.id and message.channel.id == ctx.channel.id and message.content.strip().isdigit()

        for attempt in range(1, 4):
            try:
                message = await self.bot.wait_for("message", timeout=20, check=check)
            except asyncio.TimeoutError:
                await ctx.send(f"⌛ Time is up. The number was **{answer}**.")
                return
            guess = int(message.content.strip())
            if guess == answer:
                await ctx.send(f"🎉 Correct in **{attempt}** attempt(s)!")
                return
            if attempt < 3:
                await ctx.send(f"Guess **{'higher' if guess < answer else 'lower'}**. {3 - attempt} attempt(s) left.")
        await ctx.send(f"The number was **{answer}**.")

    @commands.command(name="vibe", aliases=["rate"])
    async def vibe(self, ctx: commands.Context, *, target: str = "") -> None:
        subject = target.strip() or ctx.author.display_name
        seed = f"{date.today().isoformat()}:{subject.lower()}".encode()
        score = int(hashlib.sha256(seed).hexdigest()[:8], 16) % 101
        await ctx.send(f"✨ **{subject[:100]}** has a **{score}% vibe** today.")


async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(Entertainment(bot))
