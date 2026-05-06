import discord
from discord.ext import tasks, commands
import os
import datetime
import random
import hashlib
from zoneinfo import ZoneInfo

TOKEN = os.getenv("TOKEN")

intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix="!", intents=intents)

SOFIA_TZ = ZoneInfo("Europe/Sofia")
TARGET_HOUR = 12

# ---------------- CHORES CONFIG ----------------
# interval = every N days
CHORES = {
    "dishes": 1,
    "trash": 2,
    "floor": 3,
    "bathroom": 7,
    "tidy": 3
}

data = {
    "users": [],
    "vacation": False
}

# ---------------- SEED SYSTEM ----------------

def get_daily_seed(date_str: str):
    return int(hashlib.sha256(date_str.encode()).hexdigest(), 16)

def assign_chores(seed, users, date_str):
    rng = random.Random(seed)

    shuffled = users[:]
    rng.shuffle(shuffled)

    day_number = datetime.date.fromisoformat(date_str).toordinal()

    assignments = []
    user_index = 0

    for chore, interval in CHORES.items():

        # 🔁 interval logic (IMPORTANT FIX)
        if day_number % interval != 0:
            continue

        user = shuffled[user_index % len(shuffled)]
        label = "him" if user == users[0] else "her"

        assignments.append((chore, user, label))
        user_index += 1

    return assignments

# ---------------- BOT EVENTS ----------------

@bot.event
async def on_ready():
    print(f"Logged in as {bot.user}")
    chore_loop.start()

# ---------------- AUTO LOOP ----------------

@tasks.loop(minutes=1)
async def chore_loop():
    if data["vacation"] or len(data["users"]) < 2:
        return

    now = datetime.datetime.now(SOFIA_TZ)

    if now.hour < TARGET_HOUR:
        return

    channel = discord.utils.get(bot.get_all_channels(), name="chores")
    if not channel:
        return

    date_str = now.date().isoformat()
    seed = get_daily_seed(date_str)

    chores_today = assign_chores(seed, data["users"], date_str)

    if not chores_today:
        return

    await channel.send("☀️ **Daily chore assignment (12:00)**")

    for chore, user_id, label in chores_today:
        await channel.send(f"👉 <@{user_id}> ({label}) → **{chore}**")

# ---------------- COMMANDS ----------------

@bot.command()
async def setup(ctx, user1: discord.Member, user2: discord.Member):
    data["users"] = [str(user1.id), str(user2.id)]
    await ctx.send("✅ Setup complete!")

@bot.command()
async def chores(ctx, date: str = None):
    if len(data["users"]) < 2:
        await ctx.send("⚠️ Run !setup first.")
        return

    if date is None:
        date = datetime.datetime.now(SOFIA_TZ).date().isoformat()

    seed = get_daily_seed(date)
    chores_today = assign_chores(seed, data["users"], date)

    if not chores_today:
        await ctx.send(f"📅 No chores scheduled for {date}.")
        return

    msg = f"📅 **Chores for {date}:**\n\n"

    for chore, user_id, label in chores_today:
        msg += f"👉 <@{user_id}> ({label}) → **{chore}**\n"

    await ctx.send(msg)

@bot.command()
async def fromseed(ctx, seed: int):
    if len(data["users"]) < 2:
        await ctx.send("⚠️ Run !setup first.")
        return

    # fake date only for formatting
    date_str = "seed-mode"

    chores_today = assign_chores(seed, data["users"], "2026-01-01")

    msg = f" **Chores from seed {seed}:**\n\n"

    for chore, user_id, label in chores_today:
        msg += f"👉 <@{user_id}> ({label}) → **{chore}**\n"

    await ctx.send(msg)

@bot.command()
async def vacation(ctx, mode: str):
    data["vacation"] = (mode == "on")
    await ctx.send(f"Vacation mode: {'ON' if data['vacation'] else 'OFF'}")

# ---------------- RUN ----------------

bot.run(TOKEN)