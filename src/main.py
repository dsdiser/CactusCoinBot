import asyncio
import atexit
import logging
import signal
import sys

from src.api_handlers.food_handler import generate_food_questions
from src.cogs.main_cog import BotCog
import src.config as config
from src.models import database, TABLES


import discord
from discord.ext import commands



async def setup(initiated_bot: commands.Bot):
    await initiated_bot.add_cog(BotCog(initiated_bot))
    # await bot.add_cog(TriviaCog(bot))


async def main(initiated_bot: commands.Bot):
    token = config.get_attribute('token', None)
    database.connect()
    database.create_tables(TABLES)
    generate_food_questions()
    if token:
        await setup(initiated_bot)
        await initiated_bot.start(token)
    else:
        logging.error('No token provided in config.yml, bot not started.')

def invoke_exit(_signo, _frame):
    sys.exit(0)

if __name__ == "__main__":
    logging.basicConfig(stream=sys.stderr, level=config.get_attribute('logLevel', 'INFO'))
    # This is needed to get full list of members
    intents = discord.Intents.default()
    intents.members = True
    intents.message_content = True
    bot = commands.Bot(command_prefix='?', intents=intents, help_command=None)
    signal.signal(signal.SIGTERM, invoke_exit)
    signal.signal(signal.SIGINT, invoke_exit)
    asyncio.run(main(initiated_bot=bot))

    @atexit.register
    def handle_exit():
        logging.info('Closing client down...')
        asyncio.run(bot.close())
