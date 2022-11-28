import sqlite3
import atexit
from datetime import datetime

import config
import signal


try:
    connection = sqlite3.connect(config.getAttribute('dbFile'))
    connection.execute('CREATE TABLE IF NOT EXISTS AMOUNTS (id integer PRIMARY KEY, coin integer)')
    connection.execute('CREATE TABLE IF NOT EXISTS TRANSACTIONS (id integer, coin integer, memo text, date date)')
    connection.execute('CREATE TABLE IF NOT EXISTS BETS (id varchar(4), date date, author integer, opponent integer, amount integer, reason text, active integer)')
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


def add_bet(bet_id: str, author_id: int, opponent_id: int, amount: int, reason: str):
    """
    Adds a bet entry for two members
    :param bet_id:
    :param author_id:
    :param opponent_id:
    :param amount:
    :param reason:
    :return:
    """
    cur = connection.cursor()
    cur.execute("INSERT INTO BETS(id, date, author, opponent, amount, reason, active) VALUES (?, ?, ?, ?, ?, ?, ?)",
                (bet_id, datetime.utcnow(), author_id, opponent_id, amount, reason, True))
    connection.commit()


def fetch_bet(bet_id: str):
    """
    Fetches bet entry from id
    :param bet_id:
    :return:
    """
    cur = connection.cursor()
    bet = cur.execute("SELECT * FROM BETS WHERE id is (?)", (bet_id,)).fetchone()
    return bet


def remove_bet(bet_id: str):
    """
    Removes a bet entry
    :param bet_id:
    :return:
    """
    cur = connection.cursor()
    cur.execute("DELETE FROM BETS WHERE id is (?)", (bet_id,))
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


def get_transactions(time: datetime):
    """
    Get all transactions between now and the given date, ordered from greatest to least.
    :param time:
    :return:
    """
    cur = connection.cursor()
    transactions = cur.execute("SELECT id, coin FROM TRANSACTIONS WHERE date BETWEEN ? AND ? ORDER BY coin",
                               (time, datetime.utcnow())).fetchall()
    if transactions:
        return transactions
    return None


def get_active_bets():
    """
    Get all active bets
    :return:
    """
    cur = connection.cursor()
    bets = cur.execute("SELECT * FROM BETS WHERE active = 1 ORDER BY date").fetchall()
    if bets:
        return bets
    return None
