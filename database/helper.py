from database.models import User, db, AnnouncedYoutubeVideo, DuckAttemptLog


class GFDDatabaseHelper:
    def __init__(self):
        db.connect()
        db.create_tables([
            User,
            AnnouncedYoutubeVideo,
            DuckAttemptLog
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
