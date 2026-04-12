import json
import os
import random
from discord.ext import commands


class Study(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.file_path = "study_notes.json"
        self.data = self.load_data()

        self.flashcards = [
            {"q": "What does DNS do?", "a": "It translates domain names into IP addresses."},
            {"q": "What does DHCP do?", "a": "It automatically assigns IP settings to devices."},
            {"q": "What is TCP?", "a": "A reliable connection-based transport protocol."},
            {"q": "What is UDP?", "a": "A faster connectionless transport protocol."},
            {"q": "Port 443?", "a": "HTTPS."},
            {"q": "Port 22?", "a": "SSH."},
            {"q": "Port 3389?", "a": "RDP."},
            {"q": "What is a packet header?", "a": "Control information like source, destination, and protocol."}
        ]

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

    def get_user_notes(self, user_id: int):
        key = str(user_id)
        if key not in self.data:
            self.data[key] = []
        return self.data[key]

    @commands.command(help="Add a study note.")
    async def addnote(self, ctx, *, note: str):
        notes = self.get_user_notes(ctx.author.id)
        notes.append(note)
        self.save_data()
        await ctx.send("Study note saved.")

    @commands.command(help="List your study notes.")
    async def notes(self, ctx):
        notes = self.get_user_notes(ctx.author.id)

        if not notes:
            await ctx.send("You have no saved study notes.")
            return

        lines = [f"{i}. {note}" for i, note in enumerate(notes, start=1)]
        output = "\n".join(lines)

        if len(output) > 1900:
            output = output[:1900] + "..."

        await ctx.send(f"**Your Study Notes**\n{output}")

    @commands.command(help="Delete a study note by number.")
    async def deletenote(self, ctx, index: int):
        notes = self.get_user_notes(ctx.author.id)

        if index < 1 or index > len(notes):
            await ctx.send("That note number does not exist.")
            return

        removed = notes.pop(index - 1)
        self.save_data()
        await ctx.send(f"Deleted note:\n`{removed}`")

    @commands.command(help="Get a random flashcard.")
    async def flashcard(self, ctx):
        card = random.choice(self.flashcards)
        await ctx.send(f"**Flashcard**\nQ: {card['q']}\nUse `!showanswer` to reveal it.")
        self.data[f"flashcard_{ctx.channel.id}"] = card["a"]
        self.save_data()

    @commands.command(help="Show the answer to the current flashcard.")
    async def showanswer(self, ctx):
        key = f"flashcard_{ctx.channel.id}"

        if key not in self.data:
            await ctx.send("There is no active flashcard in this channel.")
            return

        await ctx.send(f"**Answer:** {self.data[key]}")
        del self.data[key]
        self.save_data()

    @commands.command(help="Give a quick quiz question.")
    async def quizme(self, ctx):
        card = random.choice(self.flashcards)
        self.data[f"quiz_{ctx.channel.id}"] = card["a"].lower()
        self.save_data()
        await ctx.send(f"**Quiz**\n{card['q']}\nReply with `!quizanswer <your answer>`")

    @commands.command(help="Answer the current quiz.")
    async def quizanswer(self, ctx, *, answer: str):
        key = f"quiz_{ctx.channel.id}"

        if key not in self.data:
            await ctx.send("There is no active quiz in this channel.")
            return

        correct = self.data[key]
        guess = answer.lower().strip()

        if guess == correct:
            await ctx.send("Correct.")
        else:
            await ctx.send(f"Not quite. Correct answer: **{correct}**")

        del self.data[key]
        self.save_data()

    @commands.command(help="Generate a simple study plan.")
    async def studyplan(self, ctx, *, topic: str):
        await ctx.send(
            f"**Study Plan for {topic}**\n"
            "1. Learn the core definition.\n"
            "2. Break it into 3-5 subtopics.\n"
            "3. Take short notes in your own words.\n"
            "4. Quiz yourself without looking.\n"
            "5. Review weak spots.\n"
            "6. Explain the topic out loud like you are teaching it."
        )

    @commands.command(help="Gives a focus/study tip.")
    async def focus(self, ctx):
        tips = [
            "Use 25 minutes of focus, then take a 5-minute break.",
            "Put your phone out of reach while studying.",
            "Quiz yourself instead of only rereading notes.",
            "Study the hardest thing first while your brain is fresh.",
            "Teach the topic out loud to expose weak areas."
        ]
        await ctx.send(random.choice(tips))

    @commands.command(help="Explain a good way to study.")
    async def howtostudy(self, ctx):
        await ctx.send(
            "Best way to study:\n"
            "- break topics into chunks\n"
            "- write short notes\n"
            "- quiz yourself\n"
            "- repeat what you missed\n"
            "- do not just reread forever"
        )

    @commands.command(help="Shows study commands.")
    async def studyhelp(self, ctx):
        await ctx.send(
            "**Study Commands**\n"
            "!addnote <note>\n"
            "!notes\n"
            "!deletenote <number>\n"
            "!flashcard\n"
            "!showanswer\n"
            "!quizme\n"
            "!quizanswer <answer>\n"
            "!studyplan <topic>\n"
            "!focus\n"
            "!howtostudy\n"
            "!studyhelp"
        )


async def setup(bot):
    await bot.add_cog(Study(bot))