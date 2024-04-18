from datetime import datetime
from peewee import SqliteDatabase, IntegerField, AutoField, DateField, TextField, Model, BooleanField, CharField, ForeignKeyField
import src.config as config

database = SqliteDatabase(config.get_attribute('dbFile'), pragmas={'foreign_keys': 1})


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

    class Meta:
        table_name = "TRANSACTIONS"
        primary_key = False


class FoodAnswer(BaseModel):
    """Tracking user's answers """
    user_id = IntegerField()
    barcode = IntegerField(primary_key=True)
    date = DateField(default=datetime.utcnow())
    answer = TextField()
    is_correct = BooleanField()

    class Meta:
        table_name = "FOOD_ANSWER"


class Food(BaseModel):
    barcode = IntegerField(primary_key=True)
    name = TextField()
    image_url = TextField()
    used = BooleanField() # Whether the food has been used for a trivia

    class Meta:
        table_name = "FOOD"
    

class CountryAnswer(BaseModel):
    barcode = ForeignKeyField(Food, backref='countries')
    correct = BooleanField()
    name = CharField(max_length=50)

    class Meta:
        table_name = "COUNTRY_ANSWER"

class FoodChannel(BaseModel):
    id = IntegerField(primary_key=True)

TABLES = [Amount, Transaction, FoodAnswer, Food, CountryAnswer, FoodChannel]

