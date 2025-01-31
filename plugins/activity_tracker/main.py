import datetime
from datetime import timedelta

import discord
from peewee import fn

from database.helper import gfd_database_helper
from database.models import Activity, ActivityGame, ActivityGamePlatform
from logger import logger
from plugins.base import BasePlugin


class ActivityTracker(BasePlugin):

    def on_ready(self):
        if self.is_ready():
            return

    async def on_message(self, message: discord.Message):
        if message.content.lower() == '.games':
            await self.post_weekly_stats(message)
        if message.content.lower() == '.games-daily':
            await self.post_daily_stats(message)

    async def presence_update(self, before: discord.Member, after: discord.Member):
        prior_game_activities: list[discord.Activity] = list(
            filter(lambda x: x.type == discord.ActivityType.playing, before.activities)
        )
        new_game_activities: list[discord.Game] = list(
            filter(lambda x: x.type == discord.ActivityType.playing, after.activities)
        )
        if not prior_game_activities and not new_game_activities:
            return
        if prior_game_activities and not new_game_activities:
            prior_game_activity = prior_game_activities[0]
            self.close_latest_activity(before, prior_game_activity)
            return
        if prior_game_activities and new_game_activities:
            prior_game_activity = prior_game_activities[0]
            new_game_activity = new_game_activities[0]
            if prior_game_activity.name == new_game_activity.name:
                return
            self.close_latest_activity(before, prior_game_activity)
            self.create_new_activity(before, new_game_activity)
            return
        if not prior_game_activities and new_game_activities:
            new_game_activity = new_game_activities[0]
            self.create_new_activity(before, new_game_activity)

    @staticmethod
    def create_new_activity(member, new_game_activity):
        logger.info(f'Starting new activity for {member.display_name} {new_game_activity.name}')
        gfd_database_helper.replenish_db()
        activity_game, created = ActivityGame.get_or_create(name=new_game_activity.name)
        activity_game_platform = None
        if new_game_activity.platform is not None:
            activity_game_platform, created = ActivityGamePlatform.get_or_create(name=new_game_activity.platform)
        activity = Activity.create(
            user_id=member.id,
            activity_game_id=activity_game.id,
            activity_game_platform_id=None if activity_game_platform is None else activity_game_platform.id,
            start_time=new_game_activity.start.timestamp(),
        )
        gfd_database_helper.release_db()
        return activity

    @staticmethod
    def close_latest_activity(member, game_activity):
        logger.info(f'Closing activity for {member.display_name} {game_activity.name}')
        gfd_database_helper.replenish_db()
        latest_activity: Activity = Activity.get_latest_by_user_id(member.id)
        if (
                latest_activity is None
                or latest_activity.activity_game.name != game_activity.name
                or latest_activity.end_time is not None
        ):
            logger.info(f'Creating shadow activity for {member.display_name} {game_activity.name}')
            activity: Activity = ActivityTracker.create_new_activity(member, game_activity)
            activity.end_time = datetime.datetime.now().timestamp()
            activity.save()
            return
        if (
                latest_activity is not None
                and latest_activity.end_time is None
                and latest_activity.activity_game.name == game_activity.name
        ):
            latest_activity.end_time = datetime.datetime.now().timestamp()
            latest_activity.save()
        gfd_database_helper.release_db()

    @staticmethod
    async def post_weekly_stats(message: discord.Message):
        last_week = datetime.datetime.now() - timedelta(days=7)
        query = ActivityTracker.get_activities_selection_query(last_week)
        gfd_database_helper.replenish_db()
        results = query.dicts()
        gfd_database_helper.release_db()
        if len(results) == 0:
            await message.reply('No stats for this week yet')
            return
        stats_text = 'Y\'all played a lot of games this week!\n\n'
        stats_text += ActivityTracker.create_games_stats_text(results)
        await message.reply(stats_text)

    @staticmethod
    async def post_daily_stats(message: discord.Message):
        today = datetime.datetime.now() - timedelta(days=1)
        query = ActivityTracker.get_activities_selection_query(today)
        gfd_database_helper.replenish_db()
        results = query.dicts()
        gfd_database_helper.release_db()
        if len(results) == 0:
            await message.reply('No stats for this day yet')
            return
        stats_text = 'Y\'all played a lot of games today!\n\n'
        stats_text += ActivityTracker.create_games_stats_text(results)
        await message.reply(stats_text)

    @staticmethod
    def get_activities_selection_query(last_week):
        query = (
            Activity
            .select(
                ActivityGame.name,
                fn.SUM(Activity.end_time - Activity.start_time).alias('total_time')
            )
            .join(ActivityGame, on=(Activity.activity_game_id == ActivityGame.id))
            .where(
                (Activity.end_time.is_null(False))
                & (Activity.start_time >= last_week)
                & ((Activity.end_time - Activity.start_time) >= 60)
            )
            .group_by(Activity.activity_game_id)
            .order_by(fn.SUM(Activity.end_time - Activity.start_time).desc())
        )

        return query

    @staticmethod
    def create_games_stats_text(results):
        stats_text = ''
        for result in results:
            duration = result["total_time"]
            hours, remainder = divmod(duration, 3600)
            minutes = remainder // 60
            stats_text += f'**{result["name"]}**: {int(hours)}h {int(minutes)}m\n'
        return stats_text
