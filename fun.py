import os
import json
import random
import discord
from discord.ext import commands

ECONOMY_FILE = "economy.json"


# =========================
# ECONOMY HELPERS
# =========================
def load_economy():
    if not os.path.exists(ECONOMY_FILE):
        with open(ECONOMY_FILE, "w", encoding="utf-8") as f:
            json.dump({}, f, indent=4)
    with open(ECONOMY_FILE, "r", encoding="utf-8") as f:
        return json.load(f)


def save_economy(data):
    with open(ECONOMY_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=4)


def ensure_user(data, user_id: str):
    if user_id not in data:
        data[user_id] = {
            "coins": 0,
            "bank": 0,
            "last_daily": 0,
            "last_work": 0,
            "last_crime": 0,
            "last_beg": 0,
        }


def award_coins(user_id: int, amount: int):
    data = load_economy()
    uid = str(user_id)
    ensure_user(data, uid)
    data[uid]["coins"] += amount
    save_economy(data)


# =========================
# TIC TAC TOE UI
# =========================
class TicTacToeButton(discord.ui.Button):
    def __init__(self, x: int, y: int):
        super().__init__(style=discord.ButtonStyle.secondary, label="\u200b", row=y)
        self.x = x
        self.y = y

    async def callback(self, interaction: discord.Interaction):
        view: "TicTacToeView" = self.view

        if interaction.user.id not in (view.player_x.id, view.player_o.id):
            await interaction.response.send_message("This is not your match.", ephemeral=True)
            return

        if interaction.user.id != view.current_player.id:
            await interaction.response.send_message("It is not your turn.", ephemeral=True)
            return

        if view.board[self.y][self.x] != " ":
            await interaction.response.send_message("That spot is already taken.", ephemeral=True)
            return

        symbol = "X" if interaction.user.id == view.player_x.id else "O"
        view.board[self.y][self.x] = symbol
        self.label = symbol
        self.disabled = True
        self.style = discord.ButtonStyle.danger if symbol == "X" else discord.ButtonStyle.success

        winner = view.check_winner()
        if winner:
            for child in view.children:
                child.disabled = True

            reward = 120
            award_coins(winner.id, reward)

            await interaction.response.edit_message(
                content=(
                    f"**Tic Tac Toe**\n"
                    f"{winner.mention} wins and earned **{reward:,} Spring Coins**."
                ),
                view=view,
            )
            view.stop()
            return

        if view.is_draw():
            for child in view.children:
                child.disabled = True
            await interaction.response.edit_message(
                content="**Tic Tac Toe**\nIt ended in a draw.",
                view=view,
            )
            view.stop()
            return

        view.current_player = view.player_o if view.current_player.id == view.player_x.id else view.player_x
        await interaction.response.edit_message(
            content=f"**Tic Tac Toe**\n{view.current_player.mention}'s turn.",
            view=view,
        )


class TicTacToeView(discord.ui.View):
    def __init__(self, player_x: discord.Member, player_o: discord.Member):
        super().__init__(timeout=180)
        self.player_x = player_x
        self.player_o = player_o
        self.current_player = player_x
        self.board = [[" " for _ in range(3)] for _ in range(3)]

        for y in range(3):
            for x in range(3):
                self.add_item(TicTacToeButton(x, y))

    def check_winner(self):
        lines = []

        for row in self.board:
            lines.append(row)

        for col in range(3):
            lines.append([self.board[row][col] for row in range(3)])

        lines.append([self.board[0][0], self.board[1][1], self.board[2][2]])
        lines.append([self.board[0][2], self.board[1][1], self.board[2][0]])

        for line in lines:
            if line == ["X", "X", "X"]:
                return self.player_x
            if line == ["O", "O", "O"]:
                return self.player_o
        return None

    def is_draw(self):
        return all(cell != " " for row in self.board for cell in row)

    async def on_timeout(self):
        for child in self.children:
            child.disabled = True


# =========================
# BLACKJACK
# =========================
SUITS = ["♠", "♥", "♦", "♣"]
RANKS = ["A", "2", "3", "4", "5", "6", "7", "8", "9", "10", "J", "Q", "K"]


def make_deck():
    deck = [f"{rank}{suit}" for suit in SUITS for rank in RANKS]
    random.shuffle(deck)
    return deck


def card_value(card: str) -> int:
    rank = card[:-1]
    if rank in ["J", "Q", "K"]:
        return 10
    if rank == "A":
        return 11
    return int(rank)


def hand_value(hand):
    value = sum(card_value(card) for card in hand)
    aces = sum(1 for card in hand if card[:-1] == "A")
    while value > 21 and aces:
        value -= 10
        aces -= 1
    return value


def format_hand(hand, hide_first=False):
    if hide_first and len(hand) > 1:
        shown = ["🂠"] + hand[1:]
        return " ".join(shown)
    return " ".join(hand)


class BlackjackView(discord.ui.View):
    def __init__(self, cog: "Fun", player_id: int):
        super().__init__(timeout=120)
        self.cog = cog
        self.player_id = player_id

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        if interaction.user.id != self.player_id:
            await interaction.response.send_message("This is not your blackjack game.", ephemeral=True)
            return False
        return True

    @discord.ui.button(label="Hit", style=discord.ButtonStyle.primary)
    async def hit_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        result = self.cog.blackjack_hit(self.player_id)
        if result is None:
            await interaction.response.send_message("No active blackjack game found.", ephemeral=True)
            return
        text, finished = result
        if finished:
            for child in self.children:
                child.disabled = True
        await interaction.response.edit_message(content=text, view=self)

    @discord.ui.button(label="Stand", style=discord.ButtonStyle.success)
    async def stand_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        result = self.cog.blackjack_stand(self.player_id)
        if result is None:
            await interaction.response.send_message("No active blackjack game found.", ephemeral=True)
            return
        text, _ = result
        for child in self.children:
            child.disabled = True
        await interaction.response.edit_message(content=text, view=self)

    async def on_timeout(self):
        self.cog.blackjack_games.pop(self.player_id, None)
        for child in self.children:
            child.disabled = True


# =========================
# UNO
# =========================
UNO_COLORS = ["Red", "Blue", "Green", "Yellow"]
UNO_NUMBERS = [str(i) for i in range(10)]
UNO_ACTIONS = ["Skip", "Reverse", "Draw Two"]


def build_uno_deck():
    deck = []
    for color in UNO_COLORS:
        for number in UNO_NUMBERS:
            deck.append(f"{color} {number}")
            if number != "0":
                deck.append(f"{color} {number}")
        for action in UNO_ACTIONS:
            deck.append(f"{color} {action}")
            deck.append(f"{color} {action}")
    deck += [
        "Wild", "Wild", "Wild", "Wild",
        "Wild Draw Four", "Wild Draw Four", "Wild Draw Four", "Wild Draw Four"
    ]
    random.shuffle(deck)
    return deck


def uno_card_matches(card: str, top_card: str, forced_color: str | None):
    if forced_color:
        return card.startswith(forced_color) or card.startswith("Wild")

    if card.startswith("Wild"):
        return True

    if top_card.startswith("Wild"):
        return True

    card_parts = card.split(" ", 1)
    top_parts = top_card.split(" ", 1)

    if len(card_parts) == 2 and len(top_parts) == 2:
        card_color, card_value = card_parts
        top_color, top_value = top_parts
        return card_color == top_color or card_value == top_value

    return False


class UnoView(discord.ui.View):
    def __init__(self, cog: "Fun", player_id: int):
        super().__init__(timeout=180)
        self.cog = cog
        self.player_id = player_id

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        if interaction.user.id != self.player_id:
            await interaction.response.send_message("This is not your Uno game.", ephemeral=True)
            return False
        return True

    @discord.ui.button(label="Play First Valid Card", style=discord.ButtonStyle.primary)
    async def play_valid(self, interaction: discord.Interaction, button: discord.ui.Button):
        result = self.cog.uno_play_first_valid(self.player_id)
        if result is None:
            await interaction.response.send_message("No active Uno game found.", ephemeral=True)
            return
        text, finished = result
        if finished:
            for child in self.children:
                child.disabled = True
        await interaction.response.edit_message(content=text, view=self)

    @discord.ui.button(label="Draw Card", style=discord.ButtonStyle.secondary)
    async def draw_card(self, interaction: discord.Interaction, button: discord.ui.Button):
        result = self.cog.uno_draw(self.player_id)
        if result is None:
            await interaction.response.send_message("No active Uno game found.", ephemeral=True)
            return
        text, finished = result
        if finished:
            for child in self.children:
                child.disabled = True
        await interaction.response.edit_message(content=text, view=self)

    async def on_timeout(self):
        self.cog.uno_games.pop(self.player_id, None)
        for child in self.children:
            child.disabled = True


# =========================
# MAIN COG
# =========================
class Fun(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.blackjack_games = {}
        self.uno_games = {}

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

    # =========================
    # BLACKJACK HELPERS
    # =========================
    def blackjack_status_text(self, user_id: int):
        game = self.blackjack_games[user_id]
        player_total = hand_value(game["player"])
        dealer_show = format_hand(game["dealer"], hide_first=True)

        return (
            "**Blackjack**\n"
            f"Dealer: {dealer_show}\n"
            f"You: {format_hand(game['player'])} ({player_total})\n\n"
            "Press **Hit** or **Stand**."
        )

    def blackjack_finish_text(self, user_id: int):
        game = self.blackjack_games[user_id]
        player_total = hand_value(game["player"])
        dealer_total = hand_value(game["dealer"])

        while dealer_total < 17:
            game["dealer"].append(game["deck"].pop())
            dealer_total = hand_value(game["dealer"])

        reward_text = ""
        if dealer_total > 21:
            reward = 100
            award_coins(user_id, reward)
            result = "Dealer busted. You win."
            reward_text = f"\n**Reward:** {reward:,} Spring Coins"
        elif player_total > dealer_total:
            reward = 100
            award_coins(user_id, reward)
            result = "You win."
            reward_text = f"\n**Reward:** {reward:,} Spring Coins"
        elif dealer_total > player_total:
            result = "Dealer wins."
        else:
            result = "Push. It is a tie."

        text = (
            "**Blackjack - Final**\n"
            f"Dealer: {format_hand(game['dealer'])} ({dealer_total})\n"
            f"You: {format_hand(game['player'])} ({player_total})\n\n"
            f"**{result}**{reward_text}"
        )

        self.blackjack_games.pop(user_id, None)
        return text

    def blackjack_hit(self, user_id: int):
        game = self.blackjack_games.get(user_id)
        if not game:
            return None

        game["player"].append(game["deck"].pop())
        total = hand_value(game["player"])

        if total > 21:
            dealer_total = hand_value(game["dealer"])
            text = (
                "**Blackjack - Final**\n"
                f"Dealer: {format_hand(game['dealer'])} ({dealer_total})\n"
                f"You: {format_hand(game['player'])} ({total})\n\n"
                "**Bust. Dealer wins.**"
            )
            self.blackjack_games.pop(user_id, None)
            return text, True

        return self.blackjack_status_text(user_id), False

    def blackjack_stand(self, user_id: int):
        game = self.blackjack_games.get(user_id)
        if not game:
            return None
        return self.blackjack_finish_text(user_id), True

    # =========================
    # UNO HELPERS
    # =========================
    def uno_text(self, user_id: int):
        game = self.uno_games[user_id]
        player_hand = ", ".join(game["player"]) if game["player"] else "No cards"
        bot_count = len(game["bot"])
        forced = f" | Active color: {game['forced_color']}" if game["forced_color"] else ""

        return (
            "**Uno vs SpringBot**\n"
            f"Top card: {game['top']}{forced}\n"
            f"Your cards ({len(game['player'])}): {player_hand}\n"
            f"SpringBot cards: {bot_count}\n\n"
            "Press **Play First Valid Card** or **Draw Card**."
        )

    def uno_bot_turn(self, game):
        log = []

        while True:
            playable = [card for card in game["bot"] if uno_card_matches(card, game["top"], game["forced_color"])]

            if not playable:
                if not game["deck"]:
                    game["deck"] = build_uno_deck()
                drawn = game["deck"].pop()
                game["bot"].append(drawn)
                log.append("SpringBot drew a card.")
                playable = [card for card in game["bot"] if uno_card_matches(card, game["top"], game["forced_color"])]
                if not playable:
                    break

            card = playable[0]
            game["bot"].remove(card)
            game["top"] = card
            game["forced_color"] = None
            log.append(f"SpringBot played **{card}**.")

            if card.startswith("Wild Draw Four"):
                chosen = random.choice(UNO_COLORS)
                game["forced_color"] = chosen
                for _ in range(4):
                    if not game["deck"]:
                        game["deck"] = build_uno_deck()
                    game["player"].append(game["deck"].pop())
                log.append(f"SpringBot changed the color to **{chosen}** and you drew 4 cards.")
                break

            if card == "Wild":
                chosen = random.choice(UNO_COLORS)
                game["forced_color"] = chosen
                log.append(f"SpringBot changed the color to **{chosen}**.")
                break

            if "Draw Two" in card:
                for _ in range(2):
                    if not game["deck"]:
                        game["deck"] = build_uno_deck()
                    game["player"].append(game["deck"].pop())
                log.append("You drew 2 cards.")
                break

            if "Skip" in card or "Reverse" in card:
                log.append("SpringBot took the momentum and your turn was skipped.")
                continue

            break

        return log

    def uno_play_first_valid(self, user_id: int):
        game = self.uno_games.get(user_id)
        if not game:
            return None

        playable = [card for card in game["player"] if uno_card_matches(card, game["top"], game["forced_color"])]
        if not playable:
            return self.uno_text(user_id) + "\n\nYou had no valid card to play.", False

        card = playable[0]
        game["player"].remove(card)
        game["top"] = card
        game["forced_color"] = None
        log = [f"You played **{card}**."]

        if not game["player"]:
            reward = 150
            award_coins(user_id, reward)
            text = (
                "**Uno vs SpringBot**\n"
                f"Top card: {game['top']}\n\n"
                f"**You win and earned {reward:,} Spring Coins.**"
            )
            self.uno_games.pop(user_id, None)
            return text, True

        if card.startswith("Wild Draw Four"):
            chosen = random.choice(UNO_COLORS)
            game["forced_color"] = chosen
            for _ in range(4):
                if not game["deck"]:
                    game["deck"] = build_uno_deck()
                game["bot"].append(game["deck"].pop())
            log.append(f"You changed the color to **{chosen}**.")
            log.append("SpringBot drew 4 cards.")
        elif card == "Wild":
            chosen = random.choice(UNO_COLORS)
            game["forced_color"] = chosen
            log.append(f"You changed the color to **{chosen}**.")
        elif "Draw Two" in card:
            for _ in range(2):
                if not game["deck"]:
                    game["deck"] = build_uno_deck()
                game["bot"].append(game["deck"].pop())
            log.append("SpringBot drew 2 cards.")
        elif "Skip" in card or "Reverse" in card:
            log.append("SpringBot lost its turn.")
            text = self.uno_text(user_id) + "\n\n" + "\n".join(log)
            return text, False

        bot_log = self.uno_bot_turn(game)
        log.extend(bot_log)

        if not game["bot"]:
            text = (
                "**Uno vs SpringBot**\n"
                f"Top card: {game['top']}\n\n"
                "**SpringBot wins.**"
            )
            self.uno_games.pop(user_id, None)
            return text, True

        return self.uno_text(user_id) + "\n\n" + "\n".join(log), False

    def uno_draw(self, user_id: int):
        game = self.uno_games.get(user_id)
        if not game:
            return None

        if not game["deck"]:
            game["deck"] = build_uno_deck()

        drawn = game["deck"].pop()
        game["player"].append(drawn)
        log = [f"You drew **{drawn}**."]

        if uno_card_matches(drawn, game["top"], game["forced_color"]):
            log.append("That card is playable. Use **Play First Valid Card** to play it.")

        bot_log = self.uno_bot_turn(game)
        log.extend(bot_log)

        if not game["bot"]:
            text = (
                "**Uno vs SpringBot**\n"
                f"Top card: {game['top']}\n\n"
                "**SpringBot wins.**"
            )
            self.uno_games.pop(user_id, None)
            return text, True

        return self.uno_text(user_id) + "\n\n" + "\n".join(log), False

    # =========================
    # EXISTING FUN COMMANDS
    # =========================
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
        await ctx.send(f"Question: {question}\nAnswer: **{random.choice(responses)}**")

    # =========================
    # GAME COMMANDS
    # =========================
    @commands.command(help="Start a tic tac toe match against another member.")
    async def tictactoe(self, ctx, member: discord.Member):
        if member.bot:
            await ctx.send("You cannot challenge a bot to tic tac toe.")
            return
        if member.id == ctx.author.id:
            await ctx.send("You cannot play tic tac toe against yourself.")
            return

        first, second = random.sample([ctx.author, member], 2)
        view = TicTacToeView(first, second)
        await ctx.send(
            f"**Tic Tac Toe**\n{first.mention} is **X**\n{second.mention} is **O**\n\n{view.current_player.mention}'s turn.",
            view=view,
        )

    @commands.command(help="Start a blackjack game against the dealer.")
    async def blackjack(self, ctx):
        if ctx.author.id in self.blackjack_games:
            await ctx.send("You already have an active blackjack game.")
            return

        deck = make_deck()
        player = [deck.pop(), deck.pop()]
        dealer = [deck.pop(), deck.pop()]

        self.blackjack_games[ctx.author.id] = {
            "deck": deck,
            "player": player,
            "dealer": dealer,
        }

        player_total = hand_value(player)
        dealer_total = hand_value(dealer)

        if player_total == 21 and dealer_total == 21:
            text = (
                "**Blackjack - Final**\n"
                f"Dealer: {format_hand(dealer)} ({dealer_total})\n"
                f"You: {format_hand(player)} ({player_total})\n\n"
                "**Double blackjack. Push.**"
            )
            self.blackjack_games.pop(ctx.author.id, None)
            await ctx.send(text)
            return

        if player_total == 21:
            reward = 150
            award_coins(ctx.author.id, reward)
            text = (
                "**Blackjack - Final**\n"
                f"Dealer: {format_hand(dealer)} ({dealer_total})\n"
                f"You: {format_hand(player)} ({player_total})\n\n"
                f"**Blackjack. You win.**\n**Reward:** {reward:,} Spring Coins"
            )
            self.blackjack_games.pop(ctx.author.id, None)
            await ctx.send(text)
            return

        if dealer_total == 21:
            text = (
                "**Blackjack - Final**\n"
                f"Dealer: {format_hand(dealer)} ({dealer_total})\n"
                f"You: {format_hand(player)} ({player_total})\n\n"
                "**Dealer blackjack. You lose.**"
            )
            self.blackjack_games.pop(ctx.author.id, None)
            await ctx.send(text)
            return

        view = BlackjackView(self, ctx.author.id)
        await ctx.send(self.blackjack_status_text(ctx.author.id), view=view)

    @commands.command(help="Hit in your active blackjack game.")
    async def hit(self, ctx):
        result = self.blackjack_hit(ctx.author.id)
        if result is None:
            await ctx.send("You do not have an active blackjack game.")
            return
        text, _ = result
        await ctx.send(text)

    @commands.command(help="Stand in your active blackjack game.")
    async def stand(self, ctx):
        result = self.blackjack_stand(ctx.author.id)
        if result is None:
            await ctx.send("You do not have an active blackjack game.")
            return
        text, _ = result
        await ctx.send(text)

    @commands.command(help="Start a simplified Uno game against SpringBot.")
    async def uno(self, ctx):
        if ctx.author.id in self.uno_games:
            await ctx.send("You already have an active Uno game.")
            return

        deck = build_uno_deck()
        player = [deck.pop() for _ in range(7)]
        bot_hand = [deck.pop() for _ in range(7)]
        top = deck.pop()

        while top.startswith("Wild"):
            deck.insert(0, top)
            random.shuffle(deck)
            top = deck.pop()

        self.uno_games[ctx.author.id] = {
            "deck": deck,
            "player": player,
            "bot": bot_hand,
            "top": top,
            "forced_color": None,
        }

        view = UnoView(self, ctx.author.id)
        await ctx.send(self.uno_text(ctx.author.id), view=view)

    @commands.command(help="Play the first valid Uno card from your hand.")
    async def unoplay(self, ctx):
        result = self.uno_play_first_valid(ctx.author.id)
        if result is None:
            await ctx.send("You do not have an active Uno game.")
            return
        text, _ = result
        await ctx.send(text)

    @commands.command(help="Draw a card in your Uno game.")
    async def unodraw(self, ctx):
        result = self.uno_draw(ctx.author.id)
        if result is None:
            await ctx.send("You do not have an active Uno game.")
            return
        text, _ = result
        await ctx.send(text)

    @commands.command(help="Show your current Uno hand and top card.")
    async def unohand(self, ctx):
        game = self.uno_games.get(ctx.author.id)
        if not game:
            await ctx.send("You do not have an active Uno game.")
            return
        await ctx.send(self.uno_text(ctx.author.id))

    @commands.command(help="Ends your active blackjack or Uno game.")
    async def endgame(self, ctx):
        ended = False

        if ctx.author.id in self.blackjack_games:
            self.blackjack_games.pop(ctx.author.id, None)
            ended = True

        if ctx.author.id in self.uno_games:
            self.uno_games.pop(ctx.author.id, None)
            ended = True

        if ended:
            await ctx.send("Your active game was ended.")
        else:
            await ctx.send("You do not have an active game right now.")

    @commands.command(help="Shows all fun and game commands.")
    async def funhelp(self, ctx):
        await ctx.send(
            "**SpringBot Fun + Games**\n"
            "`!joke` - random funny joke\n"
            "`!roast [@user]` - random roast\n"
            "`!motivate` - fake motivation\n"
            "`!excuse` - random funny excuse\n"
            "`!brosaid` - bro said joke\n"
            "`!pickup` - parody pickup line\n"
            "`!coinflip` - flip a coin\n"
            "`!roll` - roll a die\n"
            "`!say <message>` - make the bot repeat you\n"
            "`!eightball <question>` - chaotic magic 8-ball\n"
            "`!tictactoe @user` - play tic tac toe for coins\n"
            "`!blackjack` - start blackjack for coins\n"
            "`!hit` - hit in blackjack\n"
            "`!stand` - stand in blackjack\n"
            "`!uno` - start Uno vs SpringBot for coins\n"
            "`!unoplay` - play first valid Uno card\n"
            "`!unodraw` - draw a card in Uno\n"
            "`!unohand` - show your Uno hand\n"
            "`!endgame` - end your current game\n"
            "`!funhelp` - show this list"
        )


async def setup(bot):
    await bot.add_cog(Fun(bot))