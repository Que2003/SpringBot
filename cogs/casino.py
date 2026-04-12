import os
import json
import random

from discord.ext import commands


class Casino(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.file_path = "economy.json"
        self.currency_name = "SpringCoins"
        self.blackjack_games = {}
        self.data = self.load_data()

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

    def get_user(self, guild_id: int, user_id: int):
        guild_key = str(guild_id)
        user_key = str(user_id)

        if guild_key not in self.data:
            self.data[guild_key] = {}

        if user_key not in self.data[guild_key]:
            self.data[guild_key][user_key] = {
                "balance": 500,
                "last_daily": None,
                "last_work": None,
                "wins": 0,
                "losses": 0
            }

        return self.data[guild_key][user_key]

    def get_balance(self, guild_id: int, user_id: int):
        return int(self.get_user(guild_id, user_id)["balance"])

    def add_balance(self, guild_id: int, user_id: int, amount: int):
        user = self.get_user(guild_id, user_id)
        user["balance"] = max(0, int(user["balance"]) + int(amount))
        self.save_data()

    def record_win(self, guild_id: int, user_id: int):
        user = self.get_user(guild_id, user_id)
        user["wins"] = int(user.get("wins", 0)) + 1
        self.save_data()

    def record_loss(self, guild_id: int, user_id: int):
        user = self.get_user(guild_id, user_id)
        user["losses"] = int(user.get("losses", 0)) + 1
        self.save_data()

    def draw_card(self):
        deck = [2, 3, 4, 5, 6, 7, 8, 9, 10, 10, 10, 10, 11]
        return random.choice(deck)

    def hand_value(self, hand):
        total = sum(hand)
        aces = hand.count(11)

        while total > 21 and aces > 0:
            total -= 10
            aces -= 1

        return total

    @commands.command(help="Bet on coinflip. Example: !coinflipbet 100 heads")
    async def coinflipbet(self, ctx, amount: int, choice: str):
        choice = choice.lower().strip()

        if choice not in ["heads", "tails"]:
            await ctx.send("Pick `heads` or `tails`.")
            return

        if amount <= 0:
            await ctx.send("Enter a valid bet amount.")
            return

        balance = self.get_balance(ctx.guild.id, ctx.author.id)
        if amount > balance:
            await ctx.send("You do not have enough SpringCoins.")
            return

        result = random.choice(["heads", "tails"])

        if choice == result:
            self.add_balance(ctx.guild.id, ctx.author.id, amount)
            self.record_win(ctx.guild.id, ctx.author.id)
            await ctx.send(
                f"The coin landed on **{result}**.\n"
                f"You won **{amount} {self.currency_name}**."
            )
        else:
            self.add_balance(ctx.guild.id, ctx.author.id, -amount)
            self.record_loss(ctx.guild.id, ctx.author.id)
            await ctx.send(
                f"The coin landed on **{result}**.\n"
                f"You lost **{amount} {self.currency_name}**."
            )

    @commands.command(help="Play slots. Example: !slots 100")
    async def slots(self, ctx, amount: int):
        if amount <= 0:
            await ctx.send("Enter a valid bet amount.")
            return

        balance = self.get_balance(ctx.guild.id, ctx.author.id)
        if amount > balance:
            await ctx.send("You do not have enough SpringCoins.")
            return

        symbols = ["🍒", "🍋", "💎", "7️⃣", "🍀", "🔔"]
        result = [random.choice(symbols) for _ in range(3)]

        payout = 0
        if result[0] == result[1] == result[2]:
            if result[0] == "💎":
                payout = amount * 6
            elif result[0] == "7️⃣":
                payout = amount * 5
            else:
                payout = amount * 4
        elif result[0] == result[1] or result[1] == result[2] or result[0] == result[2]:
            payout = amount * 2

        if payout > 0:
            profit = payout - amount
            self.add_balance(ctx.guild.id, ctx.author.id, profit)
            self.record_win(ctx.guild.id, ctx.author.id)
            await ctx.send(
                f"**{' '.join(result)}**\n"
                f"You won **{profit} {self.currency_name}** profit."
            )
        else:
            self.add_balance(ctx.guild.id, ctx.author.id, -amount)
            self.record_loss(ctx.guild.id, ctx.author.id)
            await ctx.send(
                f"**{' '.join(result)}**\n"
                f"You lost **{amount} {self.currency_name}**."
            )

    @commands.command(help="Start a blackjack game. Example: !blackjack 100")
    async def blackjack(self, ctx, amount: int):
        if amount <= 0:
            await ctx.send("Enter a valid bet amount.")
            return

        balance = self.get_balance(ctx.guild.id, ctx.author.id)
        if amount > balance:
            await ctx.send("You do not have enough SpringCoins.")
            return

        player = [self.draw_card(), self.draw_card()]
        dealer = [self.draw_card(), self.draw_card()]

        self.blackjack_games[ctx.author.id] = {
            "bet": amount,
            "player": player,
            "dealer": dealer,
            "guild_id": ctx.guild.id
        }

        player_total = self.hand_value(player)

        if player_total == 21:
            winnings = int(amount * 1.5)
            self.add_balance(ctx.guild.id, ctx.author.id, winnings)
            self.record_win(ctx.guild.id, ctx.author.id)
            del self.blackjack_games[ctx.author.id]
            await ctx.send(
                f"Your hand: **{player}** = **{player_total}**\n"
                f"Blackjack. You won **{winnings} {self.currency_name}**."
            )
            return

        await ctx.send(
            f"Your hand: **{player}** = **{player_total}**\n"
            f"Dealer shows: **[{dealer[0]}, ?]**\n"
            "Use `!hit` or `!stand`."
        )

    @commands.command(help="Draw another card in blackjack.")
    async def hit(self, ctx):
        if ctx.author.id not in self.blackjack_games:
            await ctx.send("You do not have an active blackjack game.")
            return

        game = self.blackjack_games[ctx.author.id]
        game["player"].append(self.draw_card())

        total = self.hand_value(game["player"])

        if total > 21:
            self.add_balance(game["guild_id"], ctx.author.id, -game["bet"])
            self.record_loss(game["guild_id"], ctx.author.id)
            await ctx.send(
                f"Your hand: **{game['player']}** = **{total}**\n"
                f"You busted and lost **{game['bet']} {self.currency_name}**."
            )
            del self.blackjack_games[ctx.author.id]
            return

        await ctx.send(
            f"Your hand: **{game['player']}** = **{total}**\n"
            "Use `!hit` or `!stand`."
        )

    @commands.command(help="Stand in blackjack.")
    async def stand(self, ctx):
        if ctx.author.id not in self.blackjack_games:
            await ctx.send("You do not have an active blackjack game.")
            return

        game = self.blackjack_games[ctx.author.id]
        player_total = self.hand_value(game["player"])

        while self.hand_value(game["dealer"]) < 17:
            game["dealer"].append(self.draw_card())

        dealer_total = self.hand_value(game["dealer"])
        bet = game["bet"]

        if dealer_total > 21 or player_total > dealer_total:
            self.add_balance(game["guild_id"], ctx.author.id, bet)
            self.record_win(game["guild_id"], ctx.author.id)
            result = f"You won **{bet} {self.currency_name}**."
        elif dealer_total == player_total:
            result = "Push. Nobody wins."
        else:
            self.add_balance(game["guild_id"], ctx.author.id, -bet)
            self.record_loss(game["guild_id"], ctx.author.id)
            result = f"You lost **{bet} {self.currency_name}**."

        await ctx.send(
            f"Your hand: **{game['player']}** = **{player_total}**\n"
            f"Dealer hand: **{game['dealer']}** = **{dealer_total}**\n"
            f"{result}"
        )

        del self.blackjack_games[ctx.author.id]

    @commands.command(help="Try to rob another user.")
    async def rob(self, ctx, member: commands.MemberConverter = None):
        if member is None:
            await ctx.send("Mention someone to rob.")
            return

        if member.bot:
            await ctx.send("You cannot rob bots.")
            return

        if member.id == ctx.author.id:
            await ctx.send("You cannot rob yourself.")
            return

        attacker_balance = self.get_balance(ctx.guild.id, ctx.author.id)
        victim_balance = self.get_balance(ctx.guild.id, member.id)

        if attacker_balance < 100:
            await ctx.send("You need at least **100 SpringCoins** to attempt a robbery.")
            return

        if victim_balance < 50:
            await ctx.send("That user is too broke to rob.")
            return

        success = random.randint(1, 100) <= 40

        if success:
            stolen = min(random.randint(50, 200), victim_balance)
            self.add_balance(ctx.guild.id, member.id, -stolen)
            self.add_balance(ctx.guild.id, ctx.author.id, stolen)
            self.record_win(ctx.guild.id, ctx.author.id)
            await ctx.send(
                f"You robbed {member.mention} and stole **{stolen} {self.currency_name}**."
            )
        else:
            penalty = random.randint(25, 100)
            self.add_balance(ctx.guild.id, ctx.author.id, -penalty)
            self.record_loss(ctx.guild.id, ctx.author.id)
            await ctx.send(
                f"Robbery failed. You got caught and lost **{penalty} {self.currency_name}**."
            )

    @commands.command(help="Show casino stats.")
    async def casinostats(self, ctx, member: commands.MemberConverter = None):
        member = member or ctx.author
        user = self.get_user(ctx.guild.id, member.id)
        wins = int(user.get("wins", 0))
        losses = int(user.get("losses", 0))

        await ctx.send(
            f"**Casino Stats for {member.display_name}**\n"
            f"Wins: **{wins}**\n"
            f"Losses: **{losses}**\n"
            f"Balance: **{user.get('balance', 0)} {self.currency_name}**"
        )

    @commands.command(help="Show casino commands.")
    async def casinohelp(self, ctx):
        await ctx.send(
            "**Casino Commands**\n"
            "!coinflipbet <amount> <heads/tails>\n"
            "!slots <amount>\n"
            "!blackjack <amount>\n"
            "!hit\n"
            "!stand\n"
            "!rob @user\n"
            "!casinostats [@user]\n"
            "!casinohelp"
        )


async def setup(bot):
    await bot.add_cog(Casino(bot))