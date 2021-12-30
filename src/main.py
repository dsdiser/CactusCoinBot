import discord_client
import discord
import config
import logging
import sys
import atexit
import signal

logging.basicConfig(stream=sys.stderr, level=config.getAttribute('logLevel', 'INFO'))

# This is needed to get full list of members
intents = discord.Intents.default()
intents.members = True
client = discord_client.Client(intents=intents)

def main():
    token = config.getAttribute('token', None)
    if token:
        client.run(token)
    else:
        logging.error('No token provided in config.yml, bot not started.')


def handle_exit():
    logging.info('Closing client down...')
    # await client.close()


atexit.register(handle_exit)
signal.signal(signal.SIGTERM, handle_exit)
signal.signal(signal.SIGINT, handle_exit)
main()
