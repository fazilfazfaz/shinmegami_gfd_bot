import datetime
import re
import sqlite3

import dateparser
import discord
import pytz

from database.helper import gfd_database_helper
from database.models import User, db
from plugins.base import BasePlugin


class TimeZoneAlias:
    def __init__(self, alias_name, alias_shorthand, tz):
        self.tz = tz
        self.alias_shorthand = alias_shorthand
        self.alias_name = alias_name


class TimeAssistant(BasePlugin):
    time_assist_channels = []
    pattern = re.compile(r'(^| )at (.*?) my time', re.IGNORECASE)
    pattern_with_mention = re.compile(r'(^| )at (.*?) <@\d+> time', re.IGNORECASE)
    pattern_with_tz = re.compile(r'(^| )at (.*?) ([A-Za-z]+) time', re.IGNORECASE)
    timezone_aliases: dict[str, TimeZoneAlias] = {
        'Universal Herman Time': TimeZoneAlias('Universal Herman Time', 'UHT', 'America/New_York'),
        'Universal Cheese Time': TimeZoneAlias('Universal Cheese Time', 'UCT', 'Europe/Paris'),
        'Universal Mac Time': TimeZoneAlias('Universal Mac Time', 'UMT', 'Europe/Paris'),
    }

    def __init__(self, client, config):
        super().__init__(client, config)
        if 'TIME_ASSIST_CHANNELS' in self.config:
            self.time_assist_channels = self.config['TIME_ASSIST_CHANNELS'].split(',')

    async def on_message(self, message):
        if len(self.time_assist_channels) == 0 or str(message.channel.id) in self.time_assist_channels:
            await self.process_message(message)

    async def process_message(self, message: discord.Message):
        if message.content == '.tz':
            await self.show_timezone_for_user(message.author, message)
        elif message.content.startswith('.tz '):
            await self.config_timezone_for_user(message.author, message)
        elif message.content == '.clock':
            await self.print_users_clocks(message)
        else:
            m = self.pattern.search(message.content)
            if m is not None:
                await self.respond_with_utc_time(message, m.group(2))
                return
            m = self.pattern_with_mention.search(message.content)
            if m is not None:
                await self.respond_with_utc_time_for_other_user(message, m.group(2))
                return
            m = self.pattern_with_tz.search(message.content)
            if m is not None:
                await self.respond_with_utc_time_for_tz(message, m.group(2), m.group(3))

    async def config_timezone_for_user(self, author: discord.User, message: discord.Message):
        timezone_string = message.content[4:]
        timezone = self.parse_timezone(timezone_string)
        if timezone is None:
            # timezone not detected
            suggestions = self.get_timezone_suggestions(timezone_string)
            if len(suggestions) == 1:
                await self.set_timezone_for_user(message, author, suggestions[0])
            elif len(suggestions) == 0:
                await message.reply('I can\'t read this timezone!')
            else:
                suggestions_string = "\n".join(map(lambda x: f'\t{x}', suggestions))
                await message.reply(f'Did you mean one of: \n{suggestions_string}')
        else:
            await self.set_timezone_for_user(message, author, timezone_string)

    @classmethod
    async def show_timezone_for_user(cls, author: discord.User, message: discord.Message):
        gfd_database_helper.replenish_db()
        user = User.get_by_author(author)
        gfd_database_helper.release_db()
        if user.timezone is None:
            await cls.respond_to_message_with_tz_unknown_tip(message)
            return
        await message.reply(f'Your timezone is set to {user.timezone} 🕗')

    @classmethod
    def parse_timezone(cls, timezone_string):
        try:
            for alias_name, alias in cls.timezone_aliases.items():
                if alias.alias_name == timezone_string or alias.alias_shorthand == timezone_string:
                    return pytz.timezone(alias.tz)
            timezone = pytz.timezone(timezone_string)
            return timezone
        except pytz.UnknownTimeZoneError:
            return None

    @staticmethod
    async def respond_to_message_with_tz_unknown_tip(message):
        await message.reply('I don\'t know your timezone, set it with .tz <your timezone>')

    @staticmethod
    async def respond_to_message_with_tz_unknown_other_user_tip(message):
        await message.reply('I don\'t know their timezone')

    @classmethod
    async def respond_with_utc_time(cls, message: discord.Message, time_string):
        gfd_database_helper.replenish_db()
        user = User.get_by_author(message.author)
        gfd_database_helper.release_db()
        if user.timezone is None:
            await cls.respond_to_message_with_tz_unknown_tip(message)
            return
        resolved_timezone = user.timezone
        if user.timezone in cls.timezone_aliases:
            resolved_timezone = cls.timezone_aliases[user.timezone].tz
        await cls.parse_time_and_reply_to_message(message, resolved_timezone, time_string)

    @classmethod
    async def parse_time_and_reply_to_message(cls, message, resolved_timezone, time_string):
        parser_settings = {'TIMEZONE': resolved_timezone, 'RETURN_AS_TIMEZONE_AWARE': True}
        dt: datetime.datetime = dateparser.parse(time_string, settings=parser_settings)
        if dt is not None:
            await message.reply(f'That\'s <t:{int(dt.timestamp())}:F>', mention_author=False)

    async def respond_with_utc_time_for_other_user(self, message: discord.Message, time_string):
        if message.mentions[0].id == self.client.user.id:
            # they're asking for herm time
            await self.parse_time_and_reply_to_message(
                message,
                self.timezone_aliases['Universal Herman Time'].tz,
                time_string,
            )
            return
        gfd_database_helper.replenish_db()
        user = User.get_by_author(message.mentions[0])
        gfd_database_helper.release_db()
        if user.timezone is None:
            await self.respond_to_message_with_tz_unknown_other_user_tip(message)
            return
        resolved_timezone = user.timezone
        if user.timezone in self.timezone_aliases:
            resolved_timezone = self.timezone_aliases[user.timezone].tz
        await self.parse_time_and_reply_to_message(message, resolved_timezone, time_string)

    @classmethod
    async def respond_with_utc_time_for_tz(cls, message: discord.Message, time_string, time_zone_string):
        time_zone = cls.parse_timezone(time_zone_string)
        if time_zone is None:
            return
        await cls.parse_time_and_reply_to_message(message, time_zone.zone, time_string)

    @classmethod
    def get_timezone_suggestions(cls, timezone_string: str):
        suggestions = []
        timezone_string_lower = timezone_string.lower()
        alias_tz: TimeZoneAlias
        for alias_tz in cls.timezone_aliases.values():
            if timezone_string_lower in alias_tz.alias_name.lower() \
                    or timezone_string_lower in alias_tz.alias_shorthand.lower():
                suggestions.append(alias_tz.alias_name)
        for timezone in pytz.all_timezones:
            if timezone_string_lower in timezone.lower():
                suggestions.append(timezone)
        return suggestions[0:5]

    @staticmethod
    async def set_timezone_for_user(source_message: discord.Message, author: discord.User, timezone_string: str):
        gfd_database_helper.replenish_db()
        user = User.get_by_author(author)
        user.set_timezone(timezone_string)
        user.save()
        gfd_database_helper.release_db()
        await source_message.reply(f'Your timezone has been set to {timezone_string} 🕗')

    @classmethod
    async def print_users_clocks(cls, message: discord.Message):
        gfd_database_helper.replenish_db()
        res: sqlite3.Cursor = db.execute_sql(
            'SELECT user_id,timezone FROM user\n'
            'WHERE timezone IS NOT NULL'
        )
        rows = res.fetchall()
        gfd_database_helper.release_db()
        if len(rows) == 0:
            await message.reply(f'Nobody has configured timezones yet 🕗')
            return
        message_parts = [
            'Here\'s how the clock\'s looking for these peeps:'
        ]
        for row in rows:
            timezone = row[1]
            if timezone in cls.timezone_aliases:
                timezone = cls.timezone_aliases[timezone].tz
            tz = pytz.timezone(timezone)
            now_for_user = datetime.datetime.now(tz)
            formatted_time = now_for_user.strftime('%Y %B %d %I:%M %p')
            message_parts.append(f'<@{row[0]}>: **{formatted_time}**')
        message_parts.append('\n')
        message_parts.append('Set your timezone with `.tz` to appear here')
        message_parts.append('And remember, the clock\'s always ticking 🕗')
        await message.reply('\n'.join(message_parts), allowed_mentions=discord.AllowedMentions(users=False))
