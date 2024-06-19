import calendar
import datetime
from typing import List
import discord
from discord.ext import commands, tasks
from pytz import timezone


from src import permissions
from src.cogs.main_cog import adminCommands
from src.models import Game, ChallengeChannel, database


# Challenge alerts 
est = timezone("US/Eastern")
challenge_alert_time_start = datetime.time(hour=1, tzinfo=est)

class ChallengesCog(commands.Cog):
    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot

    @commands.Cog.listener()
    async def on_ready(self) -> None:
        print("Bot enabled for CG Challenges")
        print("------")
        self.challenge_loop.start()

    async def cog_unload(self):
        self.challenge_loop.cancel()

    @discord.app_commands.command(
        name="challenges-start", description=adminCommands["/challenges-start"]
    )
    @discord.app_commands.check(permissions.is_admin)
    @discord.app_commands.guild_only()
    async def challenges_start(self, interaction: discord.Interaction) -> None:
        _game_channel, created = ChallengeChannel.get_or_create(id=interaction.channel_id)
        assert interaction.channel is not None
        await interaction.response.send_message(
            f"{interaction.channel.name} {'already' if created else ''} enabled for CG Challenges."
        )

    @discord.app_commands.command(
        name="challenges-end", description=adminCommands["/challenges-end"]
    )
    @discord.app_commands.check(permissions.is_admin)
    @discord.app_commands.guild_only()
    async def challenges_end(self, interaction: discord.Interaction) -> None:
        assert interaction.channel is not None
        channels_removed = ChallengeChannel.delete().where(ChallengeChannel.id == interaction.channel_id)
        if channels_removed:
            await interaction.response.send_message(f"{interaction.channel.name} disabled for CG Challenges.")
        else:
            await interaction.response.send_message("This channel is not enabled for CG Challenges.")

    @discord.app_commands.command(
        name="add-challenge", description=adminCommands["/add-challenge"]
    )
    @discord.app_commands.describe(
        game="The name of the game/challenge you want to add to the pool"
    )
    @discord.app_commands.check(permissions.is_admin)
    @discord.app_commands.guild_only()
    async def add_challenge(self, interaction: discord.Interaction, game: str) -> None:
        assert interaction.channel is not None
        Game.insert(name=game).execute()
        game_entries: List[Game] = Game.select()
        string_of_games = ""
        game_entry: Game
        for game_entry in game_entries:
            string_of_games += f"{game_entry.name}\n"
        game_list_embed = discord.Embed(title="Possible Challenges", description=string_of_games)
        await interaction.response.send_message("Challenge added.", embed=game_list_embed, ephemeral=True)


    @tasks.loop(time=challenge_alert_time_start)
    async def challenge_loop(
        self,
    ) -> None:
        today = datetime.datetime.today().date()
        # initial alert day is the first of every other month
        alert_date = datetime.datetime.today().date().replace(day=1)
        # actual start date is the last saturday of the month
        month = calendar.monthcalendar(datetime.datetime.now().year, datetime.datetime.now().month)
        day_of_month = max(month[-1][calendar.SATURDAY], month[-2][calendar.SATURDAY])
        game_date = datetime.datetime.today().date().replace(day=day_of_month)

        # check if this month is an odd month or today is not the scheduled alert or game day
        if today.month % 2 != 0 or not (alert_date == today or game_date == today):
            return
        channel_id = ChallengeChannel.get()
        channel = await self.bot.fetch_channel(channel_id)
        # send a message alerting people about the game
        if alert_date == today:     
            try:
                # pull a random game from the DB, send alert message, and delete game
                unused_game = Game.select().order_by(database.random()).limit(1)[0]
                await channel.send(content=f"This month's Cactus Coin challenge game will be {unused_game['name']}!" +
                                f" Please react with the times you'll be free on {game_date.strftime('%A, %B %d')}."
                                )
                Game.delete().where(Game.id == unused_game['id']).execute()
            except Exception:
                await channel.send(content="Bot couldn't fetch a game to play, pls elp.")
            
        # send a reminder message that the game session is today
        elif game_date == today:
            channel.send(content="Reminder: Today is the challenge day, be in the Discord at the time with the most votes.")