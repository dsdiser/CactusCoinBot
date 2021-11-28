import discord
import config
import sql_client as sql


# Checks admin status for a member for specific admin only functionality.
def is_admin(member: discord.Member):
    roleNames = [role.name for role in member.roles if 'CactusCoinDev' in role.name or 'President' in role.name or 'Vice President' in role.name]
    if roleNames:
        return True
    return False


# Creates a cactus coin role that denotes the amount of coin a member has.
async def create_role(guild: discord.Guild, amount: int):
    # avoid duplicating roles whenever possible
    newRoleName = 'Cactus Coin: ' + str(amount)
    existingRole = [role for role in guild.roles if role.name == newRoleName]
    if existingRole:
        return existingRole[0]
    return await guild.create_role(name=newRoleName, reason='Cactus Coin: New CC amount.', color=discord.Color.dark_gold())


# Verifies the state of a user's role denoting their coin, creates it if it doesn't exist.
async def verify_coin(guild: discord.Guild, member: discord.Member, amount: int = config.getAttribute('defaultCoin')):
    # update coin for member who has cactus coin in database
    db_amount = get_coin(member.id)
    print(db_amount)
    if db_amount:
        amount = db_amount
    else:
        update_coin(member.id, amount)

    roleNames = [role.name for role in member.roles if 'Cactus Coin:' in role.name]
    if not roleNames:
        role = await create_role(guild, amount)
        await member.add_roles(role, reason='Cactus Coin: Role updated for ' + member.name)


# Deletes old role and calls function to update new role displaying coin amount
async def update_roles(guild: discord.Guild, member: discord.Member, amount: int):
    cactusRoles = [role for role in member.roles if 'Cactus Coin:' in role.name]
    if cactusRoles:
        cactusRole = cactusRoles[0]
        await member.remove_roles(cactusRole)
        # if the current user is the only one with the role or there are no users with the role
        if len(cactusRole.members) == 1:
            await cactusRole.delete(reason='CactusCoin: Role no longer in use.')

    role = await create_role(guild, amount)
    await member.add_roles(role, reason='Cactus Coin: Role updated for ' + member.name)


# Adds a specified coin amount to a member's role and stores in the database
async def add_coin(guild: discord.Guild, member: discord.Member, amount: int):
    memberId = member.id
    current_coin = get_coin(memberId)
    current_coin += amount
    await update_roles(guild, member, current_coin)


#############################################################
# SQL functions for updating
def update_coin(memberid: str, amount: int):
    cur = sql.connection.cursor()
    cur.execute("INSERT INTO AMOUNTS(id, coin) VALUES ('{0}', {1}) ON CONFLICT(id) DO UPDATE SET coin=excluded.coin".format(memberid, amount))
    sql.connection.commit()
    return amount


def get_coin(memberid: str):
    cur = sql.connection.cursor()
    amount = cur.execute("SELECT coin from AMOUNTS WHERE id IS '{0}'".format(memberid)).fetchall()
    print(memberid, 'current amount:', amount)
    if amount:
        return amount[0][0]
    return None
