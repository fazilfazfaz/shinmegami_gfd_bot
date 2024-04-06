import asyncio
import datetime
import io

import discord
from PIL import Image

from plugins.base import BasePlugin


class IconFlipper(BasePlugin):
    icon_flipper_hours_start: int
    icon_flipper_hours_end: int

    def on_ready(self):
        if self.is_ready():
            return
        if 'ICON_FLIPPER_HOURS_START' in self.config:
            self.icon_flipper_hours_start = int(self.config['ICON_FLIPPER_HOURS_START'])
        else:
            return
        if 'ICON_FLIPPER_HOURS_END' in self.config:
            self.icon_flipper_hours_end = int(self.config['ICON_FLIPPER_HOURS_END'])
        else:
            return
        asyncio.get_event_loop().create_task(self.run())

    async def run(self):
        while True:
            try:
                sleep_seconds = self.get_seconds_until_hour(self.icon_flipper_hours_start)
                print(f'Waiting {sleep_seconds} to flip the image')
                await asyncio.sleep(sleep_seconds)
                print('Flipping the channel icon')
                await self.flip_channel_icon()
                sleep_seconds = self.get_seconds_until_hour(self.icon_flipper_hours_end)
                print(f'Waiting {sleep_seconds} to flip the image back')
                await asyncio.sleep(sleep_seconds)
                print('Flipping the channel icon back')
                await self.flip_channel_icon()
            except Exception as e:
                print('Exception while sleeping for flipper', str(e))
                pass

    async def flip_channel_icon(self):
        icon_bytes = io.BytesIO()
        icon_bytes_flipped = io.BytesIO()
        guild: discord.Guild = self.client.guilds[0]
        await guild.icon.save(icon_bytes)
        icon_image = Image.open(icon_bytes)
        icon_image_flipped = icon_image.transpose(method=Image.Transpose.FLIP_LEFT_RIGHT)
        icon_image_flipped.save(icon_bytes_flipped, icon_image.format)
        icon_bytes_flipped.seek(0)
        await guild.edit(icon=icon_bytes_flipped.read())

    @staticmethod
    def get_seconds_until_hour(hour):
        now = datetime.datetime.now()
        day_delta = datetime.timedelta(hours=24)
        target_hour = now.replace(hour=hour, minute=0, second=0, microsecond=0)
        target_delta = day_delta - (now - target_hour)
        return target_delta.total_seconds() % (24 * 3600)
