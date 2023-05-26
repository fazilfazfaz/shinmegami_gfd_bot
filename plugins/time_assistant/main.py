import datetime
import re

import dateparser
import discord
import pytz

from database.helper import GFDDatabaseHelper
from database.models import User
from plugins.base import BasePlugin


class TimeAssistant(BasePlugin):
    time_assist_channels = []
    pattern = re.compile(r'at (.*?) my time', re.IGNORECASE)

    def __init__(self, client, config):
        super().__init__(client, config)
        if 'TIME_ASSIST_CHANNELS' in self.config:
            self.time_assist_channels = self.config['TIME_ASSIST_CHANNELS'].split(',')

    async def on_message(self, message):
        if len(self.time_assist_channels) == 0 or str(message.channel.id) in self.time_assist_channels:
            await self.process_message(message)

    async def process_message(self, message: discord.Message):
        if message.content.startswith('.tz '):
            await self.config_timezone_for_user(message.author, message)
        else:
            m = self.pattern.search(message.content)
            if m is not None:
                await self.respond_with_utc_time(message, m.group(1))

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

    @staticmethod
    def parse_timezone(timezone_string):
        try:
            timezone = pytz.timezone(timezone_string)
            return timezone
        except pytz.UnknownTimeZoneError:
            return None

    @staticmethod
    async def respond_with_utc_time(message: discord.Message, time_string):
        GFDDatabaseHelper.replenish_db()
        user = User.get_by_author(message.author)
        GFDDatabaseHelper.release_db()
        if user.timezone is None:
            await message.reply('I don\'t know your timezone, set it with .tz <your timezone>')
            return
        parser_settings = {'TIMEZONE': user.timezone, 'RETURN_AS_TIMEZONE_AWARE': True}
        dt: datetime.datetime = dateparser.parse(time_string, settings=parser_settings)
        if dt is not None:
            print(user.timezone, int(dt.timestamp()))
            await message.reply(f'That\'s <t:{int(dt.timestamp())}:F>', mention_author=False)

    @staticmethod
    def get_timezone_suggestions(timezone_string: str):
        suggestions = []
        timezone_string_lower = timezone_string.lower()
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
