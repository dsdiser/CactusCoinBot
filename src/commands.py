from random import randint
import discord
import config
import sql_client as sql
import logging
from io import BytesIO
from PIL import Image, ImageDraw
import os
from typing import List
import matplotlib.pyplot as plt
from matplotlib.offsetbox import OffsetImage, AnnotationBbox
import datetime
import cv2
import numpy as np

if not os.path.exists('../tmp'):
    os.makedirs('../tmp')

# Matplotlib styling
plt.style.use('dark_background')
for param in ['text.color', 'axes.labelcolor', 'xtick.color', 'ytick.color']:
    plt.rcParams[param] = '0.9'  # very light grey
for param in ['figure.facecolor', 'axes.facecolor', 'savefig.facecolor']:
    plt.rcParams[param] = '#212946'  # bluish dark grey
plt.rcParams['font.family'] = 'Tahoma'
plt.rcParams['font.size'] = 16

icon_size = (44, 44)
icon_mask = Image.new('L', (128, 128))
mask_draw = ImageDraw.Draw(icon_mask)
mask_draw.ellipse((0, 0, 128, 128), fill=255)


# Checks admin status for a member for specific admin only functionality.
def is_admin(member: discord.Member):
    roleNames = [role.name for role in member.roles if 'CactusCoinDev' in role.name or 'President' in role.name or 'Vice President' in role.name]
    if roleNames:
        return True
    return False


def is_dev(member: discord.Member):
    roleNames = [role.name for role in member.roles if 'CactusCoinDev' in role.name]
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


# Removes the cactus coin role from the member's role and from the guild if necessary
async def remove_role(guild: discord.Guild, member: discord.Member):
    cactusRoles = [role for role in member.roles if 'Cactus Coin:' in role.name]
    if cactusRoles:
        cactusRole = cactusRoles[0]
        await member.remove_roles(cactusRole)
        # if the current user is the only one with the role or there are no users with the role
        await clear_old_roles(guild)


# Verifies the state of a user's role denoting their coin, creates it if it doesn't exist.
async def verify_coin(guild: discord.Guild, member: discord.Member, amount: int = config.getAttribute('defaultCoin')):
    # update coin for member who has cactus coin in database
    db_amount = get_coin(member.id)
    if db_amount:
        amount = db_amount
        logging.debug('Found coin for ' + member.display_name + ': ' + str(db_amount))
    else:
        logging.debug('No coin found for ' + member.display_name + ', defaulting to: ' + str(amount))
        update_coin(member.id, amount)

    roleNames = [role.name for role in member.roles if 'Cactus Coin:' in role.name]
    if not roleNames:
        role = await create_role(guild, amount)
        await member.add_roles(role, reason='Cactus Coin: Role updated for ' + member.name + ' to ' + str(amount))


# Deletes all old cactus coin roles
async def clear_old_roles(guild: discord.Guild):
    emptyRoles = [role for role in guild.roles if 'Cactus Coin:' in role.name and len(role.members) == 0]
    for role in emptyRoles:
        await role.delete(reason='Cactus Coin: Removing unused role.')


# Deletes old role and calls function to update new role displaying coin amount
async def update_role(guild: discord.Guild, member: discord.Member, amount: int):
    await remove_role(guild, member)
    role = await create_role(guild, amount)
    await member.add_roles(role, reason='Cactus Coin: Role updated for ' + member.name + ' to ' + str(amount))


# Adds a specified coin amount to a member's role and stores in the database
async def add_coin(guild: discord.Guild, member: discord.Member, amount: int):
    memberId = member.id
    current_coin = get_coin(memberId)
    current_coin += amount
    update_coin(memberId, current_coin)
    await update_role(guild, member, current_coin)


# Computes power rankings for the server and outputs them in a bar graph in an image
async def compute_rankings(guild: discord.Guild):
    # get all coin amounts
    rankings = get_coin_rankings()
    # pull all images of ranking members from discord
    memberIcons = []
    memberNames = []
    memberAmounts = []
    memberColor = []
    storedIcons = os.listdir('../tmp')
    for memberid, amount in rankings:
        member = guild.get_member(memberid)
        if not member:
            return
        icon = member.display_avatar
        # check if we already have the file in tmp folder
        if f'{icon.key}-44px.png' not in storedIcons:
            img = Image.open(BytesIO(await icon.read()))
            img = img.resize((128, 128))
            img.save(f'../tmp/{icon.key}.png')
            img.putalpha(icon_mask)
            img = img.resize(icon_size)
            img.save(f'../tmp/{icon.key}-44px.png')
            img.close()

        memberIcons.append(f'../tmp/{icon.key}-44px.png')
        memberNames.append(member.display_name)
        memberAmounts.append(amount)
        # alternate bar color generation
        # im = img.resize((1, 1), Image.NEAREST).convert('RGB')
        # color = im.getpixel((0, 0))
        # normalize pixel values between 0 and 1
        memberC = member.color if member.color != discord.Color.default() or member.color != discord.Color.from_rgb(1, 1, 1) else discord.Color.blurple()
        color = (memberC.r, memberC.g, memberC.b)
        memberColor.append(tuple(t/255. for t in color))
    ax = plt.axes()
    ax.set_axisbelow(True)
    ax.yaxis.grid(color='.9', linestyle='dashed')
    ax.xaxis.grid(color='.9', linestyle='dashed')
    # plot chart
    height = .8
    plt.barh(memberNames, memberAmounts, height=height, color=memberColor)

    # create a glowy effect on the plot by plotting different bars
    n_shades = 5
    diff_linewidth = .05
    alpha_value = 0.5 / n_shades
    for n in range(1, n_shades + 1):
        plt.barh(memberNames, memberAmounts,
                height=(height + (diff_linewidth * n)),
                alpha=alpha_value,
                color=memberColor)

    today = datetime.date.today().strftime("%m-%d-%Y")
    plt.title('Cactus Gang Power Rankings\n' + today, fontweight='bold')
    plt.xlabel('Coin (¢)')

    # add user icons to bar charts
    max_value = max(memberAmounts)
    for i, (value, icon) in enumerate(zip(memberAmounts, memberIcons)):
        offset_image(value, i, icon, max_value=max_value, ax=ax)
    plt.savefig(f'../tmp/power-rankings-{today}.png', bbox_inches='tight', pad_inches=.5)
    plt.close()


# Adds discord icons to bar chart
def offset_image(x, y, icon, max_value, ax):
    img = plt.imread(icon)
    im = OffsetImage(img, zoom=0.65)
    im.image.axes = ax
    x_offset = -25
    # if bar is too short to show icon
    if 0 <= x < max_value / 5:
        x = x + max_value // 8
    elif x < max_value / 5:
        x = 0
    ab = AnnotationBbox(im, (x, y), xybox=(x_offset, 0), frameon=False,
                        xycoords='data', boxcoords="offset points", pad=0)
    ax.add_artist(ab)


# Generate wheel for bet as a gif
def generate_wheel(members: List[discord.Member]):
    canvas_size = 1000
    wheel_offset = 5
    bounding_box = [(wheel_offset, wheel_offset), (canvas_size - wheel_offset, canvas_size - wheel_offset)]
    sliceDegree = 360 / len(members)
    currSlice = 0
    wheelPath = '../tmp/wheel.png'
    wheel = Image.new('RGBA', (canvas_size, canvas_size), '#DDD')
    for member in members:
        wheelDraw = ImageDraw.Draw(wheel)
        wheelDraw.pieslice(bounding_box, start=currSlice, end=currSlice+sliceDegree, fill=member['color'], width=5, outline='black')
        currSlice += sliceDegree
    
    rotations = randint(50, 100)
    degree_rotate = 10
    total_rotate = 10
    wheelImgs = [wheel]
    acceleration = -.05
    for i in range(rotations):
        wheelImgs.append(wheel.rotate(total_rotate, expand=False, fillcolor='#DDD'))
        if i < 20:
            total_rotate += degree_rotate
            degree_rotate += 1
        else:
            total_rotate += degree_rotate
            degree_rotate = max(0, degree_rotate - i*acceleration)

    # GIF method 
    wheel.save('../tmp/out.gif', save_all=True, append_images=wheelImgs[1:])
    # Video method
    vid = cv2.VideoWriter('../tmp/outpy.mp4', 0x7634706d, 10, (canvas_size, canvas_size))
    for img in wheelImgs:
        img = cv2.cvtColor(np.array(img), cv2.COLOR_RGB2BGR)
        vid.write(img)

    vid.release()
    
    return wheelPath
    
    # Iterate through members and make slices for each member, concat them all together, then spin


#############################################################
# SQL functions for updating
def update_coin(memberid: int, amount: int):
    logging.debug('Updating coin for: ' + str(memberid) + ': ' + str(amount))
    cur = sql.connection.cursor()
    cur.execute("INSERT INTO AMOUNTS(id, coin) VALUES ('{0}', {1}) ON CONFLICT(id) DO UPDATE SET coin=excluded.coin".format(memberid, amount))
    sql.connection.commit()
    return amount


def get_coin(memberid: int):
    cur = sql.connection.cursor()
    amount = cur.execute("SELECT coin from AMOUNTS WHERE id IS '{0}'".format(memberid)).fetchall()
    if amount:
        return amount[0][0]
    return None


def remove_coin(memberid: int):
    cur = sql.connection.cursor()
    cur.execute("DELETE FROM AMOUNTS WHERE id is '{0}'".format(memberid))
    sql.connection.commit()


def get_coin_rankings():
    cur = sql.connection.cursor()
    amounts = cur.execute("SELECT id, coin from AMOUNTS ORDER BY coin").fetchall()
    if amounts:
        return amounts
    return None
