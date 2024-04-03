import asyncio
import atexit
import logging
import signal
import sys

from .cogs.main_cog import BotCog
from . import config
from .models import database, Amounts, Bets, Transactions


import discord
from discord.ext import commands



async def setup(initiated_bot: commands.Bot):
    await initiated_bot.add_cog(BotCog())
    # await bot.add_cog(TriviaCog(bot))


async def main(initiated_bot: commands.Bot):
    token = config.get_attribute('token', None)
    if token:
        await setup(initiated_bot)
        await initiated_bot.start(token)
        database.connect()
        database.create_tables([Amounts, Bets, Transactions])
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
