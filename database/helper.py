from database.models import User, db, AnnouncedYoutubeVideo, DuckAttemptLog, db_links, PostedLink


class BaseDatabaseHelper:
    def __init__(self, db_conn, models):
        self.db_conn = db_conn
        self.db_conn.connect()
        self.db_conn.create_tables(models)
        self.db_conn.commit()
        self.db_conn.close()

    def replenish_db(self):
        if not self.db_conn.is_connection_usable():
            self.db_conn.connect()

    def release_db(self):
        self.db_conn.commit()
        self.db_conn.close()


gfd_database_helper = BaseDatabaseHelper(db, [
    User,
    AnnouncedYoutubeVideo,
    DuckAttemptLog
])

gfd_links_database_helper = BaseDatabaseHelper(db_links, [
    PostedLink
])
