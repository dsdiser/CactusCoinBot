import discord


def is_dev(interaction: discord.Interaction) -> bool:
    member = interaction.user
    role_names = [role.name for role in member.roles if 'CactusCoinDev' in role.name]
    return bool(role_names)


def is_admin(interaction: discord.Interaction) -> bool:
    """Checks admin status for a member for specific admin only functionality."""
    member = interaction.user
    role_names = [role.name for role in member.roles if
                 'CactusCoinDev' in role.name or 'President' in role.name or 'Vice President' in role.name]
    return bool(role_names)
