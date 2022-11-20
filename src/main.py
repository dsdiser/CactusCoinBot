import asyncio
import atexit
import logging
import signal
import sys

import discord
from discord.ext import commands

import config
from discord_cog import setup

logging.basicConfig(stream=sys.stderr, level=config.getAttribute('logLevel', 'INFO'))
# This is needed to get full list of members
intents = discord.Intents.default()
intents.members = True
intents.message_content = True
bot = commands.Bot(command_prefix='/', intents=intents)


async def main():
    token = config.getAttribute('token', None)
    if token:
        await setup(bot)
        bot.run(token)
    else:
        logging.error('No token provided in config.yml, bot not started.')


def handle_exit():
    logging.info('Closing client down...')
    bot.close()


atexit.register(handle_exit)
signal.signal(signal.SIGTERM, handle_exit)
signal.signal(signal.SIGINT, handle_exit)
asyncio.run(main())
