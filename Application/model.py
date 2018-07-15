from peewee import Model, SqliteDatabase
from peewee import TextField, DateTimeField, IntegerField

db = SqliteDatabase('MailSync.db')

# Connect DB
db.connect()

class Mail(Model):
    gid = TextField(unique=True)
    subject = TextField()
    message = TextField()
    date = DateTimeField()
    sender = TextField()
    class Meta:
        database = db

class Sync(Model):
    syncedon = IntegerField(unique=True)
    class Meta:
        database = db

# Create table if not exists
db.create_tables([Mail,Sync])