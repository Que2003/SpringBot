import os
import json
import random
from datetime import datetime, timedelta, timezone

import discord
from discord.ext import commands


class Economy(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.file_path = "economy.json"
        self.currency_name = "SpringCoins"
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

    def can_claim_time(self, last_time_str, cooldown_hours: int):
        if not last_time_str:
            return True, None

        try:
            last_time = datetime.fromisoformat(last_time_str)
        except Exception:
            return True, None

        now = datetime.now(timezone.utc)
        next_time = last_time + timedelta(hours=cooldown_hours)

        if now >= next_time:
            return True, None

        remaining = next_time - now
        return False, remaining

    @commands.command(help="Show your SpringCoins balance.")
    async def balance(self, ctx, member: discord.Member = None):
        member = member or ctx.author
        bal = self.get_balance(ctx.guild.id, member.id)
        await ctx.send(f"{member.mention} has **{bal} {self.currency_name}**.")

    @commands.command(help="Claim your daily SpringCoins.")
    async def daily(self, ctx):
        user = self.get_user(ctx.guild.id, ctx.author.id)
        allowed, remaining = self.can_claim_time(user.get("last_daily"), 24)

        if not allowed:
            hours = remaining.seconds // 3600
            minutes = (remaining.seconds % 3600) // 60
            await ctx.send(f"You already claimed daily. Try again in **{hours}h {minutes}m**.")
            return

        reward = random.randint(150, 350)
        user["balance"] += reward
        user["last_daily"] = datetime.now(timezone.utc).isoformat()
        self.save_data()

        await ctx.send(f"You claimed **{reward} {self.currency_name}**.")

    @commands.command(help="Work for SpringCoins.")
    async def work(self, ctx):
        user = self.get_user(ctx.guild.id, ctx.author.id)
        allowed, remaining = self.can_claim_time(user.get("last_work"), 1)

        if not allowed:
            minutes = remaining.seconds // 60
            seconds = remaining.seconds % 60
            await ctx.send(f"You already worked recently. Try again in **{minutes}m {seconds}s**.")
            return

        jobs = [
            "fixed a broken router",
            "patched a suspicious server",
            "helped someone reset their password",
            "installed a network switch",
            "cleaned malware off a computer",
            "helped SpringBot with paperwork",
            "moderated chaos in the server",
            "ran diagnostics on a cursed laptop"
        ]

        reward = random.randint(40, 120)
        user["balance"] += reward
        user["last_work"] = datetime.now(timezone.utc).isoformat()
        self.save_data()

        await ctx.send(
            f"You **{random.choice(jobs)}** and earned **{reward} {self.currency_name}**."
        )

    @commands.command(help="Give SpringCoins to another user. Example: !pay @user 100")
    async def pay(self, ctx, member: discord.Member, amount: int):
        if member.bot:
            await ctx.send("You cannot pay bots.")
            return

        if member.id == ctx.author.id:
            await ctx.send("You cannot pay yourself.")
            return

        if amount <= 0:
            await ctx.send("Enter a valid amount greater than 0.")
            return

        sender_balance = self.get_balance(ctx.guild.id, ctx.author.id)
        if amount > sender_balance:
            await ctx.send("You do not have enough SpringCoins.")
            return

        self.add_balance(ctx.guild.id, ctx.author.id, -amount)
        self.add_balance(ctx.guild.id, member.id, amount)

        await ctx.send(
            f"{ctx.author.mention} sent **{amount} {self.currency_name}** to {member.mention}."
        )

    @commands.command(help="Show the richest users in the server.")
    async def leaderboard(self, ctx):
        guild_key = str(ctx.guild.id)
        guild_data = self.data.get(guild_key, {})

        if not guild_data:
            await ctx.send("No economy data yet.")
            return

        sorted_users = sorted(
            guild_data.items(),
            key=lambda item: int(item[1].get("balance", 0)),
            reverse=True
        )[:10]

        lines = []
        for i, (user_id, info) in enumerate(sorted_users, start=1):
            member = ctx.guild.get_member(int(user_id))
            name = member.display_name if member else f"User {user_id}"
            lines.append(f"{i}. **{name}** — {info.get('balance', 0)} {self.currency_name}")

        await ctx.send("**SpringCoins Leaderboard**\n" + "\n".join(lines))

    @commands.command(help="Show economy commands.")
    async def economyhelp(self, ctx):
        await ctx.send(
            "**Economy Commands**\n"
            "!balance [@user]\n"
            "!daily\n"
            "!work\n"
            "!pay @user <amount>\n"
            "!leaderboard\n"
            "!economyhelp"
        )


async def setup(bot):
    await bot.add_cog(Economy(bot))