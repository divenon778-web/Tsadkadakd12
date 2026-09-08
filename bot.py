import discord
from discord.ext import commands
import os
import asyncio
from dotenv import load_dotenv
from database.db_manager import init_db

load_dotenv()

TOKEN = os.getenv("DISCORD_TOKEN")
CHANNEL_ID = int(os.getenv("CHANNEL_ID", 0))

intents = discord.Intents.default()
intents.message_content = True

bot = commands.Bot(command_prefix="!", intents=intents)


@bot.event
async def on_ready():
    await init_db()
    await bot.load_extension("cogs.search")
    print(f"Trackin is online as {bot.user}")


if __name__ == "__main__":
    if not TOKEN:
        print("ERROR: DISCORD_TOKEN not set in .env")
        exit(1)
    bot.run(TOKEN)
