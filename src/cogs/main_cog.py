import discord
from discord.ext import commands

from src import bot_helper, config, permissions, sql_client

userCommands = {
    "/help": "Outputs a list of commands.",
    "/setup": "Sets up the user's Cactus Coin role.",
    "/balance": "Displays a user's coin balance.",
    "/rankings": "Outputs power rankings for the server.",
    "/give": "Gives coin to a specific user, no strings attached.",
}

adminCommands = {
    "/admin-help": "!ADMIN ONLY! Outputs a list of admin-specific commands.",
    "/admin-adjust": "!ADMIN ONLY! Adds/subtracts coin from user's wallet.",
    "/clear": "!ADMIN ONLY! Clears a user's wallet of all coin and removes coin role.",
    "/reset": "!ADMIN ONLY! Resets a user's wallet to the default starting amount",
    "/soft-reset": "!ADMIN ONLY! Resets all users's wallets to the default starting amount",
    "/full-clear": "!DEV ONLY! Clears all users's coins and clears all roles",
}


def add_bet_to_embed(embed: discord.Embed, bet, show_id=True):
    bet_id, _date, author, opponent, amount, reason, _active = bet
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

    """
    ADMIN COMMANDS
    """

    @discord.app_commands.command(
        name="admin-help", description=adminCommands["/admin-help"]
    )
    @discord.app_commands.check(permissions.is_admin)
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
    @discord.app_commands.check(permissions.is_admin)
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

    @discord.app_commands.command(name="clear", description=adminCommands["/clear"])
    @discord.app_commands.describe(user="The user to clear coin for")
    @discord.app_commands.check(permissions.is_admin)
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
    @discord.app_commands.check(permissions.is_admin)
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
    @discord.app_commands.check(permissions.is_admin)
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
    @discord.app_commands.check(permissions.is_dev)
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
    @clear.error
    @reset.error
    @soft_reset.error
    @full_clear.error
    async def permissions_error(self, interaction: discord.Interaction, error):
        if isinstance(error, discord.app_commands.errors.CheckFailure):
            await interaction.response.send_message(
                "You do not have permissions to use that command.", ephemeral=True
            )
