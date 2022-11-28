import discord
import config
import sql_client


# Define a simple View that gives us a confirmation menu
class ConfirmBet(discord.ui.View):
    def __init__(self, memberid: int):
        super().__init__()
        self.value = None
        self.memberId = memberid

    @discord.ui.button(label='Decline', style=discord.ButtonStyle.red)
    async def cancel(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id == self.memberId:
            self.value = False
            self.stop()
        else:
            await interaction.response.send_message('This is not your decision to make.', ephemeral=True)

    @discord.ui.button(label='Accept', style=discord.ButtonStyle.green)
    async def confirm(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id == self.memberId:
            self.value = True
            self.stop()
        else:
            await interaction.response.send_message('This is not your decision to make.', ephemeral=True)


class JoinWheel(discord.ui.View):
    def __init__(self, member: discord.Member, amount: int):
        super().__init__(timeout=120.0)
        self.members = [member]
        self.betAmount = amount

    @discord.ui.button(label='Join', style=discord.ButtonStyle.green)
    async def join(self, button: discord.ui.Button, interaction: discord.Interaction):
        if interaction.user not in self.members:
            currentCoin = sql_client.get_coin(interaction.user.id)
            if currentCoin - self.betAmount >= config.getAttribute('debtLimit'):
                self.members.append(interaction.user)
                await interaction.response.send_message('You\'re in the bet, good luck!', ephemeral=True)
                names = [member.display_name for member in self.members]
                joined_names = ', '.join(names)
                await interaction.message.edit(content=
                                               f'It\'s time to spin the wheel! The bet is {str(self.betAmount)} coin, and the winner takes all!\n'
                                               f'Click "Join" to play! You have 2 minutes to join the bet.\n'
                                               f'Current bettors: {joined_names}')
            else:
                await interaction.response.send_message('Sorry, you don\'t have enough money to join this bet.', ephemeral=True)
        else:
            await interaction.response.send_message('You\'ve already joined the bet, be patient.', ephemeral=True)

    @discord.ui.button(label='Cancel', style=discord.ButtonStyle.red)
    async def cancel(self, button: discord.ui.Button, interaction: discord.Interaction):
        if interaction.user == self.members[0]:
            self.members = None
            await interaction.response.send_message('You got it, cancelling the bet.', ephemeral=True)
            self.stop()
        else:
            await interaction.response.send_message('Sorry, only the person who started the bet can stop it.', ephemeral=True)

    @discord.ui.button(label='Start', style=discord.ButtonStyle.blurple)
    async def start(self, button: discord.ui.Button, interaction: discord.Interaction):
        if interaction.user == self.members[0]:
            await interaction.response.send_message('You got it, starting the bet.', ephemeral=True)
            self.stop()
        else:
            await interaction.response.send_message('Sorry, only the person who started the bet can start it.',
                                                    ephemeral=True)
