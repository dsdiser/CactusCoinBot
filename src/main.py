import asyncio
import atexit
import logging
import signal
import sys

import discord
from discord.ext import commands

import config
from discord_cog import setup

logging.basicConfig(stream=sys.stderr, level=config.get_attribute('logLevel', 'INFO'))
# This is needed to get full list of members
intents = discord.Intents.default()
intents.members = True
intents.message_content = True
bot = commands.Bot(command_prefix='?', intents=intents, help_command=None)


async def main():
    token = config.get_attribute('token', None)
    if token:
        await setup(bot)
        await bot.start(token)
    else:
        logging.error('No token provided in config.yml, bot not started.')


@atexit.register
def handle_exit():
    logging.info('Closing client down...')
    asyncio.run(bot.close())


def invoke_exit(signo, frame):
    sys.exit(0)


signal.signal(signal.SIGTERM, invoke_exit)
signal.signal(signal.SIGINT, invoke_exit)
asyncio.run(main())
