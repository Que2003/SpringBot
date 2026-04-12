import os
import json
import random
import time
import discord
from discord.ext import commands

ECONOMY_FILE = "economy.json"


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


def format_coins(amount: int) -> str:
    return f"{amount:,} Spring Coins"


class Economy(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.command(help="Check your Spring Coin balance.")
    async def balance(self, ctx, member: discord.Member = None):
        target = member or ctx.author
        data = load_economy()
        user_id = str(target.id)
        ensure_user(data, user_id)
        save_economy(data)

        wallet = data[user_id]["coins"]
        bank = data[user_id]["bank"]

        embed = discord.Embed(title=f"{target.display_name}'s Balance")
        embed.add_field(name="Wallet", value=f"{wallet:,} Spring Coins", inline=True)
        embed.add_field(name="Bank", value=f"{bank:,} Spring Coins", inline=True)
        embed.add_field(name="Total", value=f"{wallet + bank:,} Spring Coins", inline=False)
        await ctx.send(embed=embed)

    @commands.command(help="Claim your daily Spring Coins.")
    async def daily(self, ctx):
        data = load_economy()
        user_id = str(ctx.author.id)
        ensure_user(data, user_id)

        now = int(time.time())
        cooldown = 86400
        elapsed = now - data[user_id]["last_daily"]

        if elapsed < cooldown:
            remaining = cooldown - elapsed
            hours = remaining // 3600
            minutes = (remaining % 3600) // 60
            await ctx.send(f"You already claimed your daily reward. Try again in **{hours}h {minutes}m**.")
            return

        reward = random.randint(200, 450)
        data[user_id]["coins"] += reward
        data[user_id]["last_daily"] = now
        save_economy(data)

        await ctx.send(f"{ctx.author.mention} claimed **{reward:,} Spring Coins** from `!daily`.")

    @commands.command(help="Work for Spring Coins.")
    async def work(self, ctx):
        jobs = [
            "fixed a broken router",
            "patched a server",
            "installed a switch",
            "ran cable through the walls",
            "reset a suspicious password",
            "cleaned malware off a laptop",
            "repaired a cracked phone",
            "built a gaming setup",
            "helped the help desk survive",
            "optimized a laggy PC",
        ]

        data = load_economy()
        user_id = str(ctx.author.id)
        ensure_user(data, user_id)

        now = int(time.time())
        cooldown = 3600
        elapsed = now - data[user_id]["last_work"]

        if elapsed < cooldown:
            remaining = cooldown - elapsed
            minutes = remaining // 60
            seconds = remaining % 60
            await ctx.send(f"You already worked recently. Try again in **{minutes}m {seconds}s**.")
            return

        reward = random.randint(80, 220)
        job = random.choice(jobs)
        data[user_id]["coins"] += reward
        data[user_id]["last_work"] = now
        save_economy(data)

        await ctx.send(f"{ctx.author.mention} {job} and earned **{reward:,} Spring Coins**.")

    @commands.command(help="Take a risky chance to earn or lose Spring Coins.")
    async def crime(self, ctx):
        success_lines = [
            "You pulled off a digital heist.",
            "You cracked the vault.",
            "You ran the play and got away clean.",
            "You snatched the loot and vanished.",
            "You hustled the underground market.",
        ]
        fail_lines = [
            "You got caught instantly.",
            "Security folded you.",
            "You left fingerprints everywhere.",
            "Your getaway plan was terrible.",
            "You tripped the alarm and lost everything.",
        ]

        data = load_economy()
        user_id = str(ctx.author.id)
        ensure_user(data, user_id)

        now = int(time.time())
        cooldown = 7200
        elapsed = now - data[user_id]["last_crime"]

        if elapsed < cooldown:
            remaining = cooldown - elapsed
            minutes = remaining // 60
            await ctx.send(f"`!crime` is on cooldown. Try again in **{minutes}m**.")
            return

        data[user_id]["last_crime"] = now

        if random.random() < 0.55:
            reward = random.randint(150, 500)
            data[user_id]["coins"] += reward
            save_economy(data)
            await ctx.send(f"{ctx.author.mention} {random.choice(success_lines)} You gained **{reward:,} Spring Coins**.")
        else:
            loss = random.randint(50, 250)
            loss = min(loss, data[user_id]["coins"])
            data[user_id]["coins"] -= loss
            save_economy(data)
            await ctx.send(f"{ctx.author.mention} {random.choice(fail_lines)} You lost **{loss:,} Spring Coins**.")

    @commands.command(help="Beg for a few Spring Coins.")
    async def beg(self, ctx):
        donors = [
            "a rich stranger",
            "a bored millionaire",
            "a mysterious trader",
            "a server legend",
            "a tired admin",
            "an NPC with pity",
        ]

        data = load_economy()
        user_id = str(ctx.author.id)
        ensure_user(data, user_id)

        now = int(time.time())
        cooldown = 1800
        elapsed = now - data[user_id]["last_beg"]

        if elapsed < cooldown:
            remaining = cooldown - elapsed
            minutes = remaining // 60
            seconds = remaining % 60
            await ctx.send(f"`!beg` is on cooldown. Try again in **{minutes}m {seconds}s**.")
            return

        reward = random.randint(15, 90)
        data[user_id]["coins"] += reward
        data[user_id]["last_beg"] = now
        save_economy(data)

        await ctx.send(f"{random.choice(donors)} gave {ctx.author.mention} **{reward:,} Spring Coins**.")

    @commands.command(help="Deposit Spring Coins into your bank.")
    async def deposit(self, ctx, amount: str):
        data = load_economy()
        user_id = str(ctx.author.id)
        ensure_user(data, user_id)

        wallet = data[user_id]["coins"]

        if amount.lower() == "all":
            amount_value = wallet
        else:
            if not amount.isdigit():
                await ctx.send("Use a number or `all`.")
                return
            amount_value = int(amount)

        if amount_value <= 0:
            await ctx.send("Deposit amount must be more than 0.")
            return

        if amount_value > wallet:
            await ctx.send("You do not have that many Spring Coins in your wallet.")
            return

        data[user_id]["coins"] -= amount_value
        data[user_id]["bank"] += amount_value
        save_economy(data)

        await ctx.send(f"{ctx.author.mention} deposited **{amount_value:,} Spring Coins** into the bank.")

    @commands.command(help="Withdraw Spring Coins from your bank.")
    async def withdraw(self, ctx, amount: str):
        data = load_economy()
        user_id = str(ctx.author.id)
        ensure_user(data, user_id)

        bank = data[user_id]["bank"]

        if amount.lower() == "all":
            amount_value = bank
        else:
            if not amount.isdigit():
                await ctx.send("Use a number or `all`.")
                return
            amount_value = int(amount)

        if amount_value <= 0:
            await ctx.send("Withdraw amount must be more than 0.")
            return

        if amount_value > bank:
            await ctx.send("You do not have that many Spring Coins in the bank.")
            return

        data[user_id]["bank"] -= amount_value
        data[user_id]["coins"] += amount_value
        save_economy(data)

        await ctx.send(f"{ctx.author.mention} withdrew **{amount_value:,} Spring Coins** from the bank.")

    @commands.command(help="Give Spring Coins to another user.")
    async def givecoins(self, ctx, member: discord.Member, amount: int):
        if member.bot:
            await ctx.send("You cannot give coins to bots.")
            return

        if member.id == ctx.author.id:
            await ctx.send("You cannot give coins to yourself.")
            return

        if amount <= 0:
            await ctx.send("Amount must be greater than 0.")
            return

        data = load_economy()
        giver_id = str(ctx.author.id)
        receiver_id = str(member.id)

        ensure_user(data, giver_id)
        ensure_user(data, receiver_id)

        if data[giver_id]["coins"] < amount:
            await ctx.send("You do not have enough Spring Coins.")
            return

        data[giver_id]["coins"] -= amount
        data[receiver_id]["coins"] += amount
        save_economy(data)

        await ctx.send(f"{ctx.author.mention} gave {member.mention} **{amount:,} Spring Coins**.")

    @commands.command(help="Show the richest players in the server.")
    async def leaderboard(self, ctx):
        data = load_economy()
        members = []

        for user_id, info in data.items():
            member = ctx.guild.get_member(int(user_id))
            if member:
                total = info.get("coins", 0) + info.get("bank", 0)
                members.append((member.display_name, total))

        members.sort(key=lambda x: x[1], reverse=True)
        top = members[:10]

        if not top:
            await ctx.send("No leaderboard data yet.")
            return

        lines = []
        for i, (name, total) in enumerate(top, start=1):
            lines.append(f"**{i}.** {name} — {total:,} Spring Coins")

        embed = discord.Embed(title="SpringBot Leaderboard", description="\n".join(lines))
        await ctx.send(embed=embed)

    @commands.command(help="Admin only: add Spring Coins to a user.")
    @commands.has_permissions(administrator=True)
    async def addcoins(self, ctx, member: discord.Member, amount: int):
        if amount <= 0:
            await ctx.send("Amount must be greater than 0.")
            return

        data = load_economy()
        user_id = str(member.id)
        ensure_user(data, user_id)

        data[user_id]["coins"] += amount
        save_economy(data)

        await ctx.send(f"Added **{amount:,} Spring Coins** to {member.mention}.")

    @commands.command(help="Admin only: remove Spring Coins from a user.")
    @commands.has_permissions(administrator=True)
    async def removecoins(self, ctx, member: discord.Member, amount: int):
        if amount <= 0:
            await ctx.send("Amount must be greater than 0.")
            return

        data = load_economy()
        user_id = str(member.id)
        ensure_user(data, user_id)

        data[user_id]["coins"] = max(0, data[user_id]["coins"] - amount)
        save_economy(data)

        await ctx.send(f"Removed **{amount:,} Spring Coins** from {member.mention}.")

    @addcoins.error
    @removecoins.error
    async def economy_admin_error(self, ctx, error):
        if isinstance(error, commands.MissingPermissions):
            await ctx.send("You need administrator permissions for that command.")


async def setup(bot):
    await bot.add_cog(Economy(bot))