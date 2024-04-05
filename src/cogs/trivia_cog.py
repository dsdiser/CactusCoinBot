# This is pretty much deprecated for now, but keeping it around for reference or in case I want to bring it back
import datetime
from typing import Optional
import discord
from discord import NotFound
from discord.ext import commands, tasks
from pytz import timezone

from src import permissions, sql_client, views
from src.cogs.main_cog import adminCommands
from src.api_handlers.trivia_handler import Question, get_trivia_questions, Difficulty


# Daily trivia at 12AM EST
est = timezone("US/Eastern")
today = datetime.datetime.now(est).date()
midnight = est.localize(
    datetime.datetime.combine(today, datetime.time(0, 0)), is_dst=None
)
trivia_time_start = datetime.time(hour=0, tzinfo=est)


class TriviaCog(commands.Cog):
    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot
        self.question_amount = 50
        self.questions = []
        self.current_question: Optional[Question] = None
        self.current_index: int = 0
        self.trivia_category: Optional[str] = None
        self.trivia_difficulty: Optional[Difficulty] = None

    @commands.Cog.listener()
    async def on_ready(self) -> None:
        print("Bot logged in and enabled for Trivia")
        print("------")
        self.populate_question_list()
        self.trivia_loop.start()

    async def cog_unload(self):
        self.trivia_loop.cancel()

    def populate_question_list(self) -> bool:
        """
        Repopulates the list of questions
        :returns boolean: False if we have no new questions, true otherwise
        """
        questions = get_trivia_questions(
            str(self.question_amount), self.trivia_category, self.trivia_difficulty
        )
        # ensures no duplicates are in the question list
        question_hashes = [tuple((hash(question),)) for question in questions]
        seen_hash_result = sql_client.get_seen_questions()
        seen_hashes = []
        if seen_hash_result:
            seen_hashes = [q[0] for q in seen_hash_result]
        questions = [
            question
            for idx, question in enumerate(questions)
            if question_hashes[idx][0] not in seen_hashes
        ]
        if questions:
            self.questions = questions
            return True
        return False

    def get_question(self, idx: int = 0) -> Question:
        """Gets a question from the question list and repopulates the list if we run out of questions"""
        # if we've run out of questions
        if len(self.questions) == 0:
            self.populate_question_list()
        curr_question = self.questions.pop(idx)
        # adds question to table of seen questions to avoid duplicates
        sql_client.add_seen_question(hash(curr_question))
        return curr_question

    @discord.app_commands.command(
        name="trivia-time", description=adminCommands["/trivia-time"]
    )
    @discord.app_commands.check(permissions.is_admin)
    @discord.app_commands.guild_only()
    async def trivia_time(self, interaction: discord.Interaction) -> None:
        await interaction.response.send_message(
            f'Trivia time is {trivia_time_start.strftime("%H:%M:%S")}.', ephemeral=True
        )

    @discord.app_commands.command(
        name="trivia-start", description=adminCommands["/trivia-start"]
    )
    @discord.app_commands.check(permissions.is_admin)
    @discord.app_commands.guild_only()
    async def trivia_start(self, interaction: discord.Interaction) -> None:
        sql_client.add_channel(interaction.channel_id)
        await interaction.response.send_message(
            f"{interaction.channel.name} enabled for trivia questions."
        )

    @discord.app_commands.command(
        name="trivia-end", description=adminCommands["/trivia-end"]
    )
    @discord.app_commands.check(permissions.is_admin)
    @discord.app_commands.guild_only()
    async def trivia_end(self, interaction: discord.Interaction) -> None:
        sql_client.remove_channel(interaction.channel_id)
        await interaction.response.send_message(
            f"{interaction.channel.name} disabled for trivia questions."
        )

    @discord.app_commands.command(
        name="trivia-populate", description=adminCommands["/trivia-populate"]
    )
    @discord.app_commands.check(permissions.is_admin)
    @discord.app_commands.guild_only()
    async def trivia_populate(self, interaction: discord.Interaction) -> None:
        result = self.populate_question_list()
        result_str = "successful" if result else "not successful"
        await interaction.response.send_message(
            f"The re-population of the trivia question base was {result_str}",
            ephemeral=True,
        )

    @discord.app_commands.command(
        name="trivia-reward", description=adminCommands["/trivia-reward"]
    )
    @discord.app_commands.describe(reward="How much to set the reward to")
    @discord.app_commands.check(permissions.is_admin)
    @discord.app_commands.guild_only()
    async def trivia_reward(
        self, interaction: discord.Interaction, reward: int
    ) -> None:
        sql_client.update_reward(interaction.channel_id, reward)
        await interaction.response.send_message(
            f"The trivia reward has been set to {reward}", ephemeral=True
        )

    @discord.app_commands.command(
        name="trivia-reset", description=adminCommands["/trivia-reset"]
    )
    @discord.app_commands.describe(
        show_answer="Whether to show the answer for the previous day's question"
    )
    @discord.app_commands.describe(
        send_question="Whether to send another question to the channel"
    )
    @discord.app_commands.check(permissions.is_admin)
    @discord.app_commands.guild_only()
    async def trivia_reset(
        self,
        interaction: discord.Interaction,
        show_answer: bool = True,
        send_question: bool = True,
    ) -> None:
        action = "Resetting" if send_question else "Clearing"
        await interaction.response.send_message(f"{action} today's trivia question")
        await self.trivia_loop(show_answer=show_answer, send_question=send_question)

    @discord.app_commands.command(
        name="trivia-submit", description=adminCommands["/trivia-submit"]
    )
    @discord.app_commands.check(permissions.is_admin)
    @discord.app_commands.guild_only()
    async def trivia_submit(self, interaction: discord.Interaction) -> None:
        question = views.QuestionSubmit()
        await interaction.response.send_modal(question)
        await question.wait()
        self.questions.insert(0, question.submitted_question)

    @tasks.loop(time=trivia_time_start)
    async def trivia_loop(
        self, send_question: bool = True, show_answer: bool = True
    ) -> None:
        channels = sql_client.get_channels()
        for channel_id, message_id, reward in channels:
            channel = await self.bot.fetch_channel(channel_id)
            # Handle previous day's message
            if message_id:
                try:
                    message = await channel.fetch_message(message_id)
                except NotFound:
                    message = None
                if message is not None and self.current_question is None:
                    # If we don't have the question we don't know the answer, so we just wipe the question
                    await message.delete()
                elif message is not None and self.current_question is not None:
                    # Provide the set of people who got the answer correct and incorrect
                    correct_users = sql_client.get_correct_users(channel_id)
                    incorrect_users = sql_client.get_incorrect_users(channel_id)
                    if len(correct_users) or len(incorrect_users):
                        embed = discord.Embed(
                            title="Results", color=discord.Color.purple()
                        )
                        correct_user_str = (
                            "\n".join(
                                [f"<@{str(user_id)}>" for user_id in correct_users]
                            )
                            or "\u200b"
                        )
                        incorrect_user_str = (
                            "\n".join(
                                [f"<@{str(user_id)}>" for user_id in incorrect_users]
                            )
                            or "\u200b"
                        )
                        embed.add_field(name="Correct", value=correct_user_str)
                        embed.add_field(name="Incorrect", value=incorrect_user_str)
                    else:
                        embed = None
                    # Bold and underline the correct answer
                    choices = (
                        [
                            f"__**{choice}**__"
                            if choice == self.current_question.correct_answer
                            else choice
                            for choice in self.current_question.get_choices()
                        ]
                        if show_answer
                        else self.current_question.get_choices()
                    )
                    await message.edit(
                        content=f"> {self.current_question.question}\n"
                        f'{", ".join(choices)}\n',
                        embed=embed,
                        view=None,
                    )

            # Send today's trivia question
            if send_question:
                self.current_question = self.get_question()
                dropdown = views.DropdownView(
                    question=self.current_question, amount=reward
                )
                prompt = (
                    f"Today's daily trivia question!\n{self.current_question.question}"
                )
                message = await channel.send(content=prompt, view=dropdown)
                sql_client.update_message_id(channel_id, message.id)
            else:
                sql_client.update_message_id(channel_id, 0)

    @trivia_start.error
    @trivia_end.error
    @trivia_populate.error
    @trivia_reward.error
    @trivia_reset.error
    @trivia_submit.error
    async def permissions_error(self, interaction: discord.Interaction, error):
        if isinstance(error, discord.app_commands.errors.CheckFailure):
            await interaction.response.send_message(
                "You do not have permissions to use that command.", ephemeral=True
            )