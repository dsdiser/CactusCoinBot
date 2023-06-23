import config
import sqlite3
import discord
from discord.ext import commands

intents = discord.Intents.default()
intents.members = True
intents.message_content = True
bot = commands.Bot('!', intents=intents)
channel_id = 0

@bot.event
async def on_ready():
    # Retrieve the channel object
    channel = bot.get_channel(channel_id)

    # Fetch the past messages in the channel
    questions = []
    async for message in channel.history(limit=None):
        # Check if the message contains a question
        if '>' in message.content and '?' in message.content:
            # Split the message content by lines
            lines = message.content.split('\n')

            # Extract the questions from the lines
            index = lines[0].find('>')
            if index != -1:
                question = lines[0][index + 1:].strip()
                questions.append((hash(question),))


    connection = sqlite3.connect(config.get_attribute('dbFile'))
    connection.execute(
        'CREATE TABLE IF NOT EXISTS TRIVIA_HASHES (hash integer, unique (hash))'
    )
    cur = connection.cursor()
    cur.executemany("INSERT OR IGNORE INTO TRIVIA_HASHES(hash) VALUES (?)", questions)
    connection.commit()

token = config.get_attribute('token', None)
bot.run(token)
