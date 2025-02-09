import os
import tempfile
from math import floor

import discord

from helpers.message_utils import mention_no_one, get_video_attachment_count
from logger import logger
from plugins.base import BasePlugin
from plugins.pixel_counter.video_pixel_counter import process_video


class PixelCounter(BasePlugin):
    async def on_message(self, message: discord.Message):
        if message.reference is None or not isinstance(message.reference, discord.MessageReference):
            return
        if not message.content.lower().startswith('.pixels'):
            return
        replied_to_message = await message.channel.fetch_message(message.reference.message_id)
        if get_video_attachment_count(replied_to_message) < 1:
            await message.reply('I can only count pixels in videos now')
            return
        try:
            await self.count_pixels(message, replied_to_message)
        except Exception as e:
            logger.error(str(e))
            await message.reply('I cant math this one', allowed_mentions=mention_no_one)

    @staticmethod
    async def count_pixels(message, replied_to_message: discord.Message):
        detected_res = []
        async with message.channel.typing():
            for attachment in replied_to_message.attachments:
                if attachment.content_type.startswith('video/'):
                    temp_file = tempfile.NamedTemporaryFile(delete=False)
                    try:
                        await attachment.save(temp_file.name)
                        results = await process_video(temp_file.name, max_frames=50)
                        temp_file.close()
                        os.unlink(temp_file.name)
                        detected_res.append(results)
                    except Exception as e:
                        logger.error(str(e))
        if len(detected_res) < 1:
            raise Exception('No results detected in videos')
        text = 'Detected pixel counts:\n'
        for res in detected_res:
            horizontal_avg = res['horizontal_avg']
            vertical_avg = res['vertical_avg']
            original_width = res['original_width']
            original_height = res['original_height']
            horizontal_percentage = res['horizontal_percentage']
            vertical_percentage = res['vertical_percentage']
            horizontal_percentage_4k = floor(res['horizontal_percentage'] * 3840 / 100)
            vertical_percentage_4k = floor(res['vertical_percentage'] * 2160 / 100)
            text += (
                f"**{horizontal_avg}** x **{vertical_avg}** "
                f"(Original **{original_width}** x **{original_height}**) "
                f"(Scale **{horizontal_percentage}%** x **{vertical_percentage}%**) "
                f"(Equivalent to **{horizontal_percentage_4k}** x **{vertical_percentage_4k}** at 4K)\n"
            )
        text += '\n*This might be completely wrong*'
        await message.reply(text, allowed_mentions=mention_no_one)
