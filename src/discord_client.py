import discord
import config
import commands
import views
import logging
import sys
import spellchecker

logging.basicConfig(stream=sys.stderr, level=config.getAttribute('logLevel'))


class Client(discord.Client):
    def get_commands(self):
        return ['!help', '!verifycoin', '!give', '!bet']

    async def on_ready(self):
        print(f'Logged in as {self.user} (ID: {self.user.id})')
        print('------')

    async def on_message(self, message: discord.Message):
        # we do not want the bot to reply to itself or message in other channels
        if message.author.id == self.user.id or message.channel.name != config.getAttribute('channelName'):
            return

        guild = message.channel.guild
        if message.content.startswith('!help'):
            await message.channel.send('Current commands: !hello, !verifycoin, !give !bet')

        elif message.content.startswith('!adminhelp') and commands.is_admin(message.author):
            await message.channel.send('Current admin-only commands: !adminadjust, !clear, !balance')

        elif message.content.startswith('!hello'):
            await message.reply('Hello!')

        elif 'deez' in message.content:
            await message.reply('Deez nuts')

        elif message.content.startswith('!verifycoin'):
            if message.mentions:
                for member in message.mentions:
                    await commands.verify_coin(guild, member)
                await message.reply(f'Verified coin for: ' + ', '.join([mention.display_name for mention in message.mentions]))
            else:
                await message.reply('No mentions. Follow the format: !verifycoin @user1 @user2 ...')

        elif message.content.startswith('!adminadjust') and commands.is_admin(message.author):
            messageContent = message.content.split()
            print(messageContent)
            if message.mentions and len(messageContent) == 3 and messageContent[2].lstrip('-').isnumeric():
                recieving_member = message.mentions[0]
                amount = int(messageContent[2])
                await commands.add_coin(guild, recieving_member, amount)
            else:
                await message.reply('Error parsing. Follow the format: !adminadjust @user ####')

        elif message.content.startswith('!clear') and commands.is_admin(message.author):
            if message.mentions:
                recieving_member = message.mentions[0]
                await commands.update_role(guild, recieving_member, config.getAttribute('defaultCoin'))
            else:
                await message.reply('Error parsing. Follow the format: !clear @user')

        elif message.content.startswith('!balance') and commands.is_admin(message.author):
            if message.mentions:
                recieving_member = message.mentions[0]
                balance = commands.get_coin(recieving_member.id)
                if balance:
                    await message.reply(recieving_member.display_name + '\'s balance: ' + str(balance) + '.')
                else:
                    await message.reply(recieving_member.display_name + ' has no balance.')
            else:
                await message.reply('Error parsing. Follow the format: !balance @user')

        elif message.content.startswith('!give'):
            messageContent = message.content.split()
            if message.mentions and len(messageContent) == 3 and messageContent[2].lstrip('-').isnumeric():
                recieving_member = message.mentions[0]
                amount = int(messageContent[2])
                if recieving_member.id == message.author.id:
                    await message.reply('Are you stupid or something?')
                elif amount > 0:
                    await commands.add_coin(guild, recieving_member, amount)
                    await commands.add_coin(guild, message.author, -amount )
                elif amount < 0:
                    await message.reply('Nice try bud.')
            else:
                await message.reply('Error parsing. Follow the format: !give @user ####')

        elif message.content.startswith('!bet'):
            messageContent = message.content.split(sep=None, maxsplit=3)
            if message.mentions and len(messageContent) == 4 and messageContent[2].lstrip('-').isnumeric():
                recieving_member = message.mentions[0]
                amount = int(messageContent[2])
                # if recieving_member.id == message.author.id:
                #     await message.reply('Are you stupid or something?')
                if amount < 0:
                    await message.reply('Nice try bud.')
                elif amount > 0:
                    # Have the challenged member confirm the bet
                    view = views.ConfirmBet(recieving_member.id)
                    betMessage = await message.channel.send(recieving_member.mention + ' do you accept the bet?',
                                                            view=view)
                    # Wait for the View to stop listening for input...
                    await view.wait()
                    if view.value is None:
                        await betMessage.delete()
                    elif not view.value:
                        await betMessage.edit(recieving_member.nick + ' has declined the bet.', view=None)
                    else:
                        betResultView = views.DecideBetOutcome(message.author, recieving_member)
                        await betMessage.edit(
                            recieving_member.display_name + ' has accepted the bet. After the bet is over, pick a winner below:',
                            view=betResultView)
                        await betResultView.wait()
                        if betResultView.winner is None:
                            await betMessage.edit('Something went wrong or the bet timed out.', view=None)
                        else:
                            winner = message.author if message.author.id == betResultView.winner else recieving_member
                            loser = message.author if message.author.id != betResultView.winner else recieving_member
                            await betMessage.edit(
                                winner.display_name + ' won the $' + str(amount) + ' bet against ' + loser.display_name +
                                ' for "' + messageContent[3] + '"!', view=None)
                            await commands.add_coin(guild, winner, amount)
                            await commands.add_coin(guild, loser, -amount )
            else:
                await message.reply('Error parsing. Follow the format: !bet @user #### reason here')

        # Can't parse command, reply best guess
        elif message.content.startswith('!'):
            command = message.content.split()[0]
            spellcheck = spellchecker.SpellChecker(language=None, case_sensitive=True)
            spellcheck.word_frequency.load_words(self.get_commands())
            correction = spellcheck.correction(command)
            if correction != command:
                await message.reply('Invalid command, did you mean ' + correction + '?  Try !help for valid commands.')
            else:
                await message.reply('Invalid command. Try !help for valid commands.')


intents = discord.Intents.default()
intents.members = True
client = Client(intents=intents)
client.run(config.getAttribute('token'))
