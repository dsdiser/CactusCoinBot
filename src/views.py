import discord

import bot_helper
import config
import sql_client
from typing import Literal, Optional
from trivia_handler import Question, QuestionType


# Define a simple View that gives us a confirmation menu
class ConfirmBet(discord.ui.View):
    def __init__(self, memberid: int):
        # 10 second timeout
        super().__init__(timeout=600.0)
        self.value = None
        self.member_id = memberid

    @discord.ui.button(label='Decline', style=discord.ButtonStyle.red)
    async def cancel(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id == self.member_id:
            self.value = False
            self.stop()
        else:
            await interaction.response.send_message('This is not your decision to make.', ephemeral=True)

    @discord.ui.button(label='Accept', style=discord.ButtonStyle.green)
    async def confirm(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id == self.member_id:
            self.value = True
            self.stop()
        else:
            await interaction.response.send_message('This is not your decision to make.', ephemeral=True)


class Dropdown(discord.ui.Select):
    def __init__(self, question: Question, disabled: bool, amount: int):
        self.interacted_users = []
        self.question = question
        self.amount = amount
        self.selectedOption = ''
        # Set the options that will be presented inside the dropdown
        self.emojis = ['1️⃣', '2️⃣', '3️⃣', '4️⃣']

        options = [
            discord.SelectOption(label=choice, emoji=self.emojis[idx])
            for idx, choice in enumerate(question.get_choices())
        ]

        # The placeholder is what will be shown when no option is chosen
        # The min and max values indicate we can only pick one of the three options
        # The options parameter defines the dropdown options. We defined this above
        super().__init__(
            placeholder='Choose your answer here...',
            min_values=1,
            max_values=1,
            options=options,
            disabled=disabled
        )

    async def callback(self, interaction: discord.Interaction):
        # Use the interaction object to send a response message containing
        # the user's favourite colour or choice. The self object refers to the
        # Select object, and the values attribute gets a list of the user's
        # selected options. We only want the first one.
        if interaction.user.id in self.interacted_users:
            await interaction.response.send_message(f'You\'ve already given your response.', ephemeral=True)
        else:
            if self.values[0] == self.question.correct_answer:
                await bot_helper.add_coin(interaction.guild, interaction.user, self.amount)
                sql_client.update_correct_answer_count(interaction.user.id)
                # Updates the channel's list of incorrect users
                correct_users = sql_client.get_correct_users(interaction.channel_id)
                correct_users.append(interaction.user.id)
                sql_client.update_correct_users(interaction.channel_id, correct_users)
                self.interacted_users.append(interaction.user.id)
                await interaction.response.send_message(
                    f'Correct answer! You\'ve received {format(self.amount, ",d")} coin!',
                    ephemeral=True
                )
            else:
                sql_client.update_incorrect_answer_count(interaction.user.id)
                # Updates the channel's list of incorrect users
                incorrect_users = sql_client.get_incorrect_users(interaction.channel_id)
                incorrect_users.append(interaction.user.id)
                sql_client.update_incorrect_users(interaction.channel_id, incorrect_users)
                self.interacted_users.append(interaction.user.id)
                await interaction.response.send_message(
                    f'Incorrect answer {config.get_attribute("sadEmote", "")} no coin awarded.',
                    ephemeral=True
                )


class DropdownView(discord.ui.View):
    def __init__(self, question: Question, disabled: bool = False, amount: int = 25):
        super().__init__()
        # Adds the dropdown to our view object.
        self.add_item(Dropdown(question=question, disabled=disabled, amount=amount))


class QuestionSubmit(discord.ui.Modal, title='Input your question'):
    question = discord.ui.TextInput(
        label='Question',
        style=discord.TextStyle.long,
        placeholder='Put question here...'
    )
    correct_answer = discord.ui.TextInput(
        label='Correct answer',
        style=discord.TextStyle.short,
        placeholder='Put correct answer here...'
    )
    answer_2 = discord.ui.TextInput(
        label='Incorrect answer',
        style=discord.TextStyle.short,
        placeholder='Put 1st incorrect answer here...',
    )
    answer_3 = discord.ui.TextInput(
        label='Incorrect answer',
        style=discord.TextStyle.short,
        placeholder='Put 2nd incorrect answer here...',
        required=False,
    )
    answer_4 = discord.ui.TextInput(
        label='Incorrect answer',
        style=discord.TextStyle.short,
        placeholder='Put 3rd incorrect answer here...',
        required=False
    )
    submitted_question: Optional[Question] = None

    async def on_submit(self, interaction: discord.Interaction):
        is_boolean = self.correct_answer.value.lower() == 'true' or self.answer_2.value.lower() == 'true'
        question_type: QuestionType = 'boolean' if is_boolean else 'multiple'
        incorrect_answers = [answer for answer in [self.answer_2.value, self.answer_3.value, self.answer_4.value] if answer]
        q = Question(
            category='custom',
            type=question_type,
            question=self.question.value,
            correct_answer=self.correct_answer.value,
            incorrect_answers=incorrect_answers
        )
        self.submitted_question = q
        await interaction.response.send_message(f'Added question to list.', ephemeral=True)
        self.stop()

    async def on_error(self, interaction: discord.Interaction, error: Exception) -> None:
        await interaction.response.send_message('Oops! Something went wrong.', ephemeral=True)


class JoinWheel(discord.ui.View):
    def __init__(self, member: discord.Member, amount: int):
        super().__init__(timeout=120.0)
        self.members = [member]
        self.betAmount = amount

    @discord.ui.button(label='Join', style=discord.ButtonStyle.green)
    async def join(self, button: discord.ui.Button, interaction: discord.Interaction):
        if interaction.user not in self.members:
            currentCoin = sql_client.get_coin(interaction.user.id)
            if currentCoin - self.betAmount >= config.get_attribute('debtLimit'):
                self.members.append(interaction.user)
                await interaction.response.send_message('You\'re in the bet, good luck!', ephemeral=True)
                names = [member.display_name for member in self.members]
                joined_names = ', '.join(names)
                await interaction.message.edit(
                    content=f'It\'s time to spin the wheel! The bet is {str(self.betAmount)} coin, and the winner takes all!\n'
                            f'Click "Join" to play! You have 2 minutes to join the bet.\n'
                            f'Current bettors: {joined_names}'
                )
            else:
                await interaction.response.send_message(
                    'Sorry, you don\'t have enough money to join this bet.',
                    ephemeral=True
                )
        else:
            await interaction.response.send_message(
                'You\'ve already joined the bet, be patient.',
                ephemeral=True
            )

    @discord.ui.button(label='Cancel', style=discord.ButtonStyle.red)
    async def cancel(self, button: discord.ui.Button, interaction: discord.Interaction):
        if interaction.user == self.members[0]:
            self.members = None
            await interaction.response.send_message('You got it, cancelling the bet.', ephemeral=True)
            self.stop()
        else:
            await interaction.response.send_message(
                'Sorry, only the person who started the bet can stop it.',
                ephemeral=True
            )

    @discord.ui.button(label='Start', style=discord.ButtonStyle.blurple)
    async def start(self, button: discord.ui.Button, interaction: discord.Interaction):
        if interaction.user == self.members[0]:
            await interaction.response.send_message('You got it, starting the bet.', ephemeral=True)
            self.stop()
        else:
            await interaction.response.send_message(
                'Sorry, only the person who started the bet can start it.',
                ephemeral=True
            )
