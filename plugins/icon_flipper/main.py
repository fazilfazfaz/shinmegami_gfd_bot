import asyncio
import io
from random import randrange

import discord
from PIL import Image

from plugins.base import BasePlugin


class IconFlipper(BasePlugin):
    icon_flipper_hours_min: int
    icon_flipper_hours_max: int
    icon_flipper_minutes_min: int
    icon_flipper_minutes_max: int

    def on_ready(self):
        if self.is_ready():
            return
        if 'ICON_FLIPPER_HOURS_MIN' in self.config:
            self.icon_flipper_hours_min = int(self.config['ICON_FLIPPER_HOURS_MIN'])
        else:
            return
        if 'ICON_FLIPPER_HOURS_MAX' in self.config:
            self.icon_flipper_hours_max = int(self.config['ICON_FLIPPER_HOURS_MAX'])
        else:
            return
        if 'ICON_FLIPPED_MINUTES_MIN' in self.config:
            self.icon_flipper_minutes_min = int(self.config['ICON_FLIPPED_MINUTES_MIN'])
        else:
            return
        if 'ICON_FLIPPED_MINUTES_MAX' in self.config:
            self.icon_flipper_minutes_max = int(self.config['ICON_FLIPPED_MINUTES_MAX'])
        else:
            return
        asyncio.get_event_loop().create_task(self.run())

    async def run(self):
        while True:
            try:
                sleep_seconds = randrange(self.icon_flipper_hours_min, self.icon_flipper_hours_max) * 60 * 60
                print(f'Waiting f{sleep_seconds} to flip the image')
                await asyncio.sleep(sleep_seconds)
                icon_bytes = io.BytesIO()
                icon_bytes_flipped = io.BytesIO()
                guild: discord.Guild = self.client.guilds[0]
                await guild.icon.save(icon_bytes)
                icon_image = Image.open(icon_bytes)
                icon_image_flipped = icon_image.transpose(method=Image.Transpose.FLIP_LEFT_RIGHT)
                icon_image_flipped.save(icon_bytes_flipped, icon_image.format)
                icon_bytes_flipped.seek(0)
                await guild.edit(icon=icon_bytes_flipped.read())
                sleep_seconds = randrange(self.icon_flipper_minutes_min, self.icon_flipper_minutes_max) * 60
                print(f'Waiting f{sleep_seconds} to flip the image back')
                await asyncio.sleep(sleep_seconds)
            except Exception as e:
                print('Exception while sleeping for flipper', str(e))
                pass
