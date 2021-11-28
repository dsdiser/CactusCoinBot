import discord


# Define a simple View that gives us a confirmation menu
class ConfirmBet(discord.ui.View):
    def __init__(self, memberid: int):
        super().__init__()
        self.value = None
        self.memberId = memberid

    # This one is similar to the confirmation button except sets the inner value to `False`
    @discord.ui.button(label='Decline', style=discord.ButtonStyle.red)
    async def cancel(self, button: discord.ui.Button, interaction: discord.Interaction):
        if interaction.user.id == self.memberId:
            # await interaction.response.send_message(interaction.user.mention + ' has declined the bet.', ephemeral=True)
            self.value = False
            self.stop()

    # When the confirm button is pressed, set the inner value to `True` and
    # stop the View from listening to more input.
    # We also send the user an ephemeral message that we're confirming their choice.
    @discord.ui.button(label='Accept', style=discord.ButtonStyle.green)
    async def confirm(self, button: discord.ui.Button, interaction: discord.Interaction):
        if interaction.user.id == self.memberId:
            # await interaction.response.send_message(interaction.user.mention + ' has accepted the bet.', ephemeral=True)
            self.value = True
            self.stop()


# Button prompts that let members decide who won the bet
class DecideBetOutcome(discord.ui.View):
    def __init__(self, member1: discord.Member, member2: discord.Member):
        super().__init__(timeout=600.0)
        self.winner = None
        self.member1 = member1
        self.member1choice = None
        button1 = discord.ui.Button(label=member1.display_name, style=discord.ButtonStyle.blurple)
        button1.callback = self.member1Win

        self.member2 = member2
        self.member2choice = None
        button2 = discord.ui.Button(label=member2.display_name, style=discord.ButtonStyle.blurple)
        button2.callback = self.member2Win

        self.add_item(button1)
        self.add_item(button2)

    # Choose the bet outcome as member1
    async def member1Win(self, interaction: discord.Interaction):
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


    # Choose the bet outcome as member2
    async def member2Win(self, interaction: discord.Interaction):
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


