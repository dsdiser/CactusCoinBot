from typing import Optional
import discord

from src import bot_helper, config, sql_client
from src.api_handlers.trivia_handler import Question, QuestionType


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
            await interaction.response.send_message("You've already given your response.", ephemeral=True)
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
        super().__init__(timeout=None)
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
        await interaction.response.send_message('Added question to list.', ephemeral=True)
        self.stop()

    async def on_error(self, interaction: discord.Interaction, error: Exception) -> None:
        await interaction.response.send_message('Oops! Something went wrong.', ephemeral=True)
