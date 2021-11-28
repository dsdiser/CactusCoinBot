import sqlite3
import atexit
import config


try:
    connection = sqlite3.connect(config.getAttribute('dbFile'))
    connection.execute('CREATE TABLE IF NOT EXISTS AMOUNTS (id text PRIMARY KEY, coin integer)')
except sqlite3.Error as e:
    print(e)


def closeDB():
    if connection:
        connection.close()


atexit.register(closeDB)
