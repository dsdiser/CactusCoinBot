import discord
import commands
import config


# Define a simple View that gives us a confirmation menu
class ConfirmBet(discord.ui.View):
    def __init__(self, memberid: int):
        super().__init__()
        self.value = None
        self.memberId = memberid

    @discord.ui.button(label='Decline', style=discord.ButtonStyle.red)
    async def cancel(self, button: discord.ui.Button, interaction: discord.Interaction):
        if interaction.user.id == self.memberId:
            self.value = False
            self.stop()
        else:
            await interaction.response.send_message('Hey this is not your decision to make.', ephemeral=True)

    @discord.ui.button(label='Accept', style=discord.ButtonStyle.green)
    async def confirm(self, button: discord.ui.Button, interaction: discord.Interaction):
        if interaction.user.id == self.memberId:
            self.value = True
            self.stop()
        else:
            await interaction.response.send_message('Hey this is not your decision to make.', ephemeral=True)


# Button prompts that let members decide who won the bet
class DecideBetOutcome(discord.ui.View):
    def __init__(self, member1: discord.Member, member2: discord.Member):
        super().__init__(timeout=600.0)
        self.winner = None
        self.member1 = member1
        self.member1choice = None
        button1 = discord.ui.Button(label=member1.display_name, style=discord.ButtonStyle.blurple)
        button1.callback = self.member1win

        self.member2 = member2
        self.member2choice = None
        button2 = discord.ui.Button(label=member2.display_name, style=discord.ButtonStyle.blurple)
        button2.callback = self.member2win

        self.add_item(button1)
        self.add_item(button2)

    # Choose the bet outcome as member1
    async def member1win(self, interaction: discord.Interaction):
        if interaction.user.id == self.member1.id:
            self.member1choice = self.member1.id
        elif interaction.user.id == self.member2.id:
            self.member2choice = self.member1.id

        # if both parties agree to the result
        if self.member1choice and self.member2choice and self.member1choice == self.member2choice:
            self.winner = self.member1.id
            self.stop()
        # if parties do not agree to the result, have a third party decide the winner.
        elif self.member1choice and self.member2choice and self.member1choice != self.member2choice and interaction.user.id != self.member1.id and interaction.user.id != self.member2.id:
            self.winner = self.member1.id
            self.stop()
        elif self.member1choice and self.member2choice and self.member1choice != self.member2choice:
            await interaction.response.send_message('Winner chosen, but there is a conflict. Have a third party vote to solve this dispute.', ephemeral=True)
        else:
            await interaction.response.send_message('Winner chosen, waiting for other party...', ephemeral=True)

    # Choose the bet outcome as member2
    async def member2win(self, interaction: discord.Interaction):
        if interaction.user.id == self.member1.id:
            self.member1choice = self.member2.id
        elif interaction.user.id == self.member2.id:
            self.member2choice = self.member2.id

        # if both parties agree to the result
        if self.member1choice and self.member2choice and self.member1choice == self.member2choice:
            self.winner = self.member2.id
            self.stop()
        # if parties do not agree to the result, have a third party decide the winner.
        elif self.member1choice and self.member2choice and self.member1choice != self.member2choice and interaction.user.id != self.member1.id and interaction.user.id != self.member2.id:
            self.winner = self.member2.id
            self.stop()
        elif self.member1choice and self.member2choice and self.member1choice != self.member2choice:
            await interaction.response.send_message('Winner chosen, but there is a conflict. Have a third party vote to solve this dispute.', ephemeral=True)
        else:
            await interaction.response.send_message('Winner chosen, waiting for other party...', ephemeral=True)


class JoinWheel(discord.ui.View):
    def __init__(self, member: discord.Member, amount: int):
        super().__init__(timeout=120.0)
        self.members = [member]
        self.betAmount = amount

    @discord.ui.button(label='Join', style=discord.ButtonStyle.green)
    async def join(self, button: discord.ui.Button, interaction: discord.Interaction):
        if interaction.user not in self.members:
            currentCoin = commands.get_coin(interaction.user.id)
            if currentCoin - self.betAmount >= config.getAttribute('debtLimit'):
                self.members.append(interaction.user)
                await interaction.response.send_message('You\'re in the bet, good luck!', ephemeral=True)
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