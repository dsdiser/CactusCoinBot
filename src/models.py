from peewee import SqliteDatabase, IntegerField, AutoField, DateField, TextField, Model, BooleanField
import src.config as config

database = SqliteDatabase(config.get_attribute('dbFile'))


class UnknownField(object):
    def __init__(self, *_, **__):
        pass


class BaseModel(Model):
    class Meta:
        database = database


class Amount(BaseModel):
    """Essentially each user's wallet"""
    id = IntegerField(primary_key=True)
    coin = IntegerField(null=True)

    class Meta:
        table_name = "AMOUNTS"


class Transaction(BaseModel):
    """Model for transactions between users"""
    id = AutoField()
    coin = IntegerField(null=True)
    date = DateField(null=True)
    memo = TextField(null=True)

    class Meta:
        table_name = "TRANSACTIONS"
        primary_key = False


class FoodAnswer(BaseModel):
    """Tracking user's answers """
    user_id = IntegerField()
    barcode = IntegerField()
    date = DateField()
    answer = TextField()
    is_correct = BooleanField()

    class Meta:
        table_name = "FOOD_ANSWER"
        primary_key = False

TABLES = [Amount, Transaction, FoodAnswer]

