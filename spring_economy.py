import random
import sqlite3
from datetime import datetime, timezone, timedelta
from typing import Optional, List, Dict, Any

DB_PATH = "springbot_v2.db"
COIN_NAME = "Spring Coins"
COIN_EMOJI = "🌸"


def now_iso():
    return datetime.now(timezone.utc).isoformat()


def db_connect(db_path: str = DB_PATH):
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    return conn


def setup_economy(db_path: str = DB_PATH):
    with db_connect(db_path) as conn:
        conn.execute("""
        CREATE TABLE IF NOT EXISTS spring_wallets (
            guild_id TEXT NOT NULL,
            user_id TEXT NOT NULL,
            balance INTEGER NOT NULL DEFAULT 0,
            lifetime_earned INTEGER NOT NULL DEFAULT 0,
            last_daily TEXT,
            last_work TEXT,
            updated_at TEXT NOT NULL,
            PRIMARY KEY (guild_id, user_id)
        )
        """)
        conn.execute("""
        CREATE TABLE IF NOT EXISTS spring_transactions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            guild_id TEXT NOT NULL,
            user_id TEXT NOT NULL,
            amount INTEGER NOT NULL,
            reason TEXT NOT NULL,
            created_at TEXT NOT NULL
        )
        """)
        conn.execute("""
        CREATE TABLE IF NOT EXISTS spring_prizes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            guild_id TEXT NOT NULL,
            name TEXT NOT NULL,
            description TEXT NOT NULL,
            price INTEGER NOT NULL,
            stock INTEGER NOT NULL DEFAULT -1,
            role_reward_id TEXT,
            created_at TEXT NOT NULL
        )
        """)
        conn.execute("""
        CREATE TABLE IF NOT EXISTS spring_inventory (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            guild_id TEXT NOT NULL,
            user_id TEXT NOT NULL,
            prize_id INTEGER NOT NULL,
            prize_name TEXT NOT NULL,
            redeemed TEXT NOT NULL DEFAULT 'false',
            created_at TEXT NOT NULL
        )
        """)
        conn.commit()


def ensure_wallet(guild_id: int, user_id: int, db_path: str = DB_PATH):
    with db_connect(db_path) as conn:
        conn.execute(
            "INSERT OR IGNORE INTO spring_wallets (guild_id, user_id, balance, lifetime_earned, updated_at) VALUES (?, ?, 0, 0, ?)",
            (str(guild_id), str(user_id), now_iso()),
        )
        conn.commit()


def get_wallet(guild_id: int, user_id: int, db_path: str = DB_PATH) -> Dict[str, Any]:
    setup_economy(db_path)
    ensure_wallet(guild_id, user_id, db_path)
    with db_connect(db_path) as conn:
        row = conn.execute(
            "SELECT * FROM spring_wallets WHERE guild_id=? AND user_id=?",
            (str(guild_id), str(user_id)),
        ).fetchone()
    return dict(row)


def add_coins(guild_id: int, user_id: int, amount: int, reason: str, db_path: str = DB_PATH) -> int:
    setup_economy(db_path)
    ensure_wallet(guild_id, user_id, db_path)
    amount = int(amount)
    with db_connect(db_path) as conn:
        conn.execute(
            "UPDATE spring_wallets SET balance=balance+?, lifetime_earned=lifetime_earned+?, updated_at=? WHERE guild_id=? AND user_id=?",
            (amount, max(amount, 0), now_iso(), str(guild_id), str(user_id)),
        )
        conn.execute(
            "INSERT INTO spring_transactions (guild_id, user_id, amount, reason, created_at) VALUES (?, ?, ?, ?, ?)",
            (str(guild_id), str(user_id), amount, reason, now_iso()),
        )
        conn.commit()
    return get_wallet(guild_id, user_id, db_path)["balance"]


def remove_coins(guild_id: int, user_id: int, amount: int, reason: str, db_path: str = DB_PATH) -> bool:
    setup_economy(db_path)
    ensure_wallet(guild_id, user_id, db_path)
    wallet = get_wallet(guild_id, user_id, db_path)
    amount = int(amount)
    if wallet["balance"] < amount:
        return False
    with db_connect(db_path) as conn:
        conn.execute(
            "UPDATE spring_wallets SET balance=balance-?, updated_at=? WHERE guild_id=? AND user_id=?",
            (amount, now_iso(), str(guild_id), str(user_id)),
        )
        conn.execute(
            "INSERT INTO spring_transactions (guild_id, user_id, amount, reason, created_at) VALUES (?, ?, ?, ?, ?)",
            (str(guild_id), str(user_id), -amount, reason, now_iso()),
        )
        conn.commit()
    return True


def can_claim_daily(guild_id: int, user_id: int, db_path: str = DB_PATH) -> tuple[bool, Optional[timedelta]]:
    wallet = get_wallet(guild_id, user_id, db_path)
    last_daily = wallet.get("last_daily")
    if not last_daily:
        return True, None
    last = datetime.fromisoformat(last_daily)
    ready_at = last + timedelta(hours=24)
    now = datetime.now(timezone.utc)
    if now >= ready_at:
        return True, None
    return False, ready_at - now


def claim_daily(guild_id: int, user_id: int, db_path: str = DB_PATH) -> tuple[bool, int, Optional[timedelta]]:
    ok, remaining = can_claim_daily(guild_id, user_id, db_path)
    if not ok:
        return False, 0, remaining
    reward = random.randint(150, 350)
    add_coins(guild_id, user_id, reward, "Daily reward", db_path)
    with db_connect(db_path) as conn:
        conn.execute(
            "UPDATE spring_wallets SET last_daily=? WHERE guild_id=? AND user_id=?",
            (now_iso(), str(guild_id), str(user_id)),
        )
        conn.commit()
    return True, reward, None


def can_work(guild_id: int, user_id: int, db_path: str = DB_PATH) -> tuple[bool, Optional[timedelta]]:
    wallet = get_wallet(guild_id, user_id, db_path)
    last_work = wallet.get("last_work")
    if not last_work:
        return True, None
    last = datetime.fromisoformat(last_work)
    ready_at = last + timedelta(minutes=30)
    now = datetime.now(timezone.utc)
    if now >= ready_at:
        return True, None
    return False, ready_at - now


def work_reward(guild_id: int, user_id: int, db_path: str = DB_PATH) -> tuple[bool, int, str, Optional[timedelta]]:
    ok, remaining = can_work(guild_id, user_id, db_path)
    if not ok:
        return False, 0, "", remaining
    jobs = [
        ("fixed a broken router", 40, 120),
        ("closed support tickets", 60, 150),
        ("helped a new member", 50, 130),
        ("cleaned up the server", 35, 110),
        ("trained SpringBot's AI", 75, 180),
        ("caught a phishing link", 100, 220),
    ]
    job, low, high = random.choice(jobs)
    reward = random.randint(low, high)
    add_coins(guild_id, user_id, reward, f"Work reward: {job}", db_path)
    with db_connect(db_path) as conn:
        conn.execute(
            "UPDATE spring_wallets SET last_work=? WHERE guild_id=? AND user_id=?",
            (now_iso(), str(guild_id), str(user_id)),
        )
        conn.commit()
    return True, reward, job, None


def gamble(guild_id: int, user_id: int, amount: int, game: str, db_path: str = DB_PATH) -> Dict[str, Any]:
    amount = int(amount)
    if amount <= 0:
        return {"ok": False, "message": "Bet must be more than 0."}
    wallet = get_wallet(guild_id, user_id, db_path)
    if wallet["balance"] < amount:
        return {"ok": False, "message": "You do not have enough Spring Coins."}

    if game == "coinflip":
        win = random.choice([True, False])
        multiplier = 2
    elif game == "slots":
        symbols = ["🌸", "💎", "🍀", "⭐", "🔥"]
        roll = [random.choice(symbols) for _ in range(3)]
        if roll[0] == roll[1] == roll[2]:
            win = True
            multiplier = 5
        elif len(set(roll)) == 2:
            win = True
            multiplier = 2
        else:
            win = False
            multiplier = 0
        result_text = " ".join(roll)
    elif game == "risk":
        chance = random.randint(1, 100)
        win = chance <= 35
        multiplier = 3
    else:
        return {"ok": False, "message": "Unknown game."}

    if game != "slots":
        result_text = "WIN" if win else "LOSE"

    if win:
        profit = amount * (multiplier - 1)
        add_coins(guild_id, user_id, profit, f"Won {game}", db_path)
        return {"ok": True, "win": True, "profit": profit, "result": result_text, "balance": get_wallet(guild_id, user_id, db_path)["balance"]}
    else:
        remove_coins(guild_id, user_id, amount, f"Lost {game}", db_path)
        return {"ok": True, "win": False, "profit": -amount, "result": result_text, "balance": get_wallet(guild_id, user_id, db_path)["balance"]}


def add_prize(guild_id: int, name: str, description: str, price: int, stock: int = -1, role_reward_id: Optional[str] = None, db_path: str = DB_PATH) -> int:
    setup_economy(db_path)
    with db_connect(db_path) as conn:
        cur = conn.execute(
            "INSERT INTO spring_prizes (guild_id, name, description, price, stock, role_reward_id, created_at) VALUES (?, ?, ?, ?, ?, ?, ?)",
            (str(guild_id), name[:120], description[:500], int(price), int(stock), role_reward_id, now_iso()),
        )
        conn.commit()
        return cur.lastrowid


def list_prizes(guild_id: int, db_path: str = DB_PATH) -> List[Dict[str, Any]]:
    setup_economy(db_path)
    with db_connect(db_path) as conn:
        rows = conn.execute(
            "SELECT * FROM spring_prizes WHERE guild_id=? ORDER BY price ASC",
            (str(guild_id),),
        ).fetchall()
    return [dict(row) for row in rows]


def buy_prize(guild_id: int, user_id: int, prize_id: int, db_path: str = DB_PATH) -> Dict[str, Any]:
    setup_economy(db_path)
    with db_connect(db_path) as conn:
        prize = conn.execute(
            "SELECT * FROM spring_prizes WHERE guild_id=? AND id=?",
            (str(guild_id), int(prize_id)),
        ).fetchone()

    if not prize:
        return {"ok": False, "message": "Prize not found."}
    prize = dict(prize)
    if prize["stock"] == 0:
        return {"ok": False, "message": "That prize is out of stock."}

    if not remove_coins(guild_id, user_id, prize["price"], f"Bought prize: {prize['name']}", db_path):
        return {"ok": False, "message": "You do not have enough Spring Coins."}

    with db_connect(db_path) as conn:
        conn.execute(
            "INSERT INTO spring_inventory (guild_id, user_id, prize_id, prize_name, redeemed, created_at) VALUES (?, ?, ?, ?, 'false', ?)",
            (str(guild_id), str(user_id), prize["id"], prize["name"], now_iso()),
        )
        if prize["stock"] > 0:
            conn.execute("UPDATE spring_prizes SET stock=stock-1 WHERE id=?", (prize["id"],))
        conn.commit()

    return {"ok": True, "prize": prize, "balance": get_wallet(guild_id, user_id, db_path)["balance"]}


def get_inventory(guild_id: int, user_id: int, db_path: str = DB_PATH) -> List[Dict[str, Any]]:
    setup_economy(db_path)
    with db_connect(db_path) as conn:
        rows = conn.execute(
            "SELECT * FROM spring_inventory WHERE guild_id=? AND user_id=? ORDER BY id DESC LIMIT 25",
            (str(guild_id), str(user_id)),
        ).fetchall()
    return [dict(row) for row in rows]


def leaderboard(guild_id: int, db_path: str = DB_PATH) -> List[Dict[str, Any]]:
    setup_economy(db_path)
    with db_connect(db_path) as conn:
        rows = conn.execute(
            "SELECT user_id, balance, lifetime_earned FROM spring_wallets WHERE guild_id=? ORDER BY balance DESC LIMIT 10",
            (str(guild_id),),
        ).fetchall()
    return [dict(row) for row in rows]
