import json
import sqlite3
import atexit
from datetime import datetime
from typing import List

import config
import signal


# TODO: This is messy, should really be using an ORM to manage these

try:
    connection = sqlite3.connect(config.get_attribute('dbFile'))
    connection.execute('CREATE TABLE IF NOT EXISTS AMOUNTS (id integer PRIMARY KEY, coin integer, correct_answers integer, incorrect_answers integer)')
    connection.execute('CREATE TABLE IF NOT EXISTS TRANSACTIONS (id integer, coin integer, memo text, date date)')
    connection.execute(
        'CREATE TABLE IF NOT EXISTS TRIVIA_CHANNELS (channel_id integer, message_id integer, correct_users text, incorrect_users text, reward integer, UNIQUE (channel_id))'
    )
    connection.execute(
        'CREATE TABLE IF NOT EXISTS TRIVIA_HASHES (hash integer, unique (hash))'
    )
except sqlite3.Error as e:
    print(e)


def handle_exit():
    if connection:
        connection.close()


atexit.register(handle_exit)
signal.signal(signal.SIGTERM, handle_exit)
signal.signal(signal.SIGINT, handle_exit)


def update_coin(member_id: int, amount: int):
    """
    Upserts a user's coin to the given amount
    :param member_id:
    :param amount:
    :return:
    """
    cur = connection.cursor()
    cur.execute(
        "INSERT INTO AMOUNTS(id, coin) VALUES ('{0}', {1}) ON CONFLICT(id) DO UPDATE SET coin=excluded.coin".format(
            member_id, amount))
    connection.commit()
    return amount


def get_coin(member_id: int):
    """
    Gets member's coin
    :param member_id:
    :return:
    """
    cur = connection.cursor()
    amount = cur.execute("SELECT coin from AMOUNTS WHERE id IS '{0}'".format(member_id)).fetchone()
    if amount:
        return amount[0]
    return None


def remove_coin(member_id: int):
    """
    Clears out all coin from a member's entry
    :param member_id:
    :return:
    """
    cur = connection.cursor()
    cur.execute("DELETE FROM AMOUNTS WHERE id is '{0}'".format(member_id))
    connection.commit()


def add_transaction(member_id: int, amount: int):
    """
    Adds a transaction entry for a specific member
    :param member_id:
    :param amount:
    :return:
    """
    cur = connection.cursor()
    cur.execute("INSERT INTO TRANSACTIONS(date, id, coin) VALUES (?, ?, ?)",
                (datetime.utcnow(), member_id, amount))
    connection.commit()


def remove_transactions(member_id: int):
    """
    Removes all transactions associated with a user
    :param member_id:
    :return:
    """
    cur = connection.cursor()
    cur.execute("DELETE FROM TRANSACTIONS WHERE id is '{0}'".format(member_id))
    connection.commit()


def get_coin_rankings():
    """
    Gets rankings of coin amounts
    :return:
    """
    cur = connection.cursor()
    amounts = cur.execute("SELECT id, coin FROM AMOUNTS ORDER BY coin").fetchall()
    if amounts:
        return amounts
    return None


def update_correct_answer_count(user_id: int):
    """
    Adds one to the user's correct answer count if it exists, starts one otherwise
    :param user_id:
    :return:
    """
    cur = connection.cursor()
    cur.execute("UPDATE AMOUNTS SET correct_answers = correct_answers + 1 WHERE id is (?)", (user_id,))
    connection.commit()


def update_incorrect_answer_count(user_id: int):
    """
    Adds one to the user's incorrect answer count if it exists, starts one otherwise
    :param user_id:
    :return:
    """
    cur = connection.cursor()
    cur.execute("UPDATE AMOUNTS SET incorrect_answers = incorrect_answers + 1 WHERE id is (?)", (user_id,))
    connection.commit()


def get_answer_counts(user_id: int):
    """
    Gets a user's number of correct and incorrect answers to trivia questions
    :param user_id:
    :return:
    """
    cur = connection.cursor()
    counts = cur.execute(
        "SELECT correct_answers, incorrect_answers FROM AMOUNTS WHERE id is (?)",
        (user_id,)
    ).fetchone()
    return counts


def get_answer_rankings():
    """
    Gets rankings of trivia amounts
    :return:
    """
    cur = connection.cursor()
    amounts = cur.execute("SELECT id, correct_answers FROM AMOUNTS ORDER BY coin").fetchall()
    if amounts:
        return amounts
    return None


"""
TRIVIA
"""


def serialize_user_list(users: List[int]) -> str:
    obj = {'users': users}
    return json.dumps(obj)


def deserialize_user_list(users: str) -> List[int]:
    users_json = json.loads(users)
    return users_json['users'] if users_json['users'] else []


def get_channels():
    """
    Gets all channels to send trivia question to
    :return:
    """
    cur = connection.cursor()
    channels = cur.execute('SELECT channel_id, message_id, reward FROM TRIVIA_CHANNELS').fetchall()
    if channels:
        return channels
    return None


def get_correct_users(channel_id: int) -> List[int]:
    """Gets all users with a correct answer for the channel"""
    cur = connection.cursor()
    users = cur.execute('SELECT correct_users FROM TRIVIA_CHANNELS WHERE channel_id = (?)', (channel_id,)).fetchone()
    if users is None:
        return "[]"
    return deserialize_user_list(users[0])


def get_incorrect_users(channel_id: int) -> List[int]:
    """Gets all users with an incorrect answer for the channel"""
    cur = connection.cursor()
    users = cur.execute('SELECT incorrect_users FROM TRIVIA_CHANNELS WHERE channel_id = (?)', (channel_id,)).fetchone()
    if users is None:
        return "[]"
    return deserialize_user_list(users[0])


def add_channel(channel_id: int) -> None:
    """Adds a channel to the list of channels enabled for trivia questions"""
    cur = connection.cursor()
    cur.execute('INSERT OR IGNORE INTO TRIVIA_CHANNELS(channel_id, message_id, reward) VALUES (?, ?, ?)',
                (channel_id, 0, 25))
    connection.commit()


def update_message_id(channel_id: int, message_id: int) -> None:
    """Adds a new message for a specific channel and resets correct and incorrect users"""
    cur = connection.cursor()
    empty_user_list = serialize_user_list([])
    cur.execute("UPDATE TRIVIA_CHANNELS "
                "SET message_id = (?), correct_users = (?), incorrect_users = (?) "
                "WHERE channel_id = (?)",
                (message_id, empty_user_list, empty_user_list, channel_id))
    connection.commit()


def update_reward(channel_id: int, reward: int) -> None:
    """Adds a new message for a specific channel and resets correct and incorrect users"""
    cur = connection.cursor()
    cur.execute("UPDATE TRIVIA_CHANNELS "
                "SET reward = (?) "
                "WHERE channel_id = (?)",
                (reward, channel_id))
    connection.commit()


def update_correct_users(channel_id: int, correct_users: List[int]) -> None:
    """Updates the list of correct users for a channel"""
    cur = connection.cursor()
    users = serialize_user_list(correct_users)
    cur.execute("UPDATE TRIVIA_CHANNELS "
                "SET correct_users = (?) "
                "WHERE channel_id = (?)",
                (users, channel_id))
    connection.commit()


def update_incorrect_users(channel_id: int, incorrect_users: List[int]) -> None:
    """Updates the list of incorrect users for a channel"""
    cur = connection.cursor()
    users = serialize_user_list(incorrect_users)
    cur.execute("UPDATE TRIVIA_CHANNELS "
                "SET incorrect_users = (?) "
                "WHERE channel_id = (?)",
                (users, channel_id))
    connection.commit()


def remove_channel(channel_id: int) -> None:
    """Removes a channel from the list of channels enabled for trivia questions"""
    cur = connection.cursor()
    cur.execute("DELETE FROM TRIVIA_CHANNELS WHERE channel_id = (?)",
                (channel_id,))
    connection.commit()


def get_seen_questions():
    """Gets all the currently seen questions"""
    cur = connection.cursor()
    hashes = cur.execute('SELECT * FROM TRIVIA_HASHES').fetchall()
    if hashes:
        return hashes
    return None


def add_seen_question(question_hash: int):
    """Adds a seen hash to the table of hashes"""
    cur = connection.cursor()
    cur.execute("INSERT OR IGNORE INTO TRIVIA_HASHES(hash) VALUES (?)", (question_hash,))
    connection.commit()
