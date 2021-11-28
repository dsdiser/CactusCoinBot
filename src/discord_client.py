import discord
import config
import commands


class Client(discord.Client):
    async def on_ready(self):
        print(f'Logged in as {self.user} (ID: {self.user.id})')
        print('------')

    async def on_message(self, message: discord.Message):
        # we do not want the bot to reply to itself or message in other channels
        if message.author.id == self.user.id or message.channel.name != config.getAttribute('channelName'):
            return

        guild = message.channel.guild
        if message.content.startswith('!help'):
            await message.channel.send('Commands:')

        elif message.content.startswith('!hello'):
            await message.reply('Hello!')

        elif 'deez' in message.content:
            await message.reply('Deez nuts')

        elif message.content.startswith('!verifycoin'):
            if message.mentions:
                for member in message.mentions:
                    await commands.verify_coin(guild, member)
                await message.reply(f'Verified coin for: ' + ', '.join([mention.name for mention in message.mentions]))
            else:
                await message.reply('No mentions. Follow the format: !verifycoin @user1 @user2 ...')

        elif message.content.startswith('!adminadjust'):
            if message.mentions:
                member = message.mentions[0]
                messageContent = message.content.split(' ')
                amount = int(messageContent[2])
                await commands.add_coin(guild, member, amount)
            else:
                await message.reply('No mentions. Follow the format: !adminadjust @user ####')

        elif message.content.startswith('!give'):
            messageContent = message.content.split(' ')
            if message.mentions and len(messageContent) == 3 and messageContent[2].isnumeric():
                recieving_member = message.mentions[0]
                amount = int(messageContent[2])
                if amount > 0:
                    await commands.add_coin(guild, recieving_member, amount)
                    await commands.add_coin(guild, message.author, -amount )
                elif amount < 0:
                    await message.reply('Nice try.')
            else:
                await message.reply('Error parsing. Follow the format: !give @user ####')


client = Client()
client.run(config.getAttribute('token'))
