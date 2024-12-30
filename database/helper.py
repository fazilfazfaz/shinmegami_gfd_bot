import logging

import database.models
import logger

if logger.is_dev:
    pewee_logger = logging.getLogger('peewee')
    pewee_logger.addHandler(logging.StreamHandler())
    pewee_logger.setLevel(logging.DEBUG)


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


gfd_database_helper = BaseDatabaseHelper(database.models.db, [
    database.models.User,
    database.models.AnnouncedYoutubeVideo,
    database.models.DuckAttemptLog,
    database.models.BannedBannerMessage,
    database.models.GiftySanta,
    database.models.GiftySantaAssignment,
])

gfd_links_database_helper = BaseDatabaseHelper(database.models.db_links_v2, [
    database.models.PostedLinkV2
])

gfd_emojis_database_helper = BaseDatabaseHelper(database.models.db_emojis, [
    database.models.UserReaction,
])
