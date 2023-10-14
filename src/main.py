import asyncio
import atexit
import logging
import signal
import sys
import openai
import os

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
    img_generator = config.get_attribute('img_generator', None)
    if img_generator == 'openai':
        openai_api_key = config.get_attribute('openai_key', None)
        if openai_api_key:
            openai.api_key = openai_api_key
        else:
            logging.error('No openai_key provided in config.yml, no openai functionality available.')
    elif img_generator == 'replicate':
        replicate_api_key = config.get_attribute('replicate_key', None)
        if replicate_api_key:
            os.environ['REPLICATE_API_TOKEN'] = replicate_api_key
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
