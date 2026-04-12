import os
import json
import discord
from discord.ext import commands

ECONOMY_FILE = "economy.json"
INVENTORY_FILE = "inventory.json"

SHOP_ITEMS = {
    # Weapons
    "knife": {"price": 250, "category": "Weapon", "rarity": "Common", "description": "A basic close-range blade."},
    "bat": {"price": 300, "category": "Weapon", "rarity": "Common", "description": "Simple, heavy, and effective."},
    "machete": {"price": 650, "category": "Weapon", "rarity": "Uncommon", "description": "Cuts through more than excuses."},
    "katana": {"price": 1200, "category": "Weapon", "rarity": "Rare", "description": "Fast, sharp, and stylish."},
    "sniper": {"price": 2200, "category": "Weapon", "rarity": "Rare", "description": "Precision from a distance."},
    "plasma_rifle": {"price": 4500, "category": "Weapon", "rarity": "Epic", "description": "Futuristic firepower."},
    "shadow_blade": {"price": 6000, "category": "Weapon", "rarity": "Epic", "description": "A silent legendary edge."},
    "dragon_cannon": {"price": 9500, "category": "Weapon", "rarity": "Legendary", "description": "Overkill in item form."},

    # Phones
    "burner_phone": {"price": 350, "category": "Phone", "rarity": "Common", "description": "Cheap and disposable."},
    "smartphone": {"price": 800, "category": "Phone", "rarity": "Common", "description": "A decent everyday phone."},
    "gaming_phone": {"price": 1800, "category": "Phone", "rarity": "Rare", "description": "Built for speed and flexing."},
    "cyber_phone": {"price": 3200, "category": "Phone", "rarity": "Epic", "description": "A sleek future-tech phone."},
    "gold_phone": {"price": 7000, "category": "Phone", "rarity": "Legendary", "description": "Pure status."},

    # Armor
    "hoodie_armor": {"price": 500, "category": "Armor", "rarity": "Common", "description": "Low-tier protection."},
    "riot_shield": {"price": 1400, "category": "Armor", "rarity": "Rare", "description": "Built to take a hit."},
    "tactical_vest": {"price": 2200, "category": "Armor", "rarity": "Rare", "description": "A real combat upgrade."},
    "nano_suit": {"price": 6500, "category": "Armor", "rarity": "Epic", "description": "Next-level body armor."},
    "titan_armor": {"price": 11000, "category": "Armor", "rarity": "Legendary", "description": "Heavy, rare, and elite."},

    # Vehicles
    "skateboard": {"price": 300, "category": "Vehicle", "rarity": "Common", "description": "Cheap movement."},
    "bike": {"price": 700, "category": "Vehicle", "rarity": "Common", "description": "Reliable transportation."},
    "motorcycle": {"price": 2200, "category": "Vehicle", "rarity": "Rare", "description": "Speed on two wheels."},
    "muscle_car": {"price": 5500, "category": "Vehicle", "rarity": "Epic", "description": "Loud and expensive."},
    "supercar": {"price": 15000, "category": "Vehicle", "rarity": "Legendary", "description": "Maximum flex."},
    "hover_car": {"price": 25000, "category": "Vehicle", "rarity": "Mythic", "description": "Future luxury."},

    # Tech
    "laptop": {"price": 1600, "category": "Tech", "rarity": "Common", "description": "A standard portable machine."},
    "gaming_pc": {"price": 5000, "category": "Tech", "rarity": "Epic", "description": "Built for power."},
    "hacking_rig": {"price": 8500, "category": "Tech", "rarity": "Legendary", "description": "A dark terminal monster."},
    "quantum_chip": {"price": 20000, "category": "Tech", "rarity": "Mythic", "description": "Ridiculous computing power."},
    "drone": {"price": 3000, "category": "Tech", "rarity": "Rare", "description": "Useful and flashy."},

    # Jewelry / Luxury
    "silver_chain": {"price": 900, "category": "Luxury", "rarity": "Common", "description": "A light flex."},
    "gold_chain": {"price": 2200, "category": "Luxury", "rarity": "Rare", "description": "A real flex."},
    "diamond_watch": {"price": 7000, "category": "Luxury", "rarity": "Epic", "description": "You bought time itself."},
    "crown": {"price": 12000, "category": "Luxury", "rarity": "Legendary", "description": "Royal status."},
    "private_jet_pass": {"price": 30000, "category": "Luxury", "rarity": "Mythic", "description": "Peak flex energy."},

    # Property
    "apartment_key": {"price": 2500, "category": "Property", "rarity": "Common", "description": "Your first place."},
    "penthouse_key": {"price": 15000, "category": "Property", "rarity": "Legendary", "description": "Sky-high luxury."},
    "mansion_key": {"price": 35000, "category": "Property", "rarity": "Mythic", "description": "Unreal estate."},
    "vault_key": {"price": 9000, "category": "Property", "rarity": "Epic", "description": "Something valuable is behind it."},

    # Food / Consumables
    "chips": {"price": 60, "category": "Consumable", "rarity": "Common", "description": "A quick snack."},
    "pizza": {"price": 120, "category": "Consumable", "rarity": "Common", "description": "Never a bad choice."},
    "energy_drink": {"price": 180, "category": "Consumable", "rarity": "Common", "description": "Pure temporary power."},
    "mystery_box": {"price": 750, "category": "Consumable", "rarity": "Rare", "description": "Could be anything."},
    "loot_crate": {"price": 1600, "category": "Consumable", "rarity": "Epic", "description": "Packed with possibility."},

    # Power / Boosts
    "luck_charm": {"price": 1400, "category": "Boost", "rarity": "Rare", "description": "Maybe your luck changes."},
    "double_coin_boost": {"price": 4000, "category": "Boost", "rarity": "Epic", "description": "A premium economy booster."},
    "xp_token": {"price": 1800, "category": "Boost", "rarity": "Rare", "description": "Level grind fuel."},
    "battle_pass": {"price": 10000, "category": "Boost", "rarity": "Legendary", "description": "Only for real grinders."},

    # Collectibles
    "ancient_relic": {"price": 6000, "category": "Collectible", "rarity": "Epic", "description": "A mysterious artifact."},
    "neon_cube": {"price": 2200, "category": "Collectible", "rarity": "Rare", "description": "Looks expensive because it is."},
    "galaxy_orb": {"price": 11000, "category": "Collectible", "rarity": "Legendary", "description": "Cosmic flex item."},
    "void_crystal": {"price": 26000, "category": "Collectible", "rarity": "Mythic", "description": "Extremely rare energy core."},

    # Pets
    "cat": {"price": 900, "category": "Pet", "rarity": "Common", "description": "A chill companion."},
    "wolf": {"price": 4200, "category": "Pet", "rarity": "Epic", "description": "Loyal and dangerous."},
    "dragon_pet": {"price": 18000, "category": "Pet", "rarity": "Legendary", "description": "Yes, an actual dragon."},
    "robot_dog": {"price": 8000, "category": "Pet", "rarity": "Epic", "description": "Metal loyalty."},
}


def load_json(path):
    if not os.path.exists(path):
        with open(path, "w", encoding="utf-8") as f:
            json.dump({}, f, indent=4)
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def save_json(path, data):
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=4)


def ensure_economy_user(data, user_id: str):
    if user_id not in data:
        data[user_id] = {
            "coins": 0,
            "bank": 0,
            "last_daily": 0,
            "last_work": 0,
            "last_crime": 0,
            "last_beg": 0,
        }


def ensure_inventory_user(data, user_id: str):
    if user_id not in data:
        data[user_id] = {}


class Shop(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.command(help="View the Spring Shop.")
    async def shop(self, ctx, page: int = 1):
        items = list(SHOP_ITEMS.items())
        per_page = 10
        total_pages = (len(items) + per_page - 1) // per_page

        if page < 1 or page > total_pages:
            await ctx.send(f"Use a page number between **1** and **{total_pages}**.")
            return

        start = (page - 1) * per_page
        end = start + per_page
        selected = items[start:end]

        lines = []
        for name, info in selected:
            lines.append(
                f"**{name}** — {info['price']:,} coins\n"
                f"{info['category']} | {info['rarity']}\n"
                f"{info['description']}"
            )

        embed = discord.Embed(
            title=f"Spring Shop — Page {page}/{total_pages}",
            description="\n\n".join(lines)
        )
        embed.set_footer(text="Use !buy <item_name> to purchase")
        await ctx.send(embed=embed)

    @commands.command(help="View shop items by category.")
    async def shopcategory(self, ctx, *, category: str):
        matches = []
        for name, info in SHOP_ITEMS.items():
            if info["category"].lower() == category.lower():
                matches.append((name, info))

        if not matches:
            categories = sorted(set(item["category"] for item in SHOP_ITEMS.values()))
            await ctx.send(f"No category found. Available categories: {', '.join(categories)}")
            return

        lines = []
        for name, info in matches[:20]:
            lines.append(
                f"**{name}** — {info['price']:,} coins | {info['rarity']}\n{info['description']}"
            )

        embed = discord.Embed(
            title=f"Shop Category: {category.title()}",
            description="\n\n".join(lines)
        )
        await ctx.send(embed=embed)

    @commands.command(help="View details about a shop item.")
    async def item(self, ctx, *, item_name: str):
        key = item_name.lower().replace(" ", "_")
        if key not in SHOP_ITEMS:
            await ctx.send("That item does not exist in the Spring Shop.")
            return

        info = SHOP_ITEMS[key]
        embed = discord.Embed(title=key)
        embed.add_field(name="Price", value=f"{info['price']:,} Spring Coins", inline=True)
        embed.add_field(name="Category", value=info["category"], inline=True)
        embed.add_field(name="Rarity", value=info["rarity"], inline=True)
        embed.add_field(name="Description", value=info["description"], inline=False)
        await ctx.send(embed=embed)

    @commands.command(help="Buy an item from the Spring Shop.")
    async def buy(self, ctx, *, item_name: str):
        key = item_name.lower().replace(" ", "_")
        if key not in SHOP_ITEMS:
            await ctx.send("That item does not exist in the Spring Shop.")
            return

        economy = load_json(ECONOMY_FILE)
        inventory = load_json(INVENTORY_FILE)
        user_id = str(ctx.author.id)

        ensure_economy_user(economy, user_id)
        ensure_inventory_user(inventory, user_id)

        price = SHOP_ITEMS[key]["price"]

        if economy[user_id]["coins"] < price:
            await ctx.send(f"You need **{price:,} Spring Coins** to buy `{key}`.")
            return

        economy[user_id]["coins"] -= price
        inventory[user_id][key] = inventory[user_id].get(key, 0) + 1

        save_json(ECONOMY_FILE, economy)
        save_json(INVENTORY_FILE, inventory)

        await ctx.send(f"{ctx.author.mention} bought **{key}** for **{price:,} Spring Coins**.")

    @commands.command(help="Check your inventory.")
    async def inventory(self, ctx, member: discord.Member = None):
        target = member or ctx.author
        inventory = load_json(INVENTORY_FILE)
        user_id = str(target.id)
        ensure_inventory_user(inventory, user_id)
        save_json(INVENTORY_FILE, inventory)

        items = inventory[user_id]
        if not items:
            await ctx.send(f"{target.display_name} has nothing in their inventory.")
            return

        lines = [f"**{name}** x{amount}" for name, amount in items.items()]
        embed = discord.Embed(title=f"{target.display_name}'s Inventory", description="\n".join(lines[:40]))
        await ctx.send(embed=embed)

    @commands.command(help="Use an item from your inventory.")
    async def use(self, ctx, *, item_name: str):
        key = item_name.lower().replace(" ", "_")
        inventory = load_json(INVENTORY_FILE)
        user_id = str(ctx.author.id)

        ensure_inventory_user(inventory, user_id)

        if key not in inventory[user_id] or inventory[user_id][key] <= 0:
            await ctx.send("You do not own that item.")
            return

        inventory[user_id][key] -= 1
        if inventory[user_id][key] <= 0:
            del inventory[user_id][key]

        save_json(INVENTORY_FILE, inventory)

        responses = {
            "chips": "You ate the chips. Minimal recovery achieved.",
            "pizza": "You crushed the pizza and restored your spirit.",
            "energy_drink": "You drank the energy drink and now your heartbeat sounds expensive.",
            "mystery_box": "You opened the mystery box. The result is classified.",
            "loot_crate": "You opened the loot crate. Something shiny was inside.",
            "luck_charm": "You activated the luck charm. Maybe the odds shifted.",
            "double_coin_boost": "You used a double coin boost. Flex acknowledged.",
            "xp_token": "You used an XP token. Progress energy increased.",
            "battle_pass": "You activated the battle pass. Grind mode enabled.",
        }

        message = responses.get(key, f"You used **{key}**.")
        await ctx.send(f"{ctx.author.mention} {message}")

    @commands.command(help="Sell an item back for half price.")
    async def sell(self, ctx, *, item_name: str):
        key = item_name.lower().replace(" ", "_")
        if key not in SHOP_ITEMS:
            await ctx.send("That item is not in the Spring Shop.")
            return

        inventory = load_json(INVENTORY_FILE)
        economy = load_json(ECONOMY_FILE)
        user_id = str(ctx.author.id)

        ensure_inventory_user(inventory, user_id)
        ensure_economy_user(economy, user_id)

        if key not in inventory[user_id] or inventory[user_id][key] <= 0:
            await ctx.send("You do not own that item.")
            return

        sell_price = SHOP_ITEMS[key]["price"] // 2
        inventory[user_id][key] -= 1
        if inventory[user_id][key] <= 0:
            del inventory[user_id][key]

        economy[user_id]["coins"] += sell_price

        save_json(INVENTORY_FILE, inventory)
        save_json(ECONOMY_FILE, economy)

        await ctx.send(f"{ctx.author.mention} sold **{key}** for **{sell_price:,} Spring Coins**.")

    @commands.command(help="Admin only: give an item to a user.")
    @commands.has_permissions(administrator=True)
    async def giveitem(self, ctx, member: discord.Member, item_name: str, amount: int = 1):
        key = item_name.lower().replace(" ", "_")

        if key not in SHOP_ITEMS:
            await ctx.send("That item is not in the Spring Shop.")
            return

        if amount <= 0:
            await ctx.send("Amount must be greater than 0.")
            return

        inventory = load_json(INVENTORY_FILE)
        user_id = str(member.id)
        ensure_inventory_user(inventory, user_id)

        inventory[user_id][key] = inventory[user_id].get(key, 0) + amount
        save_json(INVENTORY_FILE, inventory)

        await ctx.send(f"Gave {member.mention} **{amount}x {key}**.")

    @commands.command(help="Show all shop commands.")
    async def shophelp(self, ctx):
        await ctx.send(
            "**Spring Shop Commands**\n"
            "`!shop [page]` - view shop pages\n"
            "`!shopcategory <category>` - filter by category\n"
            "`!item <item_name>` - item details\n"
            "`!buy <item_name>` - buy an item\n"
            "`!inventory [@user]` - view inventory\n"
            "`!use <item_name>` - use an item\n"
            "`!sell <item_name>` - sell item for half price\n"
            "`!giveitem @user <item_name> [amount]` - admin only\n"
            "`!shophelp` - show this list"
        )

    @giveitem.error
    async def giveitem_error(self, ctx, error):
        if isinstance(error, commands.MissingPermissions):
            await ctx.send("You need administrator permissions for that command.")


async def setup(bot):
    await bot.add_cog(Shop(bot))