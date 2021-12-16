import sqlite3
import atexit
import config
import signal


try:
    connection = sqlite3.connect(config.getAttribute('dbFile'))
    connection.execute('CREATE TABLE IF NOT EXISTS AMOUNTS (id integer PRIMARY KEY, coin integer)')
    connection.execute('CREATE TABLE IF NOT EXISTS TRANSACTIONS (id integer, coin integer, memo string, date date)')
except sqlite3.Error as e:
    print(e)


def handle_exit():
    if connection:
        connection.close()

atexit.register(handle_exit)
signal.signal(signal.SIGTERM, handle_exit)
signal.signal(signal.SIGINT, handle_exit)