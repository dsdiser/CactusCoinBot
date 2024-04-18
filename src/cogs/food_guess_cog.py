import datetime
from typing import Optional
import discord
from discord import NotFound
from discord.ext import commands, tasks
from pytz import timezone


from src import permissions
from src.api_handlers.food_handler import generate_food_questions
from src.cogs.main_cog import adminCommands
from src.models import CountryAnswer, Food, FoodChannel


# Daily trivia at 12AM EST
est = timezone("US/Eastern")
today = datetime.datetime.now(est).date()
midnight = est.localize(
    datetime.datetime.combine(today, datetime.time(0, 0)), is_dst=None
)
food_guess_time_start = datetime.time(hour=0, tzinfo=est)

class FoodGuessCog(commands.Cog):
    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot

    @commands.Cog.listener()
    async def on_ready(self) -> None:
        print("Bot enabled for Food Guessing")
        print("------")
        self.food_loop.start()

    async def cog_unload(self):
        self.food_loop.cancel()

    @discord.app_commands.command(
        name="frivia-start", description=adminCommands["/frivia-start"]
    )
    @discord.app_commands.check(permissions.is_admin)
    @discord.app_commands.guild_only()
    async def frivia_start(self, interaction: discord.Interaction) -> None:
        food_channel, created = FoodChannel.get_or_create(id=interaction.channel_id)
        assert interaction.channel is not None
        await interaction.response.send_message(
            f"{interaction.channel.name} {'already' if created else ''} enabled for food trivia."
        )

    @discord.app_commands.command(
        name="frivia-end", description=adminCommands["/frivia-end"]
    )
    @discord.app_commands.check(permissions.is_admin)
    @discord.app_commands.guild_only()
    async def frivia_end(self, interaction: discord.Interaction) -> None:
        assert interaction.channel is not None
        channels_removed = FoodChannel.delete().where(FoodChannel.id == interaction.channel_id)
        if channels_removed:
            await interaction.response.send_message(f"{interaction.channel.name} disabled for food trivia.")
        else:
            await interaction.response.send_message("This channel is not enabled for food trivia.")

    async def solve_question(self):
        # solve the previous question

        # pull the last day's message id

        # get the message and barcode

        # use the barcode to get the solutions

        # output the solutions with each user's score out of the number of solutions
        print("hi")

    @tasks.loop(time=food_guess_time_start)
    async def food_loop(
        self, send_question: bool = True, show_answer: bool = True
    ) -> None:
        channel_id = FoodChannel.get()
        channel = await self.bot.fetch_channel(channel_id)
        await self.solve_question()
        # pull a new unused food and answers from the database
        unused_food = Food.get_or_none(Food.used is False)
        # if there is not one, pull new questions and retry. If that fails, print a message to the channel
        if unused_food is None:
            generate_food_questions()
        unused_food = Food.get_or_none(Food.used is False)
        if unused_food is None:
            await channel.send(content="Bot couldn't fetch a question to ask, pls elp.")
            return
        
        # craft the message to send to the channel

        # after it is sent, mark the food item as used