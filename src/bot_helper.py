import discord
import config
import logging
from io import BytesIO
from PIL import Image, ImageDraw
import os
from typing import List
import matplotlib.pyplot as plt
from matplotlib.offsetbox import OffsetImage, AnnotationBbox
from datetime import datetime, date, timedelta
from math import exp, cos, sin, radians
import random
from pytz import timezone

from id_generator import random_id
from sql_client import get_coin, add_transaction, add_bet, get_coin_rankings, get_transactions, update_coin, fetch_bet

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


def is_admin(interaction: discord.Interaction):
    """Checks admin status for a member for specific admin only functionality."""
    member = interaction.user
    roleNames = [role.name for role in member.roles if
                 'CactusCoinDev' in role.name or 'President' in role.name or 'Vice President' in role.name]
    if roleNames:
        return True
    return False


def is_dev(interaction: discord.Interaction):
    member = interaction.user
    role_names = [role.name for role in member.roles if 'CactusCoinDev' in role.name]
    if role_names:
        return True
    return False


async def create_role(guild: discord.Guild, amount: int):
    """Creates a cactus coin role that denotes the amount of coin a member has."""
    # avoid duplicating roles whenever possible
    prefix = config.get_attribute('rolePrefix', 'Cactus Coin: ')
    new_role_name = f'{prefix}{format(amount, ",d")}'
    existing_role = [role for role in guild.roles if role.name == new_role_name]
    if existing_role:
        return existing_role[0]
    return await guild.create_role(name=new_role_name, reason='Cactus Coin: New CC amount.',
                                   color=discord.Color.dark_gold())


async def remove_role(guild: discord.Guild, member: discord.Member):
    """ Removes the cactus coin role from the member's role and from the guild if necessary """
    prefix = config.get_attribute('rolePrefix', 'Cactus Coin')
    cactus_roles = [role for role in member.roles if prefix in role.name]
    if cactus_roles:
        cactus_role = cactus_roles[0]
        await member.remove_roles(cactus_role)
        # if the current user is the only one with the role or there are no users with the role
        await clear_old_roles(guild)


async def verify_coin(guild: discord.Guild, member: discord.Member, amount: int = config.get_attribute('defaultCoin')):
    """ Verifies the state of a user's role denoting their coin, creates it if it doesn't exist. """
    # update coin for member who has cactus coin in database
    db_amount = get_coin(member.id)
    prefix = config.get_attribute('rolePrefix', 'Cactus Coin')
    if db_amount:
        amount = db_amount
        logging.debug(f'Found coin for {member.display_name}: {str(db_amount)}')
    else:
        logging.debug(f'No coin found for {member.display_name}, defaulting to: {str(amount)}')
        update_coin(member.id, amount)

    roleNames = [role.name for role in member.roles if prefix in role.name]
    if not roleNames:
        role = await create_role(guild, amount)
        await member.add_roles(role, reason=f'Cactus Coin: Role updated for {member.name} to {str(amount)}')


async def clear_old_roles(guild: discord.Guild):
    """
    Deletes all old cactus coin roles
    :param guild:
    :return:
    """
    emptyRoles = [role for role in guild.roles if 'Cactus Coin:' in role.name and len(role.members) == 0]
    for role in emptyRoles:
        await role.delete(reason='Cactus Coin: Removing unused role.')


async def update_role(guild: discord.Guild, member: discord.Member, amount: int):
    """
    Deletes old role and calls function to update new role displaying coin amount
    :param guild:
    :param member:
    :param amount:
    :return:
    """
    await remove_role(guild, member)
    role = await create_role(guild, amount)
    await member.add_roles(role, reason=f'Cactus Coin: Role updated for {member.name} to {str(amount)}')


async def add_coin(guild: discord.Guild, member: discord.Member, amount: int, persist: bool = True):
    """
    Adds a specified coin amount to a member's role and stores in the database
    :param guild:
    :param member:
    :param amount:
    :param persist:
    :return:
    """
    current_coin = get_coin(member.id)
    new_coin = max(current_coin + amount, config.get_attribute('debtLimit'))
    update_coin(member.id, new_coin)
    if persist:
        add_transaction(member.id, amount)
    await update_role(guild, member, new_coin)


def start_bet(bet_author: discord.Member, bet_opponent: discord.Member, amount: int, reason: str) -> str:
    """
    Starts a bet instance
    :param bet_author:
    :param bet_opponent:
    :param amount:
    :param reason:
    :return:
    """
    # generate id
    bet_id = random_id()
    while fetch_bet(bet_id):
        bet_id = random_id()
    add_bet(bet_id=bet_id, author_id=bet_author.id, opponent_id=bet_opponent.id, amount=amount, reason=reason)
    return bet_id


async def get_movements(guild: discord.Guild, time_period: str, is_wins: bool):
    """
    Gets outlier movements either positive or negative and outputs a chart of them
    :param guild:
    :param time_period:
    :param is_wins:
    :return:
    """
    # TODO: FIX TIME PERIODS, GET START OF TIME THEN CONVERT TO UTC
    start_period = ''
    if time_period == 'week':
        start_period = datetime.now() - timedelta(days=datetime.now().weekday())
    elif time_period == 'month':
        start_period = datetime.today().replace(day=1)
    elif time_period == 'year':
        start_period = date(date.today().year, 1, 1)

    transactions = get_transactions(start_period)
    if not transactions:
        return None
    if is_wins:
        transactions = [i for i in transactions if i[1] > 0]
    else:
        transactions = [i for i in transactions if i[1] < 0]
    numb_trans = min(len(transactions), 5)
    transactions = transactions[:numb_trans] if is_wins else transactions[-numb_trans:]

    await graph_amounts(guild, transactions)
    plt.xlabel('Coin (¢)')

    if is_wins:
        plt.title('Greatest Wins From the Past ' + time_period.capitalize(), fontweight='bold')
        filename = f'../tmp/wins-{time_period}.png'
    else:
        plt.title('Greatest Losses From the Past ' + time_period.capitalize(), fontweight='bold')
        filename = f'../tmp/losses-{time_period}.png'
    plt.savefig(filename, bbox_inches='tight', pad_inches=.5)
    plt.close()
    return filename


# Computes power rankings for the server and outputs them in a bar graph in an image
async def compute_rankings(guild: discord.Guild):
    rankings = get_coin_rankings()
    await graph_amounts(guild, rankings)
    today_date = datetime.today().astimezone(tz=timezone('US/Eastern'))
    today = today_date.strftime("%m-%d-%Y")
    plt.title('Cactus Gang Power Rankings\n' + today, fontweight='bold')
    plt.xlabel('Coin (¢)')
    plt.savefig(f'../tmp/power-rankings-{today}.png', bbox_inches='tight', pad_inches=.5)
    plt.close()
    return f'../tmp/power-rankings-{today}.png'


# Verify we have a member's icon
async def get_icon(member: discord.Member):
    # check if we already have the file in tmp folder, if not grab it and save it.
    icon = member.display_avatar
    stored_icons = os.listdir('../tmp')
    if f'{icon.key}-44px.png' not in stored_icons:
        img = Image.open(BytesIO(await icon.read()))
        img = img.resize((128, 128))
        img.save(f'../tmp/{icon.key}.png')
        img.putalpha(icon_mask)
        img = img.resize(icon_size)
        img.save(f'../tmp/{icon.key}-44px.png')
        img.close()


# Generic function for graphing a nice looking bar chart of values for each member
# This function does not set plot title, axis titles, or close the plot
async def graph_amounts(guild: discord.Guild, data):
    # pull all images of ranking members from Discord
    member_icons, member_names, member_amounts, member_color = [], [], [], []

    for member_id, amount in data:
        member = guild.get_member(member_id)
        if not member:
            return
        await get_icon(member)

        member_icons.append(f'../tmp/{member.display_avatar.key}-44px.png')
        member_names.append(member.display_name)
        member_amounts.append(amount)
        # alternate bar color generation
        # im = img.resize((1, 1), Image.NEAREST).convert('RGB')
        # color = im.getpixel((0, 0))
        # normalize pixel values between 0 and 1
        memberC = member.color \
            if (
                member.color != discord.Color.default() or
                member.color != discord.Color.from_rgb(1, 1, 1)) \
            else discord.Color.blurple()
        color = (memberC.r, memberC.g, memberC.b)
        member_color.append(tuple(t / 255. for t in color))
    ax = plt.axes()
    ax.set_axisbelow(True)
    ax.yaxis.grid(color='.9', linestyle='dashed')
    ax.xaxis.grid(color='.9', linestyle='dashed')
    lab_x = [i for i in range(len(data))]
    height = .8
    plt.barh(lab_x, member_amounts, height=height, color=member_color)
    plt.yticks(lab_x, member_names)

    # create a glowy effect on the plot by plotting different bars
    n_shades = 5
    diff_linewidth = .05
    alpha_value = 0.5 / n_shades
    for n in range(1, n_shades + 1):
        plt.barh(lab_x, member_amounts,
                 height=(height + (diff_linewidth * n)),
                 alpha=alpha_value,
                 color=member_color)

    # add user icons to bar charts
    max_value = max(member_amounts)
    for i, (value, icon) in enumerate(zip(member_amounts, member_icons)):
        offset_image(value, i, icon, max_value=max_value, ax=ax)


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


# Returns the index of the winning member in members
def get_winner(num_players, win_ang):
    slice_degree = 360 / num_players
    curr_degree = win_ang
    for i in range(num_players):
        if curr_degree < slice_degree:
            return i
        curr_degree -= slice_degree


# Generate wheel for bet as a gif
async def generate_wheel(members: List[discord.Member]):
    canvas_size = 1000
    wheel_offset = 5
    bounding_box = ((wheel_offset, wheel_offset), (canvas_size - wheel_offset, canvas_size - wheel_offset))
    slice_degree = 360 / len(members)
    radius = (bounding_box[1][0] - bounding_box[0][0]) / 2
    curr_slice = 0
    wheel = Image.new('RGBA', (canvas_size, canvas_size), '#212946')
    for member in members:
        # Verify we have the member's icon stored
        await get_icon(member)
        wheel_draw = ImageDraw.Draw(wheel)
        wheel_draw.pieslice(bounding_box, start=curr_slice, end=curr_slice + slice_degree, fill=member.color.to_rgb(),
                            width=5, outline='white')
        # Put each participant's icon on the image
        if len(members) < 6:
            member_icon = Image.open(f'../tmp/{member.display_avatar.key}.png')
            offset = 128
        else:
            member_icon = Image.open(f'../tmp/{member.display_avatar.key}-44px.png')
            offset = 44
        member_icon = member_icon.convert('RGBA')
        midAngle = curr_slice + slice_degree / 2

        # grab coordinates to place icon at
        coords = (round(bounding_box[0][1] + radius + 0.5 * radius * sin(radians(midAngle - 90))) - offset,
                  round(bounding_box[0][0] + radius + 0.5 * radius * cos(radians(midAngle - 90))) - offset)
        wheel.paste(member_icon.rotate(midAngle + 90), coords)
        curr_slice += slice_degree

    win_ang = random.randint(0, 360)

    # generate time mesh for acceleration function to operate on
    # set to be 7 "seconds" polled at .1 seconds found this gave enough
    # points to make a smoother gif
    time_mesh = [i / 10 for i in range(71)]

    # starting set of rotations I found to look like someone is pulling a wheel back for
    # a rather large spin. can be messed around with
    start_animation = [0.0, -0.75, -1.5, -2.25, -3.0, -3.75, -4.5, -5.25]

    # start actual spin at the last part of the pullback
    # store all rotations of original image (in degrees) that create the gif
    rotations = [start_animation[7]]
    velocities = [0]

    # e^2t for no real reason other than it makes the wheel get up to speed quick
    acceleration_func = lambda t: exp(2 * t) if t <= 2.0 else 0

    # now calculate distance traveled in degrees from the original image for each point in the
    # time mesh using basic rotational dynamics
    for i in range(1, len(time_mesh)):
        t = time_mesh[i]
        a = acceleration_func(t)
        v = velocities[i - 1] + a * t
        d = rotations[i - 1] + v * t

        rotations.append(d)
        velocities.append(v)

    # Regardless of where we ended up, square up the last point with the original image so we can
    # position the wheel where the winning slice always hits the top
    win_ang_pos = rotations[len(rotations) - 1] + (360 - (rotations[len(rotations) - 1] % 360))
    rotations.append(win_ang_pos)

    # In order to hit the top of the circle, find the distance from the winning angle to 270(the top
    # of the circle). The minus 180 here is used to get the more gentle stop from the end_animation
    # array
    rotations.append(
        win_ang_pos + (270 - win_ang) - 180 if win_ang <= 270 else win_ang_pos + 360 - (win_ang - 270) - 180)
    end_animation = [45, 45, 25, 20, 20, 10, 5, 2, 1, 1, 1]
    curr = rotations[len(rotations) - 1]
    for i in range(len(end_animation)):
        curr += end_animation[i]
        rotations.append(curr)

    # Append the start animation to the front of the rotations array
    rotations = start_animation + rotations

    # Make the gif
    outPath = '../tmp/wheel.gif'
    wheel_imgs = []
    triangle = (bounding_box[0][0] + radius - 30, 0), (bounding_box[0][0] + radius + 30, 0), (bounding_box[0][0] + radius, 50)
    for i in range(len(rotations)):
        currWheel = wheel.rotate(-rotations[i], expand=False, fillcolor='#212946')
        draw = ImageDraw.Draw(currWheel)
        draw.polygon(triangle, outline='#181A1B', fill='#181A1B')
        wheel_imgs.append(currWheel)
    draw = ImageDraw.Draw(wheel)
    draw.polygon(triangle, outline='#181A1B', fill='#181A1B')
    wheel.save(outPath, save_all=True, append_images=wheel_imgs)
    winner = get_winner(len(members), win_ang)
    return outPath, winner
