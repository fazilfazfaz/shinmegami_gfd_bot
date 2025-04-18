import asyncio
import datetime
import random
import time
from asyncio import Task
from random import randrange
from typing import Optional

import discord
import peewee

from database.helper import gfd_database_helper
from database.models import BannedBannerMessage
from logger import logger
from plugins.base import BasePlugin


class BannerRandomizer(BasePlugin):
    def __init__(self, client, config):
        super().__init__(client, config)
        self.banner_source_channel: Optional[discord.TextChannel] = None
        self.banner_from_epoch: Optional[int] = None
        self.banner_update_frequency: Optional[int] = 3600
        self.last_banner_message: Optional[discord.Message] = None
        self.last_banned_message: Optional[discord.Message] = None
        self.last_ban_time: Optional[int] = None
        self.banned_message_author_ids: set[int] = set([])
        self.run_task: Optional[Task] = None
        self.user_last_shuffle_time: dict[int, int] = {}
        self.banner_history: list = []

    def on_ready(self):
        if self.is_ready():
            return
        if 'BANNER_SOURCE_CHANNEL' in self.config:
            self.banner_source_channel = self.client.get_channel(int(self.config['BANNER_SOURCE_CHANNEL']))
        else:
            return
        if 'BANNER_FROM_EPOCH' in self.config:
            self.banner_from_epoch = int(self.config['BANNER_FROM_EPOCH'])
        else:
            return
        if 'BANNER_UPDATE_FREQUENCY' in self.config:
            self.banner_update_frequency = int(self.config['BANNER_UPDATE_FREQUENCY'])
        if 'BANNER_BANNED_MESSAGE_AUTHORS' in self.config:
            self.banned_message_author_ids = set(
                map(
                    lambda x: int(x), self.config['BANNER_BANNED_MESSAGE_AUTHORS'].split(',')
                )
            )
        self.start_runner()

    async def on_message(self, message: discord.Message):
        message_content_lower = message.content.lower()
        if message_content_lower == '.banner':
            if self.last_banner_message is None:
                return
            gfd_database_helper.replenish_db()
            try:
                BannedBannerMessage.create(message_id=self.last_banner_message.id)
            except peewee.PeeweeException:
                return
            finally:
                gfd_database_helper.release_db()
            self.last_banned_message = self.last_banner_message
            self.last_ban_time = time.time()
            logger.info("Banned banner message " + str(self.last_banner_message.id))
            self.banner_history.pop(0)
            self.restart_runner()
            await message.reply(
                f'Got it, banning ||{self.last_banner_message.jump_url}|| forever',
                suppress_embeds=True
            )
        elif message_content_lower == '.unbanner':
            if self.last_banned_message is None or time.time() - self.last_ban_time > 120:
                await message.reply('I barely knew her!')
                return
            gfd_database_helper.replenish_db()
            try:
                BannedBannerMessage.delete() \
                    .where(BannedBannerMessage.message_id == self.last_banned_message.id) \
                    .execute()
                await message.reply(f"{self.last_banned_message.jump_url} has been unbanned")
                self.last_ban_time = None
                self.last_banned_message = None
            finally:
                gfd_database_helper.release_db()
        elif message_content_lower == '.shuffle':
            current_timestamp = int(time.time())
            author_id = message.author.id
            if author_id in self.user_last_shuffle_time \
                    and current_timestamp - self.user_last_shuffle_time[author_id] < 300:
                await message.reply('You are too fast, slow down 🐢')
                return
            self.user_last_shuffle_time[author_id] = current_timestamp
            self.restart_runner()
            await message.reply('I\'ve jazzed it up 🎲')
        elif 'banner?' in message_content_lower:
            await message.reply(f'The banner is {self.last_banner_message.jump_url}')
        elif 'banners?' in message_content_lower:
            message_parts = ['These are the last 5 banners:']
            message_parts += self.banner_history
            await message.reply('\n'.join(message_parts))

    async def run(self):
        epoch_from = self.banner_from_epoch
        while True:
            search_date = datetime.datetime.fromtimestamp(randrange(epoch_from, int(time.time())))
            banner_set = False
            async for message in self.banner_source_channel.history(around=search_date):
                if len(message.attachments) < 1:
                    continue
                if message.author.id in self.banned_message_author_ids:
                    continue
                filtered_attachments = list(
                    filter(lambda x: x.content_type.startswith('image'), message.attachments)
                )
                gfd_database_helper.replenish_db()
                banned_message = BannedBannerMessage.get_by_message_id(message.id)
                gfd_database_helper.release_db()
                if banned_message is not None:
                    continue
                while True:
                    if len(filtered_attachments) < 1:
                        break
                    if len(filtered_attachments) > 1:
                        attachment_index = random.randrange(0, len(filtered_attachments) - 1)
                    else:
                        attachment_index = 0
                    attachment: discord.Attachment = filtered_attachments.pop(attachment_index)
                    logger.debug("Setting banner to " + attachment.url)
                    try:
                        await self.client.guilds[0].edit(banner=await attachment.read())
                        banner_set = True
                        self.last_banner_message = message
                        self.banner_history.insert(0, attachment.url)
                        self.banner_history = self.banner_history[0:5]
                        break
                    except Exception as e:
                        logger.error('Failed to set banner, ' + str(e))
                if banner_set:
                    break
            await asyncio.sleep(self.banner_update_frequency)

    def start_runner(self):
        self.run_task = asyncio.get_event_loop().create_task(self.run())

    def restart_runner(self):
        self.run_task.cancel()
        self.start_runner()
