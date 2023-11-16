from peewee import *

db = SqliteDatabase('gfd.db')
db_links = SqliteDatabase('gfd_links.db')


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
    ducks_shooed = BigIntegerField(default=0)
    timezone = CharField(null=True)

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
        return self.ducks_killed <= self.ducks_befriended

    def add_duck_friend(self):
        self.ducks_befriended += 1
        self.save()

    def add_duck_kill(self):
        self.ducks_killed += 1
        self.save()

    def add_duck_shoo(self):
        self.ducks_shooed += 1
        self.save()

    def set_timezone(self, timezone):
        self.timezone = timezone
        self.save()


class DuckAttemptLog(BaseModel):
    id = BigAutoField(primary_key=True)
    user_id = BigIntegerField()
    chance = DecimalField()
    random_val = DecimalField()
    missed = BooleanField()

    @staticmethod
    def create_attempt(user_id, chance, random_val, missed):
        return DuckAttemptLog.create(user_id=user_id, chance=chance, random_val=random_val, missed=missed)


class PostedLink(Model):
    class Meta:
        database = db_links

    id = BigAutoField(primary_key=True)
    link = TextField(unique=True)
    hits = IntegerField(default=0)

    def increment_hits(self):
        self.hits += 1

    def get_hits_times_text(self):
        times = 'times' if self.hits > 1 else 'time'
        return f'{self.hits} {times}'

    @staticmethod
    def get_by_link(link):
        return PostedLink.get(PostedLink.link == link)

    @staticmethod
    def get_top_links(count: int):
        return PostedLink.select().order_by(PostedLink.hits.desc()).limit(count)

    @staticmethod
    def create_link(link):
        return PostedLink.create(link=link)
