from urllib.parse import urlparse

from peewee import *

db = SqliteDatabase('gfd.db')
db_links = SqliteDatabase('gfd_links.db')
db_links_v2 = SqliteDatabase('gfd_links_v2.db')
db_emojis = SqliteDatabase('gfd_emojis.db')


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


# Legacy posted link
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
        return PostedLink.get_or_none(PostedLink.link == link)

    @staticmethod
    def get_top_links(count: int):
        return PostedLink.select().order_by(PostedLink.hits.desc()).limit(count)

    @staticmethod
    def create_link(link):
        return PostedLink.create(link=link)


class PostedLinkV2(Model):
    class Meta:
        database = db_links_v2
        indexes = (
            (('link_minus_qp', 'qp'), True),
        )

    id = BigAutoField(primary_key=True)
    link_minus_qp = TextField()
    qp = TextField()
    hits = IntegerField(default=0)

    def increment_hits(self):
        self.hits += 1

    @staticmethod
    def get_hits_times_text(hits):
        times = 'times' if hits > 1 else 'time'
        return f'{hits} {times}'

    @staticmethod
    def get_hits_by_link(link):
        link_minus_qp, qp = PostedLinkV2.parse_link(link)
        link: PostedLinkV2 = PostedLinkV2.get_or_none(PostedLinkV2.link_minus_qp == link_minus_qp,
                                                      PostedLinkV2.qp == qp)
        if link is not None:
            return link.hits
        count = PostedLinkV2.select().where(PostedLinkV2.link_minus_qp == link_minus_qp).count()
        if count > 50:
            return 0
        hits = 0
        for link in PostedLinkV2.select().where(PostedLinkV2.link_minus_qp == link_minus_qp):
            hits += link.hits
        return hits

    @staticmethod
    def parse_link(link):
        parsed_url = urlparse(link)
        link_minus_qp = '{}://{}{}'.format(parsed_url.scheme, parsed_url.netloc, parsed_url.path)
        if parsed_url.params:
            link_minus_qp += ';{}'.format(parsed_url.params)
        qp = parsed_url.query
        return link_minus_qp, qp

    @staticmethod
    def get_top_links(count: int):
        return PostedLinkV2.select().order_by(PostedLinkV2.hits.desc()).limit(count)

    @staticmethod
    def create_link(link, hits=1):
        link_minus_qp, qp = PostedLinkV2.parse_link(link)
        return PostedLinkV2.create(link_minus_qp=link_minus_qp, qp=qp, hits=hits)

    def full_link(self):
        return self.link_minus_qp + '?' + self.qp


class BannedBannerMessage(BaseModel):
    message_id = BigIntegerField(primary_key=True)

    @staticmethod
    def get_by_message_id(message_id):
        return BannedBannerMessage.get_or_none(BannedBannerMessage.message_id == message_id)


class UserReaction(Model):
    class Meta:
        database = db_emojis

    id = BigAutoField(primary_key=True)
    source_user_id = BigIntegerField(null=False)
    target_user_id = BigIntegerField(null=False)
    emoji_id = BigIntegerField(null=True, default=None)
    emoji_str = TextField(null=True, default=None)
    is_add = BooleanField(default=True, null=False)
