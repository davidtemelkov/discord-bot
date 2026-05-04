import discord
from discord.ext import tasks, commands
import json
import datetime
import os
from zoneinfo import ZoneInfo

TOKEN = os.getenv("TOKEN")

intents = discord.Intents.default()
bot = commands.Bot(command_prefix="!", intents=intents)

DATA_FILE = "data.json"

SOFIA_TZ = ZoneInfo("Europe/Sofia")
TARGET_HOUR = 12  # 12:00 PM Sofia time

CHORES = {
    "dishes": 1,
    "trash": 2,
    "floor": 3,
    "bathroom": 7,
    "tidy": 3
}

def load_data():
    try:
        with open(DATA_FILE, "r") as f:
            return json.load(f)
    except:
        return {
            "users": [],          # [him_id, her_id]
            "sick": [],
            "vacation": False,
            "last_person": {},
            "last_sent_date": {}
        }

def save_data(data):
    with open(DATA_FILE, "w") as f:
        json.dump(data, f)

data = load_data()

def get_label(index):
    return "him" if index == 0 else "her"

def get_next_index(chore):
    last = data["last_person"].get(chore)
    if last == 0:
        return 1
    return 0

@bot.event
async def on_ready():
    print(f"Logged in as {bot.user}")
    chore_loop.start()

@tasks.loop(minutes=1)
async def chore_loop():
    if data["vacation"] or len(data["users"]) < 2:
        return

    now = datetime.datetime.now(SOFIA_TZ)

    # Only run at exactly 12:00
    if not (now.hour == TARGET_HOUR and now.minute == 0):
        return

    today_str = now.date().isoformat()

    channel = discord.utils.get(bot.get_all_channels(), name="chores")
    if not channel:
        return

    for chore, interval_days in CHORES.items():

        # prevent double-send same day
        if data["last_sent_date"].get(chore) == today_str:
            continue

        last_time_str = data["last_sent_date"].get(f"{chore}_time")

        if last_time_str:
            last_time = datetime.datetime.fromisoformat(last_time_str)
            if (now - last_time).days < interval_days:
                continue

        # sick mode → only non-sick person
        if data["sick"]:
            available = [u for u in data["users"] if u not in data["sick"]]
            if not available:
                continue
            user_id = available[0]
            label = "him" if user_id == data["users"][0] else "her"
        else:
            idx = get_next_index(chore)
            user_id = data["users"][idx]
            label = get_label(idx)
            data["last_person"][chore] = idx

        await channel.send(f"☀️ 12:00 chore: <@{user_id}> ({label}) → {chore}")

        data["last_sent_date"][chore] = today_str
        data["last_sent_date"][f"{chore}_time"] = now.isoformat()

    save_data(data)

# ---------------- COMMANDS ----------------

@bot.command()
async def setup(ctx, user1: discord.Member, user2: discord.Member):
    data["users"] = [str(user1.id), str(user2.id)]
    save_data(data)
    await ctx.send("Setup complete: user1 = him, user2 = her")

@bot.command()
async def vacation(ctx, mode: str):
    data["vacation"] = (mode == "on")
    save_data(data)
    await ctx.send(f"Vacation mode: {data['vacation']}")

@bot.command()
async def sick(ctx, user: discord.Member):
    if str(user.id) not in data["sick"]:
        data["sick"].append(str(user.id))
    save_data(data)
    await ctx.send(f"{user.name} is now sick")

@bot.command()
async def healthy(ctx, user: discord.Member):
    if str(user.id) in data["sick"]:
        data["sick"].remove(str(user.id))
    save_data(data)
    await ctx.send(f"{user.name} is now healthy")

@bot.command()
async def status(ctx):
    await ctx.send(
        f"Vacation: {data['vacation']}\n"
        f"Sick users: {data['sick']}"
    )

bot.run(TOKEN)