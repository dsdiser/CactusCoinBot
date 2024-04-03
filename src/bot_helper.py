from datetime import datetime
import logging
from io import BytesIO
import os

import discord
from PIL import Image, ImageDraw
import matplotlib.pyplot as plt
from matplotlib.offsetbox import OffsetImage, AnnotationBbox
from pytz import timezone

from . import config
from .sql_client import get_coin, add_transaction, get_coin_rankings, update_coin

# Matplotlib styling
plt.style.use('dark_background')
for param in ['text.color', 'axes.labelcolor', 'xtick.color', 'ytick.color']:
    plt.rcParams[param] = '0.9'  # very light grey
for param in ['figure.facecolor', 'axes.facecolor', 'savefig.facecolor']:
    plt.rcParams[param] = '#212946'  # bluish dark grey
plt.rcParams['font.family'] = 'Tahoma'
plt.rcParams['font.size'] = 16

ICON_SIZE = (44, 44)
icon_mask = Image.new('L', (128, 128))
mask_draw = ImageDraw.Draw(icon_mask)
mask_draw.ellipse((0, 0, 128, 128), fill=255)

RANKINGS_FOLDER = '../tmp/rankings'


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

    role_names = [role.name for role in member.roles if prefix in role.name]
    if not role_names:
        role = await create_role(guild, amount)
        await member.add_roles(role, reason=f'Cactus Coin: Role updated for {member.name} to {str(amount)}')


async def clear_old_roles(guild: discord.Guild):
    """
    Deletes all old cactus coin roles
    :param guild:
    :return:
    """
    empty_roles = [role for role in guild.roles if 'Cactus Coin:' in role.name and len(role.members) == 0]
    for role in empty_roles:
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


# Computes power rankings for the server and outputs them in a bar graph in an image
async def compute_rankings(guild: discord.Guild):
    rankings = get_coin_rankings()
    await graph_amounts(guild, rankings)
    today_date = datetime.today().astimezone(tz=timezone('US/Eastern'))
    today = today_date.strftime("%m-%d-%Y")
    plt.title('Cactus Gang Power Rankings\n' + today, fontweight='bold')
    plt.xlabel('Coin (¢)')
    if not os.path.exists(RANKINGS_FOLDER):
        os.makedirs(RANKINGS_FOLDER)
    image_path = f'{RANKINGS_FOLDER}/power-rankings-{today}.png'
    plt.savefig(image_path, bbox_inches='tight', pad_inches=.5)
    plt.close()
    return image_path


def remove_file(file_path: str):
    """
    Removes a file if it exists
    :param file_path:
    :return:
    """
    if os.path.isfile(file_path):
        os.remove(file_path)


# Verify we have a member's icon
async def get_icon(member: discord.Member):
    # check if we already have the file in tmp folder, if not grab it and save it.
    icon = member.display_avatar
    stored_icons = os.listdir('../tmp')
    if f'{icon.key}-44px.png' not in stored_icons:
        img = Image.open(BytesIO(await icon.read())).convert('RGB')
        img = img.resize((128, 128))
        img.save(f'../tmp/{icon.key}.png', 'PNG')
        img.putalpha(icon_mask)
        img = img.resize(ICON_SIZE)
        img.save(f'../tmp/{icon.key}-44px.png', 'PNG')
        img.close()


async def graph_amounts(guild: discord.Guild, data):
    """Generic function for graphing a nice looking bar chart of values for each member
    This function does not set plot title, axis titles, or close the plot"""
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


def offset_image(x, y, icon, max_value, ax):
    """Adds discord icons to bar chart"""
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
