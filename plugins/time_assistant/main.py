import datetime
import re

import dateparser
import discord
import pytz

from database.helper import GFDDatabaseHelper
from database.models import User
from plugins.base import BasePlugin


class TimeZoneAlias:
    def __init__(self, alias_name, alias_shorthand, tz):
        self.tz = tz
        self.alias_shorthand = alias_shorthand
        self.alias_name = alias_name


class TimeAssistant(BasePlugin):
    time_assist_channels = []
    pattern = re.compile(r'(^| )at (.*?) my time', re.IGNORECASE)
    timezone_aliases: dict[str, TimeZoneAlias] = {
        'Universal Herman Time': TimeZoneAlias('Universal Herman Time', 'UHT', 'America/New_York'),
        'Universal Cheese Time': TimeZoneAlias('Universal Cheese Time', 'UCT', 'Europe/Paris'),
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
        else:
            m = self.pattern.search(message.content)
            if m is not None:
                await self.respond_with_utc_time(message, m.group(2))

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
        GFDDatabaseHelper.replenish_db()
        user = User.get_by_author(author)
        GFDDatabaseHelper.release_db()
        if user.timezone is None:
            await cls.respond_to_message_with_tz_unknown_tip(message)
            return
        await message.reply(f'Your timezone is set to {user.timezone} 🕗')

    @classmethod
    def parse_timezone(cls, timezone_string):
        try:
            if timezone_string in cls.timezone_aliases:
                return pytz.timezone(cls.timezone_aliases[timezone_string].alias_name)
            timezone = pytz.timezone(timezone_string)
            return timezone
        except pytz.UnknownTimeZoneError:
            return None

    @staticmethod
    async def respond_to_message_with_tz_unknown_tip(message):
        message.reply('I don\'t know your timezone, set it with .tz <your timezone>')

    @classmethod
    async def respond_with_utc_time(cls, message: discord.Message, time_string):
        GFDDatabaseHelper.replenish_db()
        user = User.get_by_author(message.author)
        GFDDatabaseHelper.release_db()
        if user.timezone is None:
            await cls.respond_to_message_with_tz_unknown_tip(message)
            return
        resolved_timezone = user.timezone
        if user.timezone in cls.timezone_aliases:
            resolved_timezone = cls.timezone_aliases[user.timezone].tz
        parser_settings = {'TIMEZONE': resolved_timezone, 'RETURN_AS_TIMEZONE_AWARE': True}
        print(message.content, time_string, resolved_timezone)
        dt: datetime.datetime = dateparser.parse(time_string, settings=parser_settings)
        if dt is not None:
            print(dt.timestamp())
            await message.reply(f'That\'s <t:{int(dt.timestamp())}:F>', mention_author=False)

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
        GFDDatabaseHelper.replenish_db()
        user = User.get_by_author(author)
        user.set_timezone(timezone_string)
        user.save()
        GFDDatabaseHelper.release_db()
        await source_message.reply(f'Your timezone has been set to {timezone_string} 🕗')
