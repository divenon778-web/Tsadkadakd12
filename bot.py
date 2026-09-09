import sys
import os

sys.stdout.reconfigure(line_buffering=True)
sys.stderr.reconfigure(line_buffering=True)

print("=== Trackin Bot Starting ===", flush=True)
print(f"Python version: {sys.version}", flush=True)
print(f"Working directory: {os.getcwd()}", flush=True)
print(f"Files: {os.listdir('.')}", flush=True)

try:
    import discord
    from discord.ext import commands
    import asyncio
    from dotenv import load_dotenv

    load_dotenv()

    TOKEN = os.getenv("DISCORD_TOKEN")
    CHANNEL_ID = int(os.getenv("CHANNEL_ID", 0))

    print(f"DISCORD_TOKEN set: {bool(TOKEN)}", flush=True)
    print(f"CHANNEL_ID: {CHANNEL_ID}", flush=True)

    intents = discord.Intents.default()
    intents.message_content = True

    bot = commands.Bot(command_prefix="!", intents=intents)

    @bot.event
    async def on_ready():
        print(f"Bot connected as {bot.user} (ID: {bot.user.id})", flush=True)
        print(f"Guilds: {len(bot.guilds)}", flush=True)
        try:
            from database.db_manager import init_db, reassemble_db_from_parts
            reassemble_db_from_parts()
            await init_db()
        except Exception as e:
            print(f"DB setup error: {e}", flush=True)
        try:
            await bot.load_extension("cogs.search")
            print("Cog loaded successfully", flush=True)
        except Exception as e:
            print(f"Cog load error: {e}", flush=True)
        print(f"Trackin is online as {bot.user}", flush=True)

    if not TOKEN:
        print("ERROR: DISCORD_TOKEN not set!", flush=True)
        sys.exit(1)

    async def main():
        delay = 10
        while True:
            try:
                print("Attempting to connect to Discord...", flush=True)
                await bot.start(TOKEN)
            except discord.errors.HTTPException as e:
                if "429" in str(e):
                    print(f"Rate limited. Retrying in {delay}s...", flush=True)
                    await asyncio.sleep(delay)
                    delay = min(delay * 2, 300)
                else:
                    print(f"HTTP Error: {e}", flush=True)
                    raise
            except Exception as e:
                print(f"Error: {e}. Retrying in {delay}s...", flush=True)
                await asyncio.sleep(delay)
                delay = min(delay * 2, 300)

    asyncio.run(main())

except Exception as e:
    print(f"FATAL ERROR: {e}", flush=True)
    import traceback
    traceback.print_exc()
    sys.exit(1)
