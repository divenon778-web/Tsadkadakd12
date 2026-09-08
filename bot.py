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
    reassemble_db_from_parts()
    await init_db()
    await bot.load_extension("cogs.search")
    print(f"Trackin is online as {bot.user}")


if __name__ == "__main__":
    if not TOKEN:
        print("ERROR: DISCORD_TOKEN not set in .env")
        exit(1)

    async def main():
        delay = 30
        while True:
            try:
                await bot.start(TOKEN)
            except discord.errors.HTTPException as e:
                if "429" in str(e):
                    print(f"Rate limited. Retrying in {delay}s...")
                    await asyncio.sleep(delay)
                    delay = min(delay * 2, 300)
                else:
                    raise
            except Exception as e:
                print(f"Error: {e}. Retrying in {delay}s...")
                await asyncio.sleep(delay)
                delay = min(delay * 2, 300)

    asyncio.run(main())
