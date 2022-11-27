import discord
from discord.ext import commands
from typing import Literal

import bot_helper
import config
import sql_client
import views

TIME_PERIOD = Literal["week", "month", "year"]

userCommands = {
    '/help': 'Outputs a list of commands.',
    '/setup': 'Sets up the user\'s Cactus Coin role.',
    '/rankings': 'Outputs power rankings for the server.',
    '/give': 'Gives coin to a specific user, no strings attached.',
    '/bet': 'Starts a bet with another member.',
    '/end-bet': 'Ends an existing bet with another member.',
    '/cancel-bet': 'Cancels an existing bet with another member.',
    '/list-bets': 'Lists the current active bets',
    '/wheel': 'Usage: `/wheel [amount]`\n'
              'Starts a wheel instance where each player buys in with the stated amount, winner takes all.',
}

adminCommands = {
    '/admin-help': '!ADMIN ONLY! Outputs a list of admin-specific commands.',
    '/admin-adjust': '!ADMIN ONLY! Adds/subtracts coin from user\'s wallet.',
    '/balance': '!ADMIN ONLY! Outputs a user\'s wallet amount stored in the database.',
    '/clear': '!ADMIN ONLY! Clears a user\'s wallet of all coin and removes coin role.',
    '/big-wins': '!ADMIN ONLY! Outputs the greatest gains in the specified time period.',
    '/reset': '!ADMIN ONLY! Resets a user\'s wallet to the default starting amount',
    '/soft-reset': '!ADMIN ONLY! Resets all users\'s wallets to the default starting amount',
    '/full-clear': '!DEV ONLY! Clears all users\'s coins and clears all roles',
}


class BotCog(commands.Cog):
    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot

    @commands.Cog.listener()
    async def on_ready(self) -> None:
        print(f'Logged in as {self.bot.user} (ID: {self.bot.user.id})')
        print('------')

    @commands.Cog.listener()
    async def on_message(self, message: discord.Message) -> None:
        """
        Syncs slash commands to discord server
        :param message:
        """
        if message.content == 'pls sync':
            self.bot.tree.copy_global_to(guild=message.guild)
            await self.bot.tree.sync(guild=message.guild)
            await message.reply('Synced commands.')

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
    async def setup(self, interaction: discord.Interaction, user: discord.Member) -> None:
        await bot_helper.verify_coin(interaction.guild, user)
        await interaction.response.send_message(f'Verified coin for: {user.display_name}', ephemeral=True)

    @discord.app_commands.command(name="rankings", description=userCommands["/rankings"])
    @discord.app_commands.guild_only()
    async def rankings(self, interaction: discord.Interaction) -> None:
        file_path = await bot_helper.compute_rankings(interaction.guild)
        file = discord.File(file_path)
        await interaction.response.send_message('Here are the current power rankings:', file=file)

    @discord.app_commands.command(name="give", description=userCommands["/give"])
    @discord.app_commands.describe(user="The user to give Cactus Coin to")
    @discord.app_commands.describe(amount="The amount of Cactus Coin to give")
    @discord.app_commands.guild_only()
    async def give(self, interaction: discord.Interaction, user: discord.Member, amount: int) -> None:
        author_coin = sql_client.get_coin(interaction.user.id)
        if author_coin - amount < config.getAttribute('debtLimit'):
            await interaction.response.send_message(
                'You don\'t have this much coin to give <:sadge:763188455248887819>',
                ephemeral=True)
        elif user.id == interaction.user.id:
            await interaction.response.send_message('Are you stupid or something?', ephemeral=True)
        elif amount > 0:
            await bot_helper.add_coin(interaction.guild, user, amount)
            await bot_helper.add_coin(interaction.guild, interaction.user, -amount)
            await interaction.response.send_message(f'{str(amount)} coin sent to {user.display_name}', ephemeral=True)
        elif amount < 0:
            await interaction.response.send_message('Nice try <:shanechamp:910353567603384340>', ephemeral=True)

    @discord.app_commands.command(name="bet", description=userCommands["/bet"])
    @discord.app_commands.describe(user="The user to bet Cactus Coin against")
    @discord.app_commands.describe(amount="The amount of Cactus Coin to bet")
    @discord.app_commands.describe(reason="Short description of what the bet is for")
    @discord.app_commands.guild_only()
    async def bet_start(self, interaction: discord.Interaction, user: discord.Member, amount: int, reason: str) -> None:
        author_coin = sql_client.get_coin(interaction.user.id)
        opponent_coin = sql_client.get_coin(user.id)
        if author_coin - amount < config.getAttribute('debtLimit'):
            await interaction.response.send_message(
                'You don\'t have this much coin to bet <:sadge:763188455248887819>',
                ephemeral=True)
        elif opponent_coin - amount < config.getAttribute('debtLimit'):
            await interaction.response.send_message(
                f'{user.mention} doesn\'t have this much coin to bet <:sadge:763188455248887819>',
                ephemeral=True)
        elif user.id == interaction.user.id:
            await interaction.response.send_message('Are you stupid or something?', ephemeral=True)
        elif amount > 0:
            # use view to start interaction and get both users to accept the bet
            view = views.ConfirmBet(user.id)
            await interaction.response.send_message(
                f'{interaction.user.mention} has challenged {user.mention} to a {str(amount)} coin bet '
                f'for: "{reason}"\n{user.mention}, do you accept?', view=view)
            await view.wait()
            # Deal with view response
            amount_str = str(amount)
            if view.value is None:
                # view expired
                await interaction.edit_original_response(content=
                                                         f'{user.mention} didn\'t respond to the {amount_str} coin bet '
                                                         f'from {interaction.user.mention} for: "{reason}".', view=None)
            elif not view.value:
                # user declines
                await interaction.edit_original_response(content=
                                                         f'{user.mention} has declined the {amount_str} coin bet '
                                                         f'from {interaction.user.mention} for: "{reason}".', view=None)
            else:
                # bet has gone through, start bet instance
                bet_id = bot_helper.start_bet(interaction.user, user, amount, reason)
                await interaction.edit_original_response(content=
                                                         f'{interaction.user.mention} has started a {amount_str} '
                                                         f' coin bet against {user.mention} for: "{reason}"\n'
                                                         f'ID: {bet_id}',
                                                         view=None)
        elif amount <= 0:
            await interaction.response.send_message('You can\'t do negative or zero bets', ephemeral=True)

    @discord.app_commands.command(name="end-bet", description=userCommands["/end-bet"])
    @discord.app_commands.describe(bet_id="The 4-letter bet ID associated with your bet")
    @discord.app_commands.describe(winner="The user who won the bet")
    @discord.app_commands.guild_only()
    async def bet_end(self, interaction: discord.Interaction, bet_id: str, winner: discord.Member) -> None:
        original_bet = sql_client.fetch_bet(bet_id)
        if not original_bet:
            await interaction.response.send_message('A bet with this ID does not exist.', ephemeral=True)
        (bet_id, date, author, opponent, amount, reason, active) = original_bet
        # Verify interaction user is one of the active betters
        if interaction.user.id != author and interaction.user.id != opponent:
            await interaction.response.send_message('You are not one of the parties in this bet.', ephemeral=True)
        elif winner.id != author and winner.id != opponent:
            await interaction.response.send_message(
                f'{winner.mention} is not one of the parties in this bet.', ephemeral=True)

        # Make the view for the other member to accept this result

    @discord.app_commands.command(name="list-bets", description=userCommands["/list-bets"])
    @discord.app_commands.guild_only()
    async def list_bets(self, interaction: discord.Interaction) -> None:
        bets = sql_client.get_active_bets()
        if not bets:
            await interaction.response.send_message('There are no active bets.')
        else:
            embed = discord.Embed(title='Active Bets', color=discord.Color.dark_green())
            for (bet_id, date, author, opponent, amount, reason, active) in bets:
                title = f'{str(amount)} coin'
                description = f'<@{author}> vs <@{opponent}>\n'\
                              f'Reason: "{reason}"\n' \
                              f'Bet ID: {bet_id}'
                embed.add_field(name=title, value=description, inline=False)
            await interaction.response.send_message('', embed=embed)

    '''
    ADMIN COMMANDS
    '''

    @discord.app_commands.command(name="admin-help", description=adminCommands["/admin-help"])
    @discord.app_commands.check(bot_helper.is_admin)
    @discord.app_commands.guild_only()
    async def admin_help(self, interaction: discord.Interaction) -> None:
        embed = discord.Embed(title='Cactus Coin Bot Commands', color=discord.Color.dark_green())
        for idx, key in enumerate(userCommands.keys()):
            embed.add_field(name=key, value=userCommands[key], inline=True)
            if idx % 2 == 1:
                embed.add_field(name='\u200b', value='\u200b', inline=True)
        await interaction.response.send_message(embed=embed, ephemeral=True)

    @discord.app_commands.command(name="admin-adjust", description=adminCommands["/admin-adjust"])
    @discord.app_commands.describe(user="The user to give Cactus Coin to")
    @discord.app_commands.describe(amount="The amount of Cactus Coin to give")
    @discord.app_commands.describe(persist="Whether the transaction should go on the record")
    @discord.app_commands.check(bot_helper.is_admin)
    @discord.app_commands.guild_only()
    async def admin_adjust(self, interaction: discord.Interaction, user: discord.Member, amount: int,
                           persist: bool) -> None:
        await bot_helper.add_coin(interaction.guild, user, amount, persist=persist)
        await interaction.response.send_message(f'Added {str(amount)} to {user.display_name}', ephemeral=True)

    @discord.app_commands.command(name="balance", description=adminCommands["/balance"])
    @discord.app_commands.describe(user="The user to check database's coin amount for")
    @discord.app_commands.check(bot_helper.is_admin)
    @discord.app_commands.guild_only()
    async def balance(self, interaction: discord.Interaction, user: discord.Member) -> None:
        balance = sql_client.get_coin(user.id)
        if balance:
            await interaction.response.send_message(f'{user.display_name}\'s balance: {str(balance)}.', ephemeral=True)
        else:
            await interaction.response.send_message(f'{user.display_name}\'s has no balance.', ephemeral=True)

    @discord.app_commands.command(name="big-wins", description=adminCommands["/big-wins"])
    @discord.app_commands.describe(period="The period over which to look at")
    @discord.app_commands.check(bot_helper.is_admin)
    @discord.app_commands.guild_only()
    async def big_wins(self, interaction: discord.Interaction, period: TIME_PERIOD) -> None:
        filePath = await bot_helper.get_movements(interaction.guild, period, True)
        if filePath:
            file = discord.File(filePath)
            await interaction.response.send_message(f'Here are the this {period}\'s biggest winners:', file=file)
        else:
            await interaction.response.send_message(f'There are no winners for this {period}.')

    @discord.app_commands.command(name="clear", description=adminCommands["/clear"])
    @discord.app_commands.describe(user="The user to clear coin for")
    @discord.app_commands.check(bot_helper.is_admin)
    @discord.app_commands.guild_only()
    async def clear(self, interaction: discord.Interaction, user: discord.Member) -> None:
        sql_client.remove_coin(user.id)
        await bot_helper.remove_role(interaction.guild, user)
        await interaction.response.send_message(f'{user.display_name}\'s coin has been cleared.', ephemeral=True)

    @discord.app_commands.command(name="reset", description=adminCommands["/reset"])
    @discord.app_commands.describe(user="The user to reset the coin for")
    @discord.app_commands.check(bot_helper.is_admin)
    @discord.app_commands.guild_only()
    async def reset(self, interaction: discord.Interaction, user: discord.Member) -> None:
        amount = sql_client.get_coin(user.id)
        await bot_helper.add_coin(interaction.guild, user, -(amount - config.getAttribute('defaultCoin')),
                                  persist=False)
        await bot_helper.update_role(interaction.guild, user, config.getAttribute('defaultCoin'))

    @discord.app_commands.command(name="soft-reset", description=adminCommands["/soft-reset"])
    @discord.app_commands.check(bot_helper.is_admin)
    @discord.app_commands.guild_only()
    async def soft_reset(self, interaction: discord.Interaction) -> None:
        # BE CAREFUL WITH THIS IT WILL CLEAR OUT ALL COIN
        output = ''
        for member in interaction.guild.members:
            amount = sql_client.get_coin(member.id)
            await bot_helper.add_coin(interaction.guild, member, -(amount - config.getAttribute('defaultCoin')),
                                      persist=False)
            await bot_helper.update_role(interaction.guild, member, config.getAttribute('defaultCoin'))
        await interaction.response.send_message(
            f'Everyone\'s coin reset back to {config.getAttribute("defaultCoin")}...here\'s the short history just in '
            f'case.\n{output}')

    @discord.app_commands.command(name="full-clear", description=adminCommands["/full-clear"])
    @discord.app_commands.check(bot_helper.is_dev)
    @discord.app_commands.guild_only()
    async def full_clear(self, interaction: discord.Interaction) -> None:
        # BE CAREFUL WITH THIS IT WILL CLEAR OUT ALL COIN
        output = ''
        for member in interaction.guild.members:
            coin = sql_client.get_coin(member.id)
            sql_client.remove_coin(member.id)
            sql_client.remove_transactions(member.id)
            await bot_helper.remove_role(interaction.guild, member)
            output += f'{member.display_name} - {str(coin)}\n'
        await interaction.response.send_message(
            'Everything cleared out...here\'s the short history just in case.\n' + output)

    @admin_help.error
    @admin_adjust.error
    @balance.error
    @big_wins.error
    @clear.error
    @reset.error
    @soft_reset.error
    @full_clear.error
    async def permissions_error(self, interaction: discord.Interaction, error):
        if isinstance(error, discord.app_commands.errors.CheckFailure):
            await interaction.response.send_message('You do not have permissions to use that command.', ephemeral=True)


async def setup(bot: commands.Bot):
    await bot.add_cog(BotCog(bot))