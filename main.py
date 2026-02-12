import os
import asyncio
from webserver import keep_alive
from modules.config import bot
from modules.database import init_db
from modules import commands
from modules import events

async def main():
    keep_alive()
    init_db()
    asyncio.create_task(events.weekly_reset())
    await bot.load_extension("check")
    token = os.getenv("TOKEN")
    await bot.start(token)

if __name__ == "__main__":
    asyncio.run(main())

