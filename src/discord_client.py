import discord
import config
import commands
import views
import spellchecker


userCommands = {
    '!help': 'Usage: `!help`\n'
             'Outputs this list of commands.',
    '!setup': 'Usage: `!setup [user1] [user2] [user3]`\n'
              'Updates the user\'s role with their current amount or the default starting amount of coin if no record exists.',
    '!rankings': 'Usage: `!rankings`\n'
                 'Outputs power rankings for the server.',
    '!give': 'Usage: `!give [user] [amount]`\n'
             'Gives coin to a specific user, no strings attached.',
    '!bet': 'Usage: `!bet [user] [amount] [reason]`\n'
            'Starts a bet instance with another member, follow the button prompts to complete the bet.',
    '!wheel': 'Usage: `!wheel [amount]`\n'
              'Starts a wheel instance where each player buys in with the stated amount, winner takes all.',
    '!brokecheck': 'Usage: `!brokecheck [user]`\n'
                   'Checks a member\'s poverty level.',
    '!debtlimit': 'Usage: `!debtlimit`\n'
                  'Outputs the max amount of coin someone can go into debt.'
}

adminCommands = {
    '!adminhelp': 'Usage: `!adminhelp`\n'
                  'Outputs this list of commands.',
    '!adminadjust': 'Usage: `!adminadjust [user] [amount]`\n'
                    'Adds/subtracts coin from user\'s wallet.',
    '!balance': 'Usage: `!balance [user]`\n'
                'Outputs a user\'s wallet amount stored in the database.',
    '!clear': 'Usage: `!clear [user]`\n'
              'Clears a user\'s wallet of all coin and removes coin role.',
    '!bigwins': 'Usage: `!bigwins [week|month|year]`\n'
                'Outputs the greatest gains in the specified time period.',
    '!biglosses': 'Usage: `!biglosses [week|month|year]`\n'
                'Outputs the greatest losses in the specified time period.',
    '!reset': 'Usage: `!reset [user]`\n'
              'Resets a user\'s wallet to the default starting amount'
}

class Client(discord.Client):
    async def on_ready(self):
        print(f'Logged in as {self.user} (ID: {self.user.id})')
        print('------')
        # TODO: COLLECT EMOTE INFORMATION AND USE THAT INSTEAD OF HARDCODED VALUES

    async def on_message(self, message: discord.Message):
        # we do not want the bot to reply to itself or message in other channels
        if message.author.id == self.user.id or message.channel.name != config.getAttribute('channelName'):
            return

        guild = message.channel.guild
        if message.content.startswith('!help'):
            embed = discord.Embed(title='Cactus Coin Bot Commands', color=discord.Color.dark_green())
            for idx, key in enumerate(userCommands.keys()):
                embed.add_field(name=key, value=userCommands[key], inline=True)
                if idx % 2 == 1:
                    embed.add_field(name='\u200b', value='\u200b', inline=True)
            await message.channel.send(embed=embed)

        elif message.content.startswith('!adminhelp') and commands.is_admin(message.author):
            embed = discord.Embed(title='Cactus Coin Bot Admin Commands', color=discord.Color.orange())
            for idx, key in enumerate(adminCommands.keys()):
                embed.add_field(name=key, value=adminCommands[key], inline=True)
                if idx % 2 == 1:
                    embed.add_field(name='\u200b', value='\u200b', inline=True)
            await message.channel.send(embed=embed)

        elif message.content.startswith('!hello'):
            await message.reply('Hello!')

        elif message.content.startswith('!sadge'):
            await message.channel.send('<:sadge:763188455248887819>')

        elif 'deez' in message.content:
            await message.reply('Deez nuts')

        elif message.content.startswith('!setup'):
            if message.mentions:
                for member in message.mentions:
                    await commands.verify_coin(guild, member)
                await message.channel.send('Verified coin for: ' + ', '.join([mention.display_name for mention in message.mentions]))
            else:
                await message.reply('No mentions found. Follow the format: `!setup [user1] [user2] ...`')

        elif message.content.startswith('!rankings'):
            filePath = await commands.compute_rankings(message.guild)
            file = discord.File(filePath)
            await message.channel.send('Here are the current power rankings:', file=file)

        elif message.content.startswith('!debtlimit'):
            await message.channel.send(f'The current debt limit is {str(config.getAttribute("debtLimit", -10000))}.')

        elif message.content.startswith('!brokecheck'):
            if message.mentions:
                target_member = message.mentions[0]
                target_member_coin = commands.get_coin(target_member.id)
                if target_member_coin <= 0:
                    await message.channel.send(f'{target_member.display_name} is p <:OMEGALUL:392149610593779724> <:OMEGALUL:392149610593779724> r')
                else:
                    await message.channel.send(f'{target_member.display_name} isn\'t poor (yet)')

        elif message.content.startswith('!give'):
            messageContent = message.content.split()
            if message.mentions and len(messageContent) == 3 and messageContent[2].lstrip('-').isnumeric():
                recieving_member = message.mentions[0]
                amount = int(messageContent[2])
                author_coin = commands.get_coin(message.author.id)
                if author_coin - amount < config.getAttribute('debtLimit'):
                    await message.reply('You don\'t have this much coin to give <:sadge:763188455248887819>')
                elif recieving_member.id == message.author.id:
                    await message.reply('Are you stupid or something?')
                elif amount > 0:
                    await commands.add_coin(guild, recieving_member, amount)
                    await commands.add_coin(guild, message.author, -amount)
                elif amount < 0:
                    await message.reply('Nice try <:shanechamp:910353567603384340>')
            else:
                await message.reply('Error parsing command. Follow the format: `!give [user] [amount]`')

        elif message.content.startswith('!bet'):
            messageContent = message.content.split(sep=None, maxsplit=3)
            if message.mentions and len(messageContent) == 4 and messageContent[2].lstrip('-').isnumeric():
                recieving_member = message.mentions[0]
                recieving_member_coin = commands.get_coin(recieving_member.id)
                initiating_member_coin = commands.get_coin(message.author.id)
                amount = int(messageContent[2])
                if recieving_member_coin - amount < config.getAttribute('debtLimit'):
                    await message.channel.send(f'{recieving_member.display_name} doesn\'t have enough to bet <:OMEGALUL:392149610593779724>')
                elif initiating_member_coin - amount < config.getAttribute('debtLimit'):
                    await message.reply('You don\'t even have enough to bet <:OMEGALUL:392149610593779724>')
                elif recieving_member.id == message.author.id:
                    await message.reply('Are you stupid or something?')
                elif amount < 0:
                    await message.reply('Nice try <:shanechamp:910353567603384340>')
                elif amount > 0:
                    # Have the challenged member confirm the bet
                    view = views.ConfirmBet(recieving_member.id)
                    betMessage = await message.channel.send(f'{recieving_member.mention} do you accept the bet?',
                                                            view=view)
                    # Wait for the View to stop listening for input...
                    await view.wait()
                    if view.value is None:
                        # if the bet message times out
                        await betMessage.delete()
                    elif not view.value:
                        await betMessage.edit(f'{recieving_member.display_name} has declined the bet.', view=None)
                    else:
                        betResultView = views.DecideBetOutcome(message.author, recieving_member)
                        await betMessage.edit(
                            f'{recieving_member.display_name} has accepted the bet. After the bet is over, pick a winner below:',
                            view=betResultView)
                        await betResultView.wait()
                        if betResultView.winner is None:
                            await betMessage.edit('Something went wrong or the bet timed out.', view=None)
                        else:
                            winner = message.author if message.author.id == betResultView.winner else recieving_member
                            loser = message.author if message.author.id != betResultView.winner else recieving_member
                            await betMessage.edit(
                                f'{winner.display_name} won the ${str(amount)} bet against {loser.display_name} for "{messageContent[3]}"!',
                                view=None)
                            # resolve bet amounts
                            await commands.add_coin(guild, winner, amount)
                            await commands.add_coin(guild, loser, -amount)

            else:
                await message.reply('Error parsing command. Follow the format: `!bet [user] [amount] [reason]`')

        elif message.content.startswith('!wheel'):
            messageContent = message.content.split()
            if len(messageContent) == 2 and messageContent[1].isnumeric():
                betAmount = int(messageContent[1])
                wheelJoinView = views.JoinWheel(message.author, betAmount)
                wheelMessage = await message.channel.send(
                    f'It\'s time to spin the wheel! The bet is {messageContent[1]} coin, and the winner takes all!\n'
                    f'Click "Join" to play! You have 2 minutes to join the bet.\n'
                    f'Current bettors: {message.author.display_name}',
                    view=wheelJoinView
                )
                await wheelJoinView.wait()
                if wheelJoinView.members is None:
                    await wheelMessage.edit('The wheel bet has been cancelled.', view=None)
                    return
                elif len(wheelJoinView.members) == 1:
                    await wheelMessage.edit('Not enough people have joined this wheel, the bet is cancelled.', view=None)
                    return
                names = [member.display_name for member in wheelJoinView.members]
                joined_names = ', '.join(names)
                await wheelMessage.edit(f'The wheel is starting!\n Current bettors: {joined_names}', view=None)
                wheelGifPath, winnerIdx = await commands.generate_wheel(wheelJoinView.members)
                wheelGif = discord.File(wheelGifPath)
                winner = wheelJoinView.members[winnerIdx]
                winnings = len(wheelJoinView.members) * betAmount
                # send announcement message
                await message.channel.send(f'||{winner.display_name} has won the {winnings} coin wheel!||', file=wheelGif)
                for member in wheelJoinView.members:
                    if member == winner:
                        await commands.add_coin(guild, member, winnings - betAmount)
                    else:
                        await commands.add_coin(guild, member, -betAmount)

            else:
                await message.reply('Error parsing command. Follow the format: `!wheel [amount]`')

        elif message.content.startswith('!adminadjust') and commands.is_admin(message.author):
            messageContent = message.content.split()
            if message.mentions and len(messageContent) == 3 and messageContent[2].lstrip('-').isnumeric():
                recieving_member = message.mentions[0]
                amount = int(messageContent[2])
                await commands.add_coin(guild, recieving_member, amount, persist=False)
            else:
                await message.reply('Error parsing command. Follow the format: `!adminadjust [user] [amount]`')

        elif message.content.startswith('!reset') and commands.is_admin(message.author):
            if message.mentions:
                recieving_member = message.mentions[0]
                amount = commands.get_coin(recieving_member.id)
                await commands.add_coin(guild, recieving_member, -(amount - config.getAttribute('defaultCoin')), persist=False)
                await commands.update_role(guild, recieving_member, config.getAttribute('defaultCoin'))
            else:
                await message.reply('Error parsing command. Follow the format: `!reset [user]`')

        elif message.content.startswith('!clear') and commands.is_admin(message.author):
            if message.mentions:
                recieving_member = message.mentions[0]
                commands.remove_coin(recieving_member.id)
                await commands.remove_role(guild, recieving_member)
            else:
                await message.reply('Error parsing command. Follow the format: `!clear [user]`')

        elif message.content.startswith('!balance') and commands.is_admin(message.author):
            if message.mentions:
                recieving_member = message.mentions[0]
                balance = commands.get_coin(recieving_member.id)
                if balance:
                    await message.reply(f'{recieving_member.display_name}\'s balance: {str(balance)}.')
                else:
                    await message.reply(f'{recieving_member.display_name} has no balance.')
            else:
                await message.reply('Error parsing command. Follow the format: `!balance [user]`')

        elif message.content.startswith('!bigwins') or message.content.startswith('!biglosses') and commands.is_admin(message.author):
            messageContent = message.content.split()
            validPeriods = ['week', 'month', 'year']
            if len(messageContent) > 1 and messageContent[1] in validPeriods:
                wins = message.content.startswith('!bigwins')
                text = 'winners' if wins else 'losers'
                filePath = await commands.get_movements(message.guild, messageContent[1], wins)
                if filePath:
                    file = discord.File(filePath)
                    await message.channel.send(f'Here are the this {messageContent[1]}\'s biggest {text}:', file=file)
                else:
                    await message.reply(f'There are no {text} for this {messageContent[1]}.')
            else:
                await message.reply(f'Error parsing command. Follow the format: `{messageContent[0]} [week|month|year]`')
                

        elif message.content.startswith('!hardreset') and commands.is_dev(message.author):
            # BE CAREFUL WITH THIS IT WILL CLEAR OUT ALL COIN
            output = ''
            for member in guild.members:
                coin = commands.get_coin(member.id)
                commands.remove_coin(member.id)
                commands.remove_transactions(member.id)
                await commands.remove_role(guild, member)
                output += member.display_name + ' - ' + str(coin) + '\n'
            await message.reply('Everything cleared out...here\'s the short history just in case.\n' + output)

        # Can't parse command, reply best guess
        elif message.content.startswith('!'):
            command = message.content.split()[0]
            spellcheck = spellchecker.SpellChecker(language=None, case_sensitive=True)
            spellcheck.word_frequency.load_words(userCommands.keys())
            correction = spellcheck.correction(command)
            if correction != command:
                await message.reply(f'Invalid command, did you mean `{correction}`?  Try `!help` for valid commands.')
            else:
                await message.reply('Invalid command. Try `!help` for valid commands.')
