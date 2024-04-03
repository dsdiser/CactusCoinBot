from peewee import *
from . import config

database = SqliteDatabase(config.get_attribute('dbFile'))


class UnknownField(object):
    def __init__(self, *_, **__):
        pass


class BaseModel(Model):
    class Meta:
        database = database


class Amounts(BaseModel):
    coin = IntegerField(null=True)
    correct_answers = IntegerField(null=True)
    incorrect_answers = IntegerField(null=True)

    class Meta:
        table_name = "AMOUNTS"


class Bets(BaseModel):
    active = IntegerField(null=True)
    amount = IntegerField(null=True)
    author = IntegerField(null=True)
    date = DateField(null=True)
    id = CharField(null=True)
    opponent = IntegerField(null=True)
    reason = TextField(null=True)

    class Meta:
        table_name = "BETS"
        primary_key = False


class Transactions(BaseModel):
    coin = IntegerField(null=True)
    date = DateField(null=True)
    id = IntegerField(null=True)
    memo = TextField(null=True)

    class Meta:
        table_name = "TRANSACTIONS"
        primary_key = False


class TriviaChannels(BaseModel):
    channel_id = IntegerField(null=True, unique=True)
    correct_users = TextField(null=True)
    incorrect_users = TextField(null=True)
    message_id = IntegerField(null=True)
    reward = IntegerField(null=True)

    class Meta:
        table_name = "TRIVIA_CHANNELS"
        primary_key = False


class TriviaHashes(BaseModel):
    hash = IntegerField(null=True, unique=True)

    class Meta:
        table_name = "TRIVIA_HASHES"
        primary_key = False