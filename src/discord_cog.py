import discord
from discord.ext import commands

import bot_helper
import config

userCommands = {
    '/help': 'Outputs a list of commands.',
    '/setup': 'Updates the user\'s role with their current amount or the default starting amount of coin if no record exists.',
    '/rankings': 'Outputs power rankings for the server.',
    '/give': 'Gives coin to a specific user, no strings attached.',
    '/bet': 'Usage: `/bet [user] [amount] [reason]`\n'
            'Starts a bet instance with another member, follow the button prompts to complete the bet.',
    '/wheel': 'Usage: `/wheel [amount]`\n'
              'Starts a wheel instance where each player buys in with the stated amount, winner takes all.',
    '/brokecheck': 'Usage: `/brokecheck [user]`\n'
                   'Checks a member\'s poverty level.',
    '/debtlimit': 'Usage: `/debtlimit`\n'
                  'Outputs the max amount of coin someone can go into debt.'
}

adminCommands = {
    '/adminhelp': 'Outputs a list of admin-specific commands.',
    '/adminadjust': 'Adds/subtracts coin from user\'s wallet.',
    '/balance': 'Outputs a user\'s wallet amount stored in the database.',
    '/clear': 'Clears a user\'s wallet of all coin and removes coin role.',
    '/bigwins': 'Usage: `/bigwins [week|month|year]`\n'
                'Outputs the greatest gains in the specified time period.',
    '/biglosses': 'Usage: `/biglosses [week|month|year]`\n'
                  'Outputs the greatest losses in the specified time period.',
    '/reset': 'Resets a user\'s wallet to the default starting amount',
    '/softreset': 'Resets all users\'s wallets to the default starting amount',
    '/fullclear': 'Clears all users\'s coins and clears all roles !DEV ONLY!',
}


class BotCog(commands.Cog):
    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot

    @commands.Cog.listener()
    async def on_ready(self):
        print(f'Logged in as {self.bot.user} (ID: {self.bot.user.id})')
        print('------')

    '''
    USER COMMANDS
    '''

    @discord.app_commands.command(name="help", description=userCommands["/help"])
    @discord.app_commands.guild_only()
    async def help(self, interaction: discord.Interaction) -> None:
        embed = discord.Embed(title='Cactus Coin Bot Commands', color=discord.Color.dark_green())
        for idx, key in enumerate(userCommands.keys()):
            embed.add_field(name=key, value=userCommands[key], inline=True)
            # column override for proper formatting in Discord
            if idx % 2 == 1:
                embed.add_field(name='\u200b', value='\u200b', inline=True)
        await interaction.response.send_message(embed=embed, ephemeral=True)

    @discord.app_commands.command(name="setup", description=userCommands["/setup"])
    @discord.app_commands.describe(user="The user to set up Cactus Coin for")
    @discord.app_commands.guild_only()
    async def setup(self, interaction: discord.Interaction, user: discord.member) -> None:
        await bot_helper.verify_coin(interaction.guild, user)
        await interaction.response.send_message(f'Verified coin for: {user.display_name}', ephemeral=True)

    @discord.app_commands.command(name="rankings", description=userCommands["/rankings"])
    @discord.app_commands.guild_only()
    async def rankings(self, interaction: discord.Interaction) -> None:
        filePath = await bot_helper.compute_rankings(interaction.guild)
        file = discord.File(filePath)
        await interaction.channel.send('Here are the current power rankings:', file=file)

    @discord.app_commands.command(name="give", description=userCommands["/give"])
    @discord.app_commands.describe(user="The user to give Cactus Coin to")
    @discord.app_commands.describe(user="The amount of Cactus Coin to give")
    @discord.app_commands.guild_only()
    async def give(self, interaction: discord.Interaction, user: discord.Member, amount: int) -> None:
        author_coin = bot_helper.get_coin(interaction.user.id)
        if author_coin - amount < config.getAttribute('debtLimit'):
            await interaction.channel.send('You don\'t have this much coin to give <:sadge:763188455248887819>',
                                           ephemeral=True)
        elif user.id == interaction.user.id:
            await interaction.channel.send('Are you stupid or something?', ephemeral=True)
        elif amount > 0:
            await bot_helper.add_coin(interaction.guild, user, amount)
            await bot_helper.add_coin(interaction.guild, interaction.user, -amount)
            await interaction.channel.send(f'{str(amount)} sent to {user.display_name}', ephemeral=True)
        elif amount < 0:
            await interaction.channel.send('Nice try <:shanechamp:910353567603384340>', ephemeral=True)

    '''
    ADMIN COMMANDS
    '''

    @discord.app_commands.command(name="adminhelp", description=adminCommands["/adminhelp"])
    @discord.app_commands.check(bot_helper.is_admin)
    @discord.app_commands.guild_only()
    async def admin_help(self, interaction: discord.Interaction) -> None:
        embed = discord.Embed(title='Cactus Coin Bot Commands', color=discord.Color.dark_green())
        for idx, key in enumerate(userCommands.keys()):
            embed.add_field(name=key, value=userCommands[key], inline=True)
            if idx % 2 == 1:
                embed.add_field(name='\u200b', value='\u200b', inline=True)
        await interaction.response.send_message(embed=embed, ephemeral=True)

    @discord.app_commands.command(name="adminadjust", description=adminCommands["/adminadjust"])
    @discord.app_commands.describe(user="The user to give Cactus Coin to")
    @discord.app_commands.describe(user="The amount of Cactus Coin to give")
    @discord.app_commands.check(bot_helper.is_admin)
    @discord.app_commands.guild_only()
    async def admin_adjust(self, interaction: discord.Interaction, user: discord.Member, amount: int) -> None:
        await bot_helper.add_coin(interaction.guild, user, amount, persist=False)
        await interaction.channel.send(f'Added {str(amount)} to {user.display_name}', ephemeral=True)

    @discord.app_commands.command(name="balance", description=adminCommands["/balance"])
    @discord.app_commands.describe(user="The user to check database's coin amount for")
    @discord.app_commands.check(bot_helper.is_admin)
    @discord.app_commands.guild_only()
    async def balance(self, interaction: discord.Interaction, user: discord.Member) -> None:
        balance = bot_helper.get_coin(user.id)
        if balance:
            await interaction.channel.send(f'{user.display_name}\'s balance: {str(balance)}.', ephemeral=True)
        else:
            await interaction.channel.send(f'{user.display_name}\'s has no balance.', ephemeral=True)

    @discord.app_commands.command(name="clear", description=adminCommands["/clear"])
    @discord.app_commands.describe(user="The user to clear coin for")
    @discord.app_commands.check(bot_helper.is_admin)
    @discord.app_commands.guild_only()
    async def clear(self, interaction: discord.Interaction, user: discord.Member) -> None:
        bot_helper.remove_coin(user.id)
        await bot_helper.remove_role(interaction.guild, user)
        await interaction.channel.send(f'{user.display_name}\'s coin has been cleared.', ephemeral=True)

    @discord.app_commands.command(name="reset", description=adminCommands["/reset"])
    @discord.app_commands.describe(user="The user to reset the coin for")
    @discord.app_commands.check(bot_helper.is_admin)
    @discord.app_commands.guild_only()
    async def reset(self, interaction: discord.Interaction, user: discord.Member) -> None:
        amount = bot_helper.get_coin(user.id)
        await bot_helper.add_coin(interaction.guild, user, -(amount - config.getAttribute('defaultCoin')),
                                  persist=False)
        await bot_helper.update_role(interaction.guild, user, config.getAttribute('defaultCoin'))

    @discord.app_commands.command(name="softreset", description=adminCommands["/softreset"])
    @discord.app_commands.check(bot_helper.is_admin)
    @discord.app_commands.guild_only()
    async def soft_reset(self, interaction: discord.Interaction) -> None:
        # BE CAREFUL WITH THIS IT WILL CLEAR OUT ALL COIN
        output = ''
        for member in interaction.guild.members:
            amount = bot_helper.get_coin(member.id)
            await bot_helper.add_coin(interaction.guild, member, -(amount - config.getAttribute('defaultCoin')),
                                      persist=False)
            await bot_helper.update_role(interaction.guild, member, config.getAttribute('defaultCoin'))
        await interaction.channel.send(
            f'Everyone\'s coin reset back to {config.getAttribute("defaultCoin")}...here\'s the short history just in case.\n{output}')

    @discord.app_commands.command(name="fullclear", description=adminCommands["/fullclear"])
    @discord.app_commands.check(bot_helper.is_dev)
    @discord.app_commands.guild_only()
    async def full_clear(self, interaction: discord.Interaction) -> None:
        # BE CAREFUL WITH THIS IT WILL CLEAR OUT ALL COIN
        output = ''
        for member in interaction.guild.members:
            coin = bot_helper.get_coin(member.id)
            bot_helper.remove_coin(member.id)
            bot_helper.remove_transactions(member.id)
            await bot_helper.remove_role(interaction.guild, member)
            output += f'{member.display_name} - {str(coin)}\n'
        await interaction.channel.send('Everything cleared out...here\'s the short history just in case.\n' + output)


async def setup(bot: commands.Bot):
    await bot.add_cog(BotCog(bot))
