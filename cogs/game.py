import random
from discord.ext import commands


class Games(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.guess_numbers = {}
        self.hangman_games = {}
        self.ttt_games = {}

        self.trivia_questions = [
            {
                "question": "What planet is known as the Red Planet?",
                "answer": "mars"
            },
            {
                "question": "How many continents are there?",
                "answer": "7"
            },
            {
                "question": "What is the largest ocean on Earth?",
                "answer": "pacific"
            },
            {
                "question": "Who wrote Romeo and Juliet?",
                "answer": "shakespeare"
            },
            {
                "question": "What gas do plants absorb from the atmosphere?",
                "answer": "carbon dioxide"
            },
            {
                "question": "What is 9 x 9?",
                "answer": "81"
            },
            {
                "question": "What language is mainly spoken in Brazil?",
                "answer": "portuguese"
            }
        ]

        self.hangman_words = [
            "computer",
            "discord",
            "network",
            "python",
            "security",
            "algorithm",
            "database",
            "internet",
            "server",
            "keyboard",
            "monitor",
            "science",
            "history",
            "mathematics"
        ]

    def render_board(self, board):
        symbols = []
        for cell in board:
            if cell == "":
                symbols.append("⬜")
            elif cell == "X":
                symbols.append("❌")
            else:
                symbols.append("⭕")

        return (
            f"{symbols[0]} {symbols[1]} {symbols[2]}\n"
            f"{symbols[3]} {symbols[4]} {symbols[5]}\n"
            f"{symbols[6]} {symbols[7]} {symbols[8]}"
        )

    def check_winner(self, board):
        wins = [
            (0, 1, 2),
            (3, 4, 5),
            (6, 7, 8),
            (0, 3, 6),
            (1, 4, 7),
            (2, 5, 8),
            (0, 4, 8),
            (2, 4, 6),
        ]

        for a, b, c in wins:
            if board[a] != "" and board[a] == board[b] == board[c]:
                return board[a]

        if "" not in board:
            return "draw"

        return None

    def render_hangman(self, word, guessed, tries_left):
        shown = " ".join([letter if letter in guessed else "_" for letter in word])
        guessed_letters = ", ".join(sorted(guessed)) if guessed else "None"
        return (
            f"Word: **{shown}**\n"
            f"Guessed: **{guessed_letters}**\n"
            f"Tries left: **{tries_left}**"
        )

    @commands.command(help="Rock paper scissors. Example: !rps rock")
    async def rps(self, ctx, choice: str):
        user_choice = choice.lower().strip()
        valid = ["rock", "paper", "scissors"]

        if user_choice not in valid:
            await ctx.send("Use `rock`, `paper`, or `scissors`.")
            return

        bot_choice = random.choice(valid)

        if user_choice == bot_choice:
            result = "It's a tie."
        elif (
            (user_choice == "rock" and bot_choice == "scissors")
            or (user_choice == "paper" and bot_choice == "rock")
            or (user_choice == "scissors" and bot_choice == "paper")
        ):
            result = "You win."
        else:
            result = "I win."

        await ctx.send(
            f"You chose **{user_choice}**.\n"
            f"I chose **{bot_choice}**.\n"
            f"**{result}**"
        )

    @commands.command(help="Flip a coin.")
    async def coinflip(self, ctx):
        await ctx.send(f"The coin landed on **{random.choice(['Heads', 'Tails'])}**.")

    @commands.command(help="Roll a die.")
    async def roll(self, ctx, sides: int = 6):
        if sides < 2:
            await ctx.send("The die needs at least 2 sides.")
            return

        result = random.randint(1, sides)
        await ctx.send(f"You rolled a **{result}** on a **{sides}**-sided die.")

    @commands.command(help="Get a random trivia question.")
    async def trivia(self, ctx):
        q = random.choice(self.trivia_questions)
        await ctx.send(
            f"**Trivia Question**\n{q['question']}\n\n"
            f"Reply with: `!answer your_guess_here`"
        )
        self.guess_numbers[f"trivia_{ctx.channel.id}"] = q["answer"]

    @commands.command(help="Answer the active trivia question.")
    async def answer(self, ctx, *, user_answer: str):
        key = f"trivia_{ctx.channel.id}"
        if key not in self.guess_numbers:
            await ctx.send("There is no active trivia question in this channel.")
            return

        correct = self.guess_numbers[key]
        guess = user_answer.lower().strip()

        if guess == correct:
            await ctx.send("Correct. You got it.")
        else:
            await ctx.send(f"Wrong. The correct answer was **{correct}**.")

        del self.guess_numbers[key]

    @commands.command(help="Start a number guessing game.")
    async def guess(self, ctx):
        number = random.randint(1, 100)
        self.guess_numbers[f"guess_{ctx.channel.id}_{ctx.author.id}"] = number
        await ctx.send(
            "I picked a number between **1 and 100**.\n"
            "Guess it with `!myguess <number>`"
        )

    @commands.command(help="Guess the number in your active guessing game.")
    async def myguess(self, ctx, number: int):
        key = f"guess_{ctx.channel.id}_{ctx.author.id}"

        if key not in self.guess_numbers:
            await ctx.send("You do not have an active guessing game. Use `!guess` first.")
            return

        target = self.guess_numbers[key]

        if number == target:
            await ctx.send(f"Correct. The number was **{target}**.")
            del self.guess_numbers[key]
        elif number < target:
            await ctx.send("Too low.")
        else:
            await ctx.send("Too high.")

    @commands.command(help="Start a hangman game.")
    async def hangman(self, ctx):
        word = random.choice(self.hangman_words)
        self.hangman_games[ctx.channel.id] = {
            "word": word,
            "guessed": set(),
            "tries_left": 6
        }

        game = self.hangman_games[ctx.channel.id]
        await ctx.send(
            "**Hangman started.**\n"
            f"{self.render_hangman(game['word'], game['guessed'], game['tries_left'])}\n\n"
            "Guess with `!letter <a>`"
        )

    @commands.command(help="Guess a letter in hangman.")
    async def letter(self, ctx, guess: str):
        if ctx.channel.id not in self.hangman_games:
            await ctx.send("There is no active hangman game in this channel.")
            return

        guess = guess.lower().strip()

        if len(guess) != 1 or not guess.isalpha():
            await ctx.send("Guess one letter only.")
            return

        game = self.hangman_games[ctx.channel.id]

        if guess in game["guessed"]:
            await ctx.send("That letter was already guessed.")
            return

        game["guessed"].add(guess)

        if guess not in game["word"]:
            game["tries_left"] -= 1

        if all(letter in game["guessed"] for letter in game["word"]):
            await ctx.send(
                f"{self.render_hangman(game['word'], game['guessed'], game['tries_left'])}\n\n"
                f"You won. The word was **{game['word']}**."
            )
            del self.hangman_games[ctx.channel.id]
            return

        if game["tries_left"] <= 0:
            await ctx.send(
                f"{self.render_hangman(game['word'], game['guessed'], game['tries_left'])}\n\n"
                f"You lost. The word was **{game['word']}**."
            )
            del self.hangman_games[ctx.channel.id]
            return

        await ctx.send(self.render_hangman(game["word"], game["guessed"], game["tries_left"]))

    @commands.command(help="Start tic tac toe against the bot. Use positions 1-9.")
    async def tictactoe(self, ctx):
        self.ttt_games[ctx.channel.id] = {
            "board": [""] * 9,
            "player_id": ctx.author.id
        }

        await ctx.send(
            "**Tic Tac Toe started.**\n"
            "Use `!place <1-9>`\n\n"
            "Board positions:\n"
            "1 2 3\n4 5 6\n7 8 9\n\n"
            f"{self.render_board(self.ttt_games[ctx.channel.id]['board'])}"
        )

    @commands.command(help="Place your mark in tic tac toe.")
    async def place(self, ctx, position: int):
        if ctx.channel.id not in self.ttt_games:
            await ctx.send("There is no active tic tac toe game in this channel.")
            return

        game = self.ttt_games[ctx.channel.id]

        if ctx.author.id != game["player_id"]:
            await ctx.send("Only the person who started the game can play this round.")
            return

        if position < 1 or position > 9:
            await ctx.send("Choose a position from 1 to 9.")
            return

        board = game["board"]
        index = position - 1

        if board[index] != "":
            await ctx.send("That spot is already taken.")
            return

        board[index] = "X"

        winner = self.check_winner(board)
        if winner == "X":
            await ctx.send(f"{self.render_board(board)}\n\nYou win.")
            del self.ttt_games[ctx.channel.id]
            return
        if winner == "draw":
            await ctx.send(f"{self.render_board(board)}\n\nIt's a draw.")
            del self.ttt_games[ctx.channel.id]
            return

        open_spots = [i for i, cell in enumerate(board) if cell == ""]
        bot_move = random.choice(open_spots)
        board[bot_move] = "O"

        winner = self.check_winner(board)
        if winner == "O":
            await ctx.send(f"{self.render_board(board)}\n\nI win.")
            del self.ttt_games[ctx.channel.id]
            return
        if winner == "draw":
            await ctx.send(f"{self.render_board(board)}\n\nIt's a draw.")
            del self.ttt_games[ctx.channel.id]
            return

        await ctx.send(f"{self.render_board(board)}")

    @commands.command(help="Fight another user for fun.")
    async def fight(self, ctx, member=None):
        target = member if member else "a random NPC"
        attacks = [
            "hit with a folding chair",
            "threw a keyboard",
            "launched a dramatic flying elbow",
            "used emotional damage",
            "summoned chaotic energy",
            "pressed the self-destruct button"
        ]
        finisher = random.choice(attacks)
        winner = random.choice([ctx.author.mention, str(target)])
        await ctx.send(
            f"**Fight Night**\n"
            f"{ctx.author.mention} fought {target}.\n"
            f"Someone {finisher}.\n"
            f"Winner: **{winner}**"
        )

    @commands.command(name="8ball", help="Ask the magic 8-ball a question.")
    async def eightball(self, ctx, *, question: str):
        responses = [
            "Yes.",
            "No.",
            "Definitely.",
            "Absolutely not.",
            "Ask again later.",
            "The odds look good.",
            "Not looking great.",
            "Without a doubt.",
            "That would be a terrible idea.",
            "Trust me, no."
        ]
        await ctx.send(
            f"Question: **{question}**\n"
            f"Answer: **{random.choice(responses)}**"
        )

    @commands.command(help="Show all game commands.")
    async def gamehelp(self, ctx):
        await ctx.send(
            "**Game Commands**\n"
            "!rps <rock/paper/scissors>\n"
            "!coinflip\n"
            "!roll [sides]\n"
            "!trivia\n"
            "!answer <your answer>\n"
            "!guess\n"
            "!myguess <number>\n"
            "!hangman\n"
            "!letter <letter>\n"
            "!tictactoe\n"
            "!place <1-9>\n"
            "!fight [@user]\n"
            "!8ball <question>\n"
            "!gamehelp"
        )


async def setup(bot):
    await bot.add_cog(Games(bot))