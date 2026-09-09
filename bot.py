import discord
from discord.ext import commands
import os
import asyncio
from dotenv import load_dotenv
from database.db_manager import init_db, reassemble_db_from_parts

load_dotenv()

TOKEN = os.getenv("DISCORD_TOKEN")
CHANNEL_ID = int(os.getenv("CHANNEL_ID", 0))

intents = discord.Intents.default()
intents.message_content = True

bot = commands.Bot(command_prefix="!", intents=intents)


@bot.event
async def on_ready():
    print(f"Bot connected as {bot.user} (ID: {bot.user.id})")
    print(f"Guilds: {len(bot.guilds)}")
    reassemble_db_from_parts()
    await init_db()
    await bot.load_extension("cogs.search")
    print(f"Trackin is online as {bot.user}")


if __name__ == "__main__":
    print(f"DISCORD_TOKEN set: {bool(TOKEN)}")
    print(f"CHANNEL_ID: {CHANNEL_ID}")

    if not TOKEN:
        print("ERROR: DISCORD_TOKEN not set!")
        exit(1)

    async def main():
        delay = 10
        while True:
            try:
                await bot.start(TOKEN)
            except discord.errors.HTTPException as e:
                if "429" in str(e):
                    print(f"Rate limited. Retrying in {delay}s...")
                    await asyncio.sleep(delay)
                    delay = min(delay * 2, 300)
                else:
                    print(f"HTTP Error: {e}")
                    raise
            except Exception as e:
                print(f"Error: {e}. Retrying in {delay}s...")
                await asyncio.sleep(delay)
                delay = min(delay * 2, 300)

    asyncio.run(main())
