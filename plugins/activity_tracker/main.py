import copy
import datetime
from datetime import timedelta

import discord
from peewee import fn, JOIN

from database.helper import gfd_database_helper
from database.models import Activity, ActivityGame, ActivityGamePlatform
from logger import logger
from plugins.base import BasePlugin

NVIDIA_GEFORCE_ID_APP_ID = 481331590383796224


class ActivityTracker(BasePlugin):

    def on_ready(self):
        if self.is_ready():
            return

    async def on_message(self, message: discord.Message):
        if message.content.lower() == '.games':
            await self.post_weekly_stats(message)
            return
        if message.content.lower() == '.games-daily':
            await self.post_daily_stats(message)
            return
        if message.content.startswith('.game '):
            await self.post_per_user_stats_for_game(message)
            return
        if message.content.startswith('.game-replay'):
            await self.post_game_replay(message)
            return

    async def presence_update(self, before: discord.Member, after: discord.Member):
        prior_game_activities = self.get_activities_filtered(before.activities)
        new_game_activities = self.get_activities_filtered(after.activities)
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
        start_time = (
            new_game_activity.start.timestamp()
            if new_game_activity.start
            else datetime.datetime.now().timestamp()
        )
        activity = Activity.create(
            user_id=member.id,
            activity_game_id=activity_game.id,
            activity_game_platform_id=None if activity_game_platform is None else activity_game_platform.id,
            start_time=start_time,
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
        header = 'Y\'all played a lot of games this week!\n\n'
        pages = ActivityTracker.create_games_stats_text(results)
        if not pages:
            await message.reply('No stats for this week yet')
            return
        num_pages = len(pages)
        await message.reply(f"{header}Page 1/{num_pages}\n\n{pages[0]}")
        for i, page in enumerate(pages[1:], start=2):
            await message.channel.send(f"Page {i}/{num_pages}\n\n{page}")

    @staticmethod
    async def post_daily_stats(message: discord.Message):
        today = datetime.datetime.now() - timedelta(days=1)
        query = ActivityTracker.get_activities_selection_query(today)
        gfd_database_helper.replenish_db()
        results = query.dicts()
        gfd_database_helper.release_db()
        header = 'Y\'all played a lot of games today!\n\n'
        pages = ActivityTracker.create_games_stats_text(results)
        if not pages:
            await message.reply('No stats for this day yet')
            return
        num_pages = len(pages)
        await message.reply(f"{header}Page 1/{num_pages}\n\n{pages[0]}")
        for i, page in enumerate(pages[1:], start=2):
            await message.channel.send(f"Page {i}/{num_pages}\n\n{page}")

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
        pages = []
        current_page = ""
        current_platform = None
        character_limit = 1800  # Leave room for headers from calling methods

        for result in results:
            lines_for_entry = []
            platform_changed = False

            if 'platform_name' in result:
                platform = result.get("platform_name") or "desktop"
                if platform and platform != current_platform:
                    platform_changed = True
                    if current_platform:
                        lines_for_entry.append(f'\n\n')
                    lines_for_entry.append(f'**Platform: {platform}**\n')
                    current_platform = platform

            duration = result["total_time"]
            hours, remainder = divmod(duration, 3600)
            minutes = remainder // 60
            lines_for_entry.append(f'**{result["name"]}**: {int(hours)}h {int(minutes)}m\n')

            entry_text = "".join(lines_for_entry)

            if len(current_page) + len(entry_text) > character_limit and current_page:
                pages.append(current_page)
                # start a new page
                if not platform_changed and current_platform:
                    current_page = f'**Platform: {current_platform} (continued)**\n' + lines_for_entry[-1]
                else:
                    current_page = entry_text
            else:
                current_page += entry_text

        if current_page:
            pages.append(current_page)

        return pages

    @staticmethod
    async def post_per_user_stats_for_game(message):
        game_name = message.content[6:].strip()
        if game_name == '':
            await message.reply('A game name must be specified!')
            return
        if len(game_name) < 3:
            await message.reply('Game name must be at least 3 characters long!')
            return
        query = (
            Activity
            .select(
                Activity.user_id,
                ActivityGame.name,
                fn.SUM(Activity.end_time - Activity.start_time).alias('total_time')
            )
            .join(ActivityGame, on=(Activity.activity_game_id == ActivityGame.id))
            .where(
                (Activity.end_time.is_null(False))
                & ((Activity.end_time - Activity.start_time) >= 60)
                & (ActivityGame.name ** f'%{game_name}%')
            )
            .group_by(Activity.user_id, Activity.activity_game_id)
            .order_by(Activity.activity_game_id, fn.SUM(Activity.end_time - Activity.start_time).desc())
        )
        gfd_database_helper.replenish_db()
        results = query.dicts()
        gfd_database_helper.release_db()
        if len(results) == 0:
            await message.reply(f'I did not find anything for **{game_name}**!')
            return
        text = ''
        last_game = None
        for result in results:
            game_name = result['name']
            user_id = result['user_id']
            duration = result['total_time']
            hours, remainder = divmod(duration, 3600)
            minutes = remainder // 60
            if last_game != game_name:
                if last_game is not None:
                    text += '\n'
                last_game = game_name
                text += f'**{game_name}**:\n'
            text += f'<@{user_id}>: {int(hours)}h {int(minutes)}m\n'

        await message.reply(text, allowed_mentions=discord.AllowedMentions(users=False))

    @staticmethod
    async def post_game_replay(message: discord.Message):
        target_user = message.author
        if message.mentions:
            target_user = message.mentions[0]
        current_date = datetime.datetime.now()
        year_to_check = current_date.year - 1

        start_of_year = datetime.datetime(year_to_check, 1, 1)
        end_of_year = datetime.datetime(year_to_check, 12, 31, 23, 59, 59)

        query = (
            Activity
            .select(
                ActivityGame.name,
                ActivityGamePlatform.name.alias('platform_name'),
                fn.SUM(Activity.end_time - Activity.start_time).alias('total_time')
            )
            .join(ActivityGame, on=(Activity.activity_game_id == ActivityGame.id))
            .join(
                ActivityGamePlatform,
                join_type=JOIN.LEFT_OUTER,
                on=(Activity.activity_game_platform_id == ActivityGamePlatform.id)
            )
            .where(
                (Activity.user_id == target_user.id)
                & (Activity.end_time.is_null(False))
                & (Activity.start_time >= start_of_year.timestamp())
                & (Activity.start_time <= end_of_year.timestamp())
                & ((Activity.end_time - Activity.start_time) >= 60)
            )
            .group_by(ActivityGame.name, ActivityGamePlatform.name)
            .order_by(ActivityGamePlatform.name.asc(nulls='FIRST'),
                      fn.SUM(Activity.end_time - Activity.start_time).desc())
        )

        gfd_database_helper.replenish_db()
        results = query.dicts()
        gfd_database_helper.release_db()

        header = f'🎮Here is the gaming replay for <@{target_user.id}> for {year_to_check}:\n\n'
        pages = ActivityTracker.create_games_stats_text(results)

        if not pages:
            if target_user == message.author:
                await message.reply(f'You have no games played in {year_to_check}!')
            else:
                await message.reply(f'{target_user.display_name} has no games played in {year_to_check}!')
            return

        num_pages = len(pages)
        await message.reply(f"{header}Page 1/{num_pages}\n\n{pages[0]}",
                            allowed_mentions=discord.AllowedMentions(users=False))
        for i, page in enumerate(pages[1:], start=2):
            await message.channel.send(f"Page {i}/{num_pages}\n\n{page}")

    @staticmethod
    def get_activities_filtered(activities):
        geforce_event = None

        for a in activities:
            if a.type != discord.ActivityType.playing:
                continue

            app_id = getattr(a, "application_id", None)
            if app_id == NVIDIA_GEFORCE_ID_APP_ID:
                details = getattr(a, "details", None)
                if details and details.startswith("Playing "):
                    geforce_event = a
                continue

            if a.name != "NVIDIA GeForce NOW":
                return [a]

        if geforce_event:
            cloned = copy.copy(geforce_event)
            cloned.name = geforce_event.details[8:]
            return [cloned]

        return []
