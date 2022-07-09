from peewee import *

db = SqliteDatabase('gfd.db')


class BaseModel(Model):
    class Meta:
        database = db


class AnnouncedYoutubeVideo(BaseModel):
    video_id = CharField(null=False, unique=True, primary_key=True)

    @staticmethod
    def should_announce(video_id):
        try:
            video = AnnouncedYoutubeVideo.get(AnnouncedYoutubeVideo.video_id == video_id)
            return False
        except DoesNotExist:
            AnnouncedYoutubeVideo.create(video_id=video_id)
            return True


class User(BaseModel):
    user_id = BigIntegerField(unique=True, primary_key=True)
    username = CharField(null=False)
    ducks_befriended = BigIntegerField(default=0)
    ducks_killed = BigIntegerField(default=0)

    @staticmethod
    def get_by_author(author):
        username = author.display_name
        try:
            user = User.get(User.user_id == author.id)
            if user.username != username and username:
                user.username = username
                user.save()
        except DoesNotExist:
            user = User.create(user_id=author.id, username=username)
        return user

    @staticmethod
    def get_by_message(message):
        return User.get_by_author(message.author)

    def has_repented_for_shooting_ducks(self):
        return self.ducks_killed * 3 <= self.ducks_befriended

    def add_duck_friend(self):
        self.ducks_befriended += 1
        self.save()

    def add_duck_kill(self):
        self.ducks_killed += 1
        self.save()
