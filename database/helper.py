from database.models import User, db, AnnouncedYoutubeVideo


class GFDDatabaseHelper:
    def __init__(self):
        db.connect()
        db.create_tables([
            User,
            AnnouncedYoutubeVideo
        ])
        db.commit()
        db.close()

    @staticmethod
    def replenish_db():
        if not db.is_connection_usable():
            db.connect()

    @staticmethod
    def release_db():
        db.commit()
        db.close()
