import asyncio
import datetime
import random
import time
from random import randrange

import discord

from plugins.base import BasePlugin


class BannerRandomizer(BasePlugin):
    banner_source_channel: discord.TextChannel = None
    banner_from_epoch: int = None
    banner_update_frequency: int = 3600

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
        asyncio.get_event_loop().create_task(self.run())

    async def run(self):
        epoch_from = self.banner_from_epoch
        while True:
            search_date = datetime.datetime.fromtimestamp(randrange(epoch_from, int(time.time())))
            banner_set = False
            async for message in self.banner_source_channel.history(around=search_date):
                if len(message.attachments) < 1:
                    continue
                filtered_attachments = list(
                    filter(lambda x: x.content_type.startswith('image'), message.attachments)
                )
                while True:
                    if len(filtered_attachments) < 1:
                        break
                    if len(filtered_attachments) > 1:
                        attachment_index = random.randrange(0, len(filtered_attachments) - 1)
                    else:
                        attachment_index = 0
                    attachment: discord.Attachment = filtered_attachments.pop(attachment_index)
                    print("Setting banner to " + attachment.url)
                    try:
                        await self.client.guilds[0].edit(banner=await attachment.read())
                        banner_set = True
                        break
                    except Exception as e:
                        print('Failed to set banner', str(e))
                if banner_set:
                    break
            await asyncio.sleep(self.banner_update_frequency)
