import datetime

import discord
from discord import NotFound
from discord.ext import commands, tasks
from typing import Literal, Optional

import bot_helper
import config
import sql_client
import views
import openai
from trivia_handler import Question, get_trivia_questions, Difficulty
from pytz import timezone

TIME_PERIOD = Literal["week", "month", "year"]

userCommands = {
    "/help": "Outputs a list of commands.",
    "/setup": "Sets up the user's Cactus Coin role.",
    "/balance": "Displays a user's coin balance.",
    "/rankings": "Outputs power rankings for the server.",
    "/give": "Gives coin to a specific user, no strings attached.",
    "/bet": "Starts a bet with another member.",
    "/end-bet": "Ends an existing bet with another member.",
    "/cancel-bet": "Cancels an existing bet with another member.",
    "/list-bets": "Lists all the active bets",
    "/my-bets": "Lists all your active bets",
    "/imagine": "Generates an image based off a prompt",
}

adminCommands = {
    "/admin-help": "!ADMIN ONLY! Outputs a list of admin-specific commands.",
    "/admin-adjust": "!ADMIN ONLY! Adds/subtracts coin from user's wallet.",
    "/clear": "!ADMIN ONLY! Clears a user's wallet of all coin and removes coin role.",
    "/big-wins": "!ADMIN ONLY! Outputs the greatest gains in the specified time period.",
    "/reset": "!ADMIN ONLY! Resets a user's wallet to the default starting amount",
    "/soft-reset": "!ADMIN ONLY! Resets all users's wallets to the default starting amount",
    "/full-clear": "!DEV ONLY! Clears all users's coins and clears all roles",
    "/trivia-start": "!ADMIN ONLY! Enables the current channel for trivia questions",
    "/trivia-end": "!ADMIN ONLY! Disables the current channel for trivia questions",
    "/trivia-populate": "!ADMIN ONLY! Repopulates the trivia bank",
    "/trivia-reward": "!ADMIN ONLY! Updates the trivia reward for a successful answer, applies to the next question",
    "/trivia-reset": "!ADMIN ONLY! Resets today's trivia question and sends a new one.",
    "/trivia-submit": "!ADMIN ONLY! Provides input for submitting a custom question.",
    "/trivia-time": "!ADMIN ONLY! Outputs the scheduled time for trivia questions.",
}


def add_bet_to_embed(embed: discord.Embed, bet, show_id=True):
    bet_id, date, author, opponent, amount, reason, active = bet
    title = f"ID: {bet_id}" if show_id else "Bet"
    description = (
        f"<@{author}> vs <@{opponent}>\n"
        f'Wager: {format(amount, ",d")} coin\n'
        f"Reason: {reason}\n"
    )
    embed.add_field(name=title, value=description)


class BotCog(commands.Cog):
    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot

    @commands.Cog.listener()
    async def on_ready(self) -> None:
        print(f"Logged in as {self.bot.user} (ID: {self.bot.user.id})")
        print("------")

    @commands.Cog.listener()
    async def on_message(self, message: discord.Message) -> None:
        """
        Syncs slash commands to discord server
        :param message:
        """
        if message.content == "pls sync":
            self.bot.tree.copy_global_to(guild=message.guild)
            await self.bot.tree.sync(guild=message.guild)
            await message.reply("Synced commands.")

    """
    USER COMMANDS
    """

    @discord.app_commands.command(name="help", description=userCommands["/help"])
    @discord.app_commands.guild_only()
    async def help(self, interaction: discord.Interaction) -> None:
        embed = discord.Embed(
            title="Cactus Coin Bot Commands", color=discord.Color.dark_green()
        )
        for idx, key in enumerate(userCommands.keys()):
            embed.add_field(name=key, value=userCommands[key], inline=True)
            # column override for proper formatting in Discord
            if idx % 2 == 1:
                embed.add_field(name="\u200b", value="\u200b", inline=True)
        await interaction.response.send_message(embed=embed, ephemeral=True)

    @discord.app_commands.command(name="setup", description=userCommands["/setup"])
    @discord.app_commands.describe(user="The user to set up Cactus Coin for")
    @discord.app_commands.guild_only()
    async def setup(
        self, interaction: discord.Interaction, user: discord.Member
    ) -> None:
        await bot_helper.verify_coin(interaction.guild, user)
        await interaction.response.send_message(
            f"Verified coin for: {user.display_name}", ephemeral=True
        )

    @discord.app_commands.command(name="balance", description=userCommands["/balance"])
    @discord.app_commands.describe(user="The user to see the amount of coin amount for")
    @discord.app_commands.guild_only()
    async def balance(
        self, interaction: discord.Interaction, user: discord.Member
    ) -> None:
        balance = sql_client.get_coin(user.id)
        if balance:
            await interaction.response.send_message(
                f"{user.display_name}'s balance: {str(balance)}.", ephemeral=True
            )
        else:
            await interaction.response.send_message(
                f"{user.display_name}'s has no balance.", ephemeral=True
            )

    @discord.app_commands.command(
        name="rankings", description=userCommands["/rankings"]
    )
    @discord.app_commands.guild_only()
    async def rankings(self, interaction: discord.Interaction) -> None:
        await interaction.response.defer(ephemeral=False, thinking=True)
        file_path = await bot_helper.compute_rankings(interaction.guild)
        file = discord.File(file_path)
        await interaction.followup.send(
            "Here are the current power rankings:", file=file
        )
        bot_helper.remove_file(file_path)

    @discord.app_commands.command(name="give", description=userCommands["/give"])
    @discord.app_commands.describe(user="The user to give Cactus Coin to")
    @discord.app_commands.describe(amount="The amount of Cactus Coin to give")
    @discord.app_commands.guild_only()
    async def give(
        self, interaction: discord.Interaction, user: discord.Member, amount: int
    ) -> None:
        author_coin = sql_client.get_coin(interaction.user.id)
        if author_coin - amount < config.get_attribute("debtLimit"):
            await interaction.response.send_message(
                f'You don\'t have this much coin to give {config.get_attribute("sadEmote", "")}',
                ephemeral=True,
            )
        elif user.id == interaction.user.id:
            await interaction.response.send_message(
                "Are you stupid or something?", ephemeral=True
            )
        elif amount > 0:
            await bot_helper.add_coin(interaction.guild, user, amount)
            await bot_helper.add_coin(interaction.guild, interaction.user, -amount)
            await interaction.response.send_message(
                f'{format(amount, ",d")} coin sent to {user.mention}'
            )
        elif amount < 0:
            await interaction.response.send_message(
                "Nice try <:shanechamp:910353567603384340>", ephemeral=True
            )

    @discord.app_commands.command(name="bet", description=userCommands["/bet"])
    @discord.app_commands.describe(user="The user to bet Cactus Coin against")
    @discord.app_commands.describe(amount="The amount of Cactus Coin to bet")
    @discord.app_commands.describe(reason="Short description of what the bet is for")
    @discord.app_commands.guild_only()
    async def bet_start(
        self,
        interaction: discord.Interaction,
        user: discord.Member,
        amount: int,
        reason: str,
    ) -> None:
        author_coin = sql_client.get_coin(interaction.user.id)
        opponent_coin = sql_client.get_coin(user.id)
        if author_coin - amount < config.get_attribute("debtLimit"):
            await interaction.response.send_message(
                f'You don\'t have this much coin to bet {config.get_attribute("sadEmote", "")}',
                ephemeral=True,
            )
        elif opponent_coin - amount < config.get_attribute("debtLimit"):
            await interaction.response.send_message(
                f'{user.mention} doesn\'t have this much coin to bet {config.get_attribute("sadEmote", "")}',
                ephemeral=True,
            )
        elif user.id == interaction.user.id:
            await interaction.response.send_message(
                "You can't bet against yourself silly", ephemeral=True
            )
        elif amount > 0:
            # use view to start interaction and get both users to accept the bet
            view = views.ConfirmBet(user.id)
            embed = discord.Embed(title="", color=discord.Color.dark_blue())
            bet_entry = ("", None, interaction.user.id, user.id, amount, reason, None)
            add_bet_to_embed(embed, bet_entry, show_id=False)
            await interaction.response.send_message(
                f"{user.mention}, {interaction.user.mention} challenged you to the following bet, do you accept?",
                embed=embed,
                view=view,
            )
            await view.wait()
            # Deal with view response
            if view.value is None:
                # view expired
                original_message = await interaction.original_response()
                await original_message.edit(
                    content=f"{user.mention} didn't respond to the following bet from {interaction.user.mention}.",
                    embed=embed,
                    view=None,
                )
            elif not view.value:
                # user declines
                await interaction.edit_original_response(
                    content=f"{user.mention} declined the following bet.",
                    embed=embed,
                    view=None,
                )
            else:
                # bet has gone through, start bet instance
                bet_id = bot_helper.start_bet(interaction.user, user, amount, reason)
                embed = discord.Embed(title="", color=discord.Color.dark_blue())
                bet_entry = (
                    bet_id,
                    None,
                    interaction.user.id,
                    user.id,
                    amount,
                    reason,
                    None,
                )
                add_bet_to_embed(embed, bet_entry, show_id=True)
                await bot_helper.add_coin(interaction.guild, interaction.user, -amount)
                await bot_helper.add_coin(interaction.guild, user, -amount)
                await interaction.edit_original_response(
                    content=f"{user.mention} accepted the following bet against {interaction.user.mention}",
                    embed=embed,
                    view=None,
                )
        elif amount <= 0:
            await interaction.response.send_message(
                "You can't do negative or zero bets", ephemeral=True
            )

    @discord.app_commands.command(name="end-bet", description=userCommands["/end-bet"])
    @discord.app_commands.describe(
        bet_id="The 4-letter bet ID associated with your bet"
    )
    @discord.app_commands.describe(winner="The user who won the bet")
    @discord.app_commands.guild_only()
    async def bet_end(
        self, interaction: discord.Interaction, bet_id: str, winner: discord.Member
    ) -> None:
        bet_id = bet_id.upper()
        original_bet = sql_client.fetch_bet(bet_id)
        if not original_bet:
            await interaction.response.send_message(
                "A bet with this ID does not exist.", ephemeral=True
            )
        else:
            (bet_id, date, author, opponent, amount, reason, active) = original_bet
            # Verify interaction user is one of the active betters
            if interaction.user.id != author and interaction.user.id != opponent:
                await interaction.response.send_message(
                    "You are not one of the parties in this bet.", ephemeral=True
                )
            elif winner.id != author and winner.id != opponent:
                await interaction.response.send_message(
                    f"{winner.mention} is not one of the parties in this bet.",
                    ephemeral=True,
                )
            else:
                other_user_id = author if interaction.user.id == opponent else opponent
                other_user = interaction.guild.get_member(other_user_id)
                loser = (
                    interaction.user if interaction.user.id != winner.id else other_user
                )
                embed = discord.Embed(title="", color=discord.Color.green())
                add_bet_to_embed(embed, original_bet)
                # if the user is the loser, we can assume they're telling the truth. Otherwise we must confirm
                if interaction.user != loser:
                    view = views.ConfirmBet(other_user.id)
                    await interaction.response.send_message(
                        f"{winner.mention} believes they won the below bet. "
                        f"{other_user.mention}, do you accept this result?",
                        embed=embed,
                        view=view,
                    )
                    await view.wait()
                    # Deal with view response
                    if view.value is None:
                        # view expired
                        await interaction.delete_original_response()
                    elif not view.value:
                        # user declines
                        await interaction.edit_original_response(
                            content=f"{other_user.mention} declined that {winner.mention} won the below bet."
                            f"Figure it out yourselves...",
                            embed=embed,
                            view=None,
                        )
                    else:
                        # bet is completed, end bet
                        sql_client.remove_bet(bet_id)
                        await bot_helper.add_coin(interaction.guild, winner, 2 * amount)
                        await interaction.edit_original_response(
                            content=f'{winner.mention} won the below bet and gained {format(amount, ",d")} coin!',
                            embed=embed,
                            view=None,
                        )
                else:
                    sql_client.remove_bet(bet_id)
                    await bot_helper.add_coin(interaction.guild, winner, 2 * amount)
                    await interaction.response.send_message(
                        f"{winner.mention} won the below bet and "
                        f'gained their original bet + {format(amount, ",d")} coin!',
                        embed=embed,
                    )

    @discord.app_commands.command(
        name="cancel-bet", description=userCommands["/cancel-bet"]
    )
    @discord.app_commands.describe(
        bet_id="The 4-letter bet ID associated with your bet"
    )
    @discord.app_commands.guild_only()
    async def bet_cancel(self, interaction: discord.Interaction, bet_id: str) -> None:
        bet_id = bet_id.upper()
        original_bet = sql_client.fetch_bet(bet_id)
        if not original_bet:
            await interaction.response.send_message(
                "A bet with this ID does not exist.", ephemeral=True
            )
        else:
            (bet_id, date, author, opponent, amount, reason, active) = original_bet
            # Verify interaction user is one of the active betters
            if interaction.user.id != author and interaction.user.id != opponent:
                await interaction.response.send_message(
                    "You are not one of the parties in this bet.", ephemeral=True
                )
            else:
                other_user_id = author if interaction.user.id == opponent else opponent
                other_user = interaction.guild.get_member(other_user_id)
                view = views.ConfirmBet(other_user_id)
                embed = discord.Embed(title="", color=discord.Color.dark_red())
                add_bet_to_embed(embed, original_bet, show_id=False)
                await interaction.response.send_message(
                    f"{other_user.mention}, {interaction.user.mention} wants to cancel the following bet. "
                    f"Do you accept?",
                    embed=embed,
                    view=view,
                )
                await view.wait()
                # Deal with view response
                if view.value is None:
                    # view expired
                    await interaction.delete_original_response()
                elif not view.value:
                    # user declines
                    await interaction.edit_original_response(
                        content=f"{other_user.mention} declined {interaction.user.mention}'s offer to cancel the "
                        f"following bet.",
                        embed=embed,
                        view=None,
                    )
                else:
                    # bet cancel has gone through, give coin back to each user
                    sql_client.remove_bet(bet_id)
                    await bot_helper.add_coin(
                        interaction.guild, interaction.user, amount
                    )
                    await bot_helper.add_coin(interaction.guild, other_user, amount)
                    await interaction.edit_original_response(
                        content="The following bet has been cancelled:",
                        embed=embed,
                        view=None,
                    )

    @discord.app_commands.command(
        name="list-bets", description=userCommands["/list-bets"]
    )
    @discord.app_commands.guild_only()
    async def list_bets(self, interaction: discord.Interaction) -> None:
        bets = sql_client.get_active_bets()
        if not bets:
            await interaction.response.send_message("There are no active bets.")
        else:
            embed = discord.Embed(title="Active Bets", color=discord.Color.dark_green())
            for idx, bet in enumerate(bets):
                add_bet_to_embed(embed, bet)
                # column override for proper formatting in Discord
                if idx % 2 == 1:
                    embed.add_field(name="\u200b", value="\u200b", inline=True)
            await interaction.response.send_message("", embed=embed)

    @discord.app_commands.command(name="my-bets", description=userCommands["/my-bets"])
    @discord.app_commands.guild_only()
    async def my_bets(self, interaction: discord.Interaction) -> None:
        bets = sql_client.get_user_bets(interaction.user.id)
        if not bets:
            await interaction.response.send_message("You have no active bets.")
        else:
            embed = discord.Embed(title="Your Bets", color=discord.Color.dark_green())
            for idx, bet in enumerate(bets):
                add_bet_to_embed(embed, bet)
                # column override for proper formatting in Discord
                if idx % 2 == 1:
                    embed.add_field(name="\u200b", value="\u200b", inline=True)
            await interaction.response.send_message("", embed=embed, ephemeral=True)

    """
    ADMIN COMMANDS
    """

    @discord.app_commands.command(
        name="admin-help", description=adminCommands["/admin-help"]
    )
    @discord.app_commands.check(bot_helper.is_admin)
    @discord.app_commands.guild_only()
    async def admin_help(self, interaction: discord.Interaction) -> None:
        embed = discord.Embed(
            title="Cactus Coin Bot Commands", color=discord.Color.dark_green()
        )
        for idx, key in enumerate(userCommands.keys()):
            embed.add_field(name=key, value=userCommands[key], inline=True)
            if idx % 2 == 1:
                embed.add_field(name="\u200b", value="\u200b", inline=True)
        await interaction.response.send_message(embed=embed, ephemeral=True)

    @discord.app_commands.command(
        name="admin-adjust", description=adminCommands["/admin-adjust"]
    )
    @discord.app_commands.describe(user="The user to give Cactus Coin to")
    @discord.app_commands.describe(amount="The amount of Cactus Coin to give")
    @discord.app_commands.describe(
        persist="Whether the transaction should go on the record"
    )
    @discord.app_commands.check(bot_helper.is_admin)
    @discord.app_commands.guild_only()
    async def admin_adjust(
        self,
        interaction: discord.Interaction,
        user: discord.Member,
        amount: int,
        persist: bool,
    ) -> None:
        await bot_helper.add_coin(interaction.guild, user, amount, persist=persist)
        await interaction.response.send_message(
            f'Added {format(amount, ",d")} to {user.display_name}', ephemeral=True
        )

    @discord.app_commands.command(
        name="big-wins", description=adminCommands["/big-wins"]
    )
    @discord.app_commands.describe(period="The period over which to look at")
    @discord.app_commands.check(bot_helper.is_admin)
    @discord.app_commands.guild_only()
    async def big_wins(
        self, interaction: discord.Interaction, period: TIME_PERIOD
    ) -> None:
        filePath = await bot_helper.get_movements(interaction.guild, period, True)
        if filePath:
            file = discord.File(filePath)
            await interaction.response.send_message(
                f"Here are the this {period}'s biggest winners:", file=file
            )
        else:
            await interaction.response.send_message(
                f"There are no winners for this {period}."
            )

    @discord.app_commands.command(name="clear", description=adminCommands["/clear"])
    @discord.app_commands.describe(user="The user to clear coin for")
    @discord.app_commands.check(bot_helper.is_admin)
    @discord.app_commands.guild_only()
    async def clear(
        self, interaction: discord.Interaction, user: discord.Member
    ) -> None:
        sql_client.remove_coin(user.id)
        await bot_helper.remove_role(interaction.guild, user)
        await interaction.response.send_message(
            f"{user.display_name}'s coin has been cleared.", ephemeral=True
        )

    @discord.app_commands.command(name="reset", description=adminCommands["/reset"])
    @discord.app_commands.describe(user="The user to reset the coin for")
    @discord.app_commands.check(bot_helper.is_admin)
    @discord.app_commands.guild_only()
    async def reset(
        self, interaction: discord.Interaction, user: discord.Member
    ) -> None:
        amount = sql_client.get_coin(user.id)
        await bot_helper.add_coin(
            interaction.guild,
            user,
            -(amount - config.get_attribute("defaultCoin")),
            persist=False,
        )
        await bot_helper.update_role(
            interaction.guild, user, config.get_attribute("defaultCoin")
        )

    @discord.app_commands.command(
        name="soft-reset", description=adminCommands["/soft-reset"]
    )
    @discord.app_commands.check(bot_helper.is_admin)
    @discord.app_commands.guild_only()
    async def soft_reset(self, interaction: discord.Interaction) -> None:
        # BE CAREFUL WITH THIS IT WILL CLEAR OUT ALL COIN
        output = ""
        for member in interaction.guild.members:
            amount = sql_client.get_coin(member.id)
            await bot_helper.add_coin(
                interaction.guild,
                member,
                -(amount - config.get_attribute("defaultCoin")),
                persist=False,
            )
            await bot_helper.update_role(
                interaction.guild, member, config.get_attribute("defaultCoin")
            )
        await interaction.response.send_message(
            f'Everyone\'s coin reset back to {config.get_attribute("defaultCoin")}...here\'s the short history just in '
            f"case.\n{output}"
        )

    @discord.app_commands.command(
        name="full-clear", description=adminCommands["/full-clear"]
    )
    @discord.app_commands.check(bot_helper.is_dev)
    @discord.app_commands.guild_only()
    async def full_clear(self, interaction: discord.Interaction) -> None:
        # BE CAREFUL WITH THIS IT WILL CLEAR OUT ALL COIN
        output = ""
        for member in interaction.guild.members:
            coin = sql_client.get_coin(member.id)
            sql_client.remove_coin(member.id)
            sql_client.remove_transactions(member.id)
            await bot_helper.remove_role(interaction.guild, member)
            output += f"{member.display_name} - {str(coin)}\n"
        await interaction.response.send_message(
            "Everything cleared out...here's the short history just in case.\n" + output
        )

    @admin_help.error
    @admin_adjust.error
    @balance.error
    @big_wins.error
    @clear.error
    @reset.error
    @soft_reset.error
    @full_clear.error
    @imagine.error
    async def permissions_error(self, interaction: discord.Interaction, error):
        if isinstance(error, discord.app_commands.errors.CheckFailure):
            await interaction.response.send_message(
                "You do not have permissions to use that command.", ephemeral=True
            )


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
        print(f"Bot logged in and enabled for Trivia")
        print("------")
        self.populate_question_list()
        self.trivia_loop.start()

    def cog_unload(self):
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
    @discord.app_commands.check(bot_helper.is_admin)
    @discord.app_commands.guild_only()
    async def trivia_time(self, interaction: discord.Interaction) -> None:
        await interaction.response.send_message(
            f'Trivia time is {trivia_time_start.strftime("%H:%M:%S")}.', ephemeral=True
        )

    @discord.app_commands.command(
        name="trivia-start", description=adminCommands["/trivia-start"]
    )
    @discord.app_commands.check(bot_helper.is_admin)
    @discord.app_commands.guild_only()
    async def trivia_start(self, interaction: discord.Interaction) -> None:
        sql_client.add_channel(interaction.channel_id)
        await interaction.response.send_message(
            f"{interaction.channel.name} enabled for trivia questions."
        )

    @discord.app_commands.command(
        name="trivia-end", description=adminCommands["/trivia-end"]
    )
    @discord.app_commands.check(bot_helper.is_admin)
    @discord.app_commands.guild_only()
    async def trivia_end(self, interaction: discord.Interaction) -> None:
        sql_client.remove_channel(interaction.channel_id)
        await interaction.response.send_message(
            f"{interaction.channel.name} disabled for trivia questions."
        )

    @discord.app_commands.command(
        name="trivia-populate", description=adminCommands["/trivia-populate"]
    )
    @discord.app_commands.check(bot_helper.is_admin)
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
    @discord.app_commands.check(bot_helper.is_admin)
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
    @discord.app_commands.check(bot_helper.is_admin)
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
    @discord.app_commands.check(bot_helper.is_admin)
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


async def setup(bot: commands.Bot):
    await bot.add_cog(BotCog(bot))
    await bot.add_cog(TriviaCog(bot))
