from peewee import *

db = SqliteDatabase('gfd.db')


class BaseModel(Model):
    class Meta:
        database = db


class User(BaseModel):
    user_id = BigIntegerField(unique=True, primary_key=True)
    username = CharField(null=False)
    ducks_befriended = BigIntegerField(default=0)
    ducks_killed = BigIntegerField(default=0)

    @staticmethod
    def get_by_message(message):
        username = message.author.display_name
        try:
            user = User.get(User.user_id == message.author.id)
            if user.username != username and username:
                user.username = username
                user.save()
        except DoesNotExist:
            user = User.create(user_id=message.author.id, username=username)
        return user

    def add_duck_friend(self):
        self.ducks_befriended += 1
        self.save()

    def add_duck_kill(self):
        self.ducks_killed += 1
        self.save()
