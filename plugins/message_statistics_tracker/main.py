import asyncio
import re
from datetime import datetime, timezone, timedelta

import dateparser
import discord
from peewee import fn

from database.helper import gfd_message_stats_database_helper
from database.models import DailyMessageCount
from logger import logger
from plugins.base import BasePlugin


class MessageStatisticsDateFilter:
    def __init__(self, date_filter, title):
        self.date_filter = date_filter
        self.title = title


class MessageStatisticsTracker(BasePlugin):
    stats_collected: dict
    invalid_date_filter_command_reply = ('Command must be .messages-today, .messages-yesterday, .messages-week, '
                                         '.messages-month, .messages-year or .messages-date <date> or .messages-range <date> <date>')
    command_range_pattern = re.compile(r'^\.messages-(today|yesterday|week|month|year|date|range)')

    class DateFilterError(Exception):
        def __init__(self, message=None):
            super().__init__(message or MessageStatisticsTracker.invalid_date_filter_command_reply)

    class UnparseableDateFilterError(DateFilterError):
        def __init__(self, date_filter_str):
            super().__init__(f'Unparseable date: {date_filter_str}')

    def __init__(self, client: discord.Client, config: dict):
        super().__init__(client, config)
        self.stats_collected = {}

    def on_ready(self):
        if self.is_ready():
            return
        asyncio.get_event_loop().create_task(self.run())

    async def run(self):
        while True:
            try:
                await asyncio.sleep(30)
                copy = self.stats_collected.copy()
                self.stats_collected = {}
                if len(copy) > 0:
                    await self.process_stats_collected(copy)
            except Exception as e:
                logger.error(str(e))

    async def on_message_private(self, message: discord.Message):
        if message.content.lower() == '.messages-stats':
            await self.post_overall_stats(message)
            return
        if message.content.lower().startswith('.messages-'):
            await self.post_range_statistics(message)
            return

    async def on_message(self, message: discord.Message):
        if message.content.lower() == '.messages-stats':
            return
        if message.content.lower().startswith('.messages-'):
            return
        self.track_message(message)

    def track_message(self, message: discord.Message):
        msg_date = message.created_at.strftime('%Y-%m-%d')
        channel_key = (
            f"t{message.channel.id}" if isinstance(message.channel, discord.Thread) else str(message.channel.id)
        )
        if channel_key not in self.stats_collected:
            self.stats_collected[channel_key] = {}
        if msg_date not in self.stats_collected[channel_key]:
            self.stats_collected[channel_key][msg_date] = {}
        if message.author.id not in self.stats_collected[channel_key][msg_date]:
            self.stats_collected[channel_key][msg_date][message.author.id] = 0
        self.stats_collected[channel_key][msg_date][message.author.id] += 1

    async def post_range_statistics(self, message: discord.Message):
        if message.content.lower().endswith(' channels'):
            await self.post_range_statistics_for_channels(message)
            return
        if message.mentions:
            await MessageStatisticsTracker.post_range_statistics_for_users(message)
            return
        try:
            date_filter = MessageStatisticsTracker.get_message_range_filter(message)
        except MessageStatisticsTracker.DateFilterError as e:
            await message.reply(str(e))
            return
        data = (
            DailyMessageCount
            .select(DailyMessageCount.user_id, fn.SUM(DailyMessageCount.message_count).alias('total_messages'))
            .where(
                date_filter.date_filter
                & (DailyMessageCount.user_id != self.client.user.id)
            )
            .group_by(DailyMessageCount.user_id)
            .order_by(fn.SUM(DailyMessageCount.message_count).desc())
        )
        if not data.exists():
            await message.reply(f'No data to show :(')
            return
        stats_message = f"**Stats for {date_filter.title}:**\n"
        for record in data:
            user_mention = f"<@{record.user_id}>"
            stats_message += f"{user_mention}: {record.total_messages:,} messages\n"
        await message.reply(stats_message, allowed_mentions=discord.AllowedMentions(users=False))

    @staticmethod
    async def post_range_statistics_for_users(message: discord.Message):
        mentioned_users = [user.id for user in message.mentions]
        try:
            date_filter = MessageStatisticsTracker.get_message_range_filter(message)
        except MessageStatisticsTracker.DateFilterError as e:
            await message.reply(str(e))
            return
        stats_message = f"**Stats for {date_filter.title}:**\n"
        data = (
            DailyMessageCount
            .select(
                DailyMessageCount.user_id,
                DailyMessageCount.channel_id,
                DailyMessageCount.thread_id,
                fn.SUM(DailyMessageCount.message_count).alias('total_messages')
            )
            .where(
                (DailyMessageCount.user_id.in_(mentioned_users)) &
                date_filter.date_filter
            )
            .group_by(DailyMessageCount.user_id, DailyMessageCount.channel_id, DailyMessageCount.thread_id)
            .order_by(DailyMessageCount.user_id, fn.SUM(DailyMessageCount.message_count).desc())
        )

        if not data.exists():
            await message.reply("No data to show for the mentioned users :(",
                                allowed_mentions=discord.AllowedMentions(users=False))
            return

        current_user = None
        for record in data:
            if record.user_id != current_user:
                current_user = record.user_id
                if current_user is not None:
                    stats_message += "\n"
                stats_message += f"Stats for <@{current_user}>:\n"
            channel_mention = f"<#{record.thread_id or record.channel_id}>"
            stats_message += f"{channel_mention}: {record.total_messages:,} messages\n"

        await message.reply(stats_message, allowed_mentions=discord.AllowedMentions(users=False))

    async def post_range_statistics_for_channels(self, message: discord.Message):
        try:
            date_filter = MessageStatisticsTracker.get_message_range_filter(message)
        except MessageStatisticsTracker.DateFilterError as e:
            await message.reply(str(e))
            return
        stats_message = f"**Stats for {date_filter.title}:**\n"
        data = (
            DailyMessageCount
            .select(
                DailyMessageCount.channel_id,
                DailyMessageCount.thread_id,
                fn.SUM(DailyMessageCount.message_count).alias('total_messages')
            )
            .where(
                date_filter.date_filter
                & (DailyMessageCount.user_id != self.client.user.id)
            )
            .group_by(DailyMessageCount.channel_id, DailyMessageCount.thread_id)
            .order_by(fn.SUM(DailyMessageCount.message_count).desc())
        )

        if not data.exists():
            await message.reply("No data to show :(",
                                allowed_mentions=discord.AllowedMentions(users=False))
            return

        for record in data:
            channel_mention = f"<#{record.thread_id or record.channel_id}>"
            stats_message += f"{channel_mention}: {record.total_messages:,} messages\n"

        await message.reply(stats_message, allowed_mentions=discord.AllowedMentions(users=False))

    async def post_overall_stats(self, message):
        data = (
            DailyMessageCount
            .select(DailyMessageCount.user_id, fn.SUM(DailyMessageCount.message_count).alias('total_messages'))
            .group_by(DailyMessageCount.user_id)
            .order_by(fn.SUM(DailyMessageCount.message_count).desc())
        )

        if not data.exists():
            await message.reply('No data to show :(')
            return

        stats_message = "**Total message counts:**\n"
        total_messages = 0
        for record in data:
            user = self.client.guilds[0].get_member(record.user_id)
            if user is None:
                continue
            user_mention = f"<@{record.user_id}>"
            stats_message += f"{user_mention}: {record.total_messages:,} messages\n"
            total_messages += record.total_messages

        stats_message += f"\n**Total messages across all users:** {total_messages:,} messages"
        await message.reply(stats_message, allowed_mentions=discord.AllowedMentions(users=False))

    @staticmethod
    def get_message_range_filter(message: discord.Message):
        msg_lower = re.sub(r"<@!?(\d+)>|channels$", "", message.content.lower()).strip()
        message_range = MessageStatisticsTracker.command_range_pattern.match(msg_lower)
        if message_range is None:
            raise MessageStatisticsTracker.DateFilterError()
        message_range_type = message_range.group(1)
        if message_range_type == "today":
            return MessageStatisticsDateFilter(DailyMessageCount.date == datetime.now(timezone.utc).date(), "today")
        if message_range_type == "yesterday":
            return MessageStatisticsDateFilter(
                DailyMessageCount.date == (datetime.now(timezone.utc) - timedelta(days=1)).date(),
                "yesterday"
            )
        if message_range_type == "week":
            start_of_week = datetime.now(timezone.utc).date() - timedelta(days=datetime.now(timezone.utc).weekday())
            return MessageStatisticsDateFilter(DailyMessageCount.date >= start_of_week, "this week")
        if message_range_type == "month":
            start_of_month = datetime.now(timezone.utc).replace(day=1).date()
            return MessageStatisticsDateFilter(DailyMessageCount.date >= start_of_month, "this month")
        if message_range_type == "year":
            year_requested = re.search(r" ([1-9]\d\d\d)$", msg_lower)
            if year_requested:
                try:
                    year = int(year_requested.group(1))
                    start_of_year = datetime(year, 1, 1, tzinfo=timezone.utc)
                    end_of_year = datetime(year, 12, 31, tzinfo=timezone.utc)
                    return MessageStatisticsDateFilter(
                        (DailyMessageCount.date >= start_of_year.date()) &
                        (DailyMessageCount.date <= end_of_year.date()),
                        f"the year {year}"
                    )
                except ValueError:
                    raise MessageStatisticsTracker.UnparseableDateFilterError(year_requested)
            start_of_year = datetime.now(timezone.utc).replace(month=1, day=1).date()
            return MessageStatisticsDateFilter(DailyMessageCount.date >= start_of_year, "this year")
        if message_range_type == "date":
            date_filter_str = msg_lower[message_range.span()[1]:].strip()
            if not date_filter_str:
                raise MessageStatisticsTracker.DateFilterError(
                    'A date filter is required after the .messages-date command')
            parser_settings = {'TIMEZONE': 'UTC', 'RETURN_AS_TIMEZONE_AWARE': True}
            dt: datetime = dateparser.parse(date_filter_str, settings=parser_settings)
            if dt is None:
                raise MessageStatisticsTracker.UnparseableDateFilterError(date_filter_str)
            return MessageStatisticsDateFilter(DailyMessageCount.date == dt.date(), dt.strftime('%Y-%m-%d'))
        if message_range_type == "range":
            date_filter_str = msg_lower[message_range.span()[1]:].strip()
            date_parts = date_filter_str.split(sep=' ')
            if len(date_parts) != 2:
                raise MessageStatisticsTracker.DateFilterError(
                    'Two dates (from and to) in the format YYYY-MM-DD are required after the .messages-range command'
                )
            try:
                from_date = datetime.strptime(date_parts[0], '%Y-%m-%d').date()
                to_date = datetime.strptime(date_parts[1], '%Y-%m-%d').date()
            except ValueError:
                raise MessageStatisticsTracker.DateFilterError(
                    'Invalid date format. Please provide dates in the format YYYY-MM-DD.'
                )
            if from_date > to_date:
                raise MessageStatisticsTracker.DateFilterError('The from_date cannot be after the to_date.')
            return MessageStatisticsDateFilter(
                (DailyMessageCount.date >= from_date) & (DailyMessageCount.date <= to_date),
                f"range -> from {from_date} to {to_date}"
            )
        raise MessageStatisticsTracker.DateFilterError()

    @staticmethod
    async def process_stats_collected(stats_collected: dict):
        gfd_message_stats_database_helper.replenish_db()
        logger.info('Saving tracked message stats')
        for origin_id in stats_collected:
            if origin_id.startswith('t'):
                thread_id = origin_id[1:]
                channel_id = None
            else:
                channel_id = origin_id
                thread_id = None
            stats = stats_collected[origin_id]
            for day in stats:
                daily_stats = stats[day]
                for user_id in daily_stats:
                    DailyMessageCount.increment_message_count(
                        user_id=user_id,
                        channel_id=channel_id,
                        thread_id=thread_id,
                        date=datetime.strptime(day, '%Y-%m-%d'),
                        increment_count=daily_stats[user_id]
                    )
        gfd_message_stats_database_helper.release_db()
