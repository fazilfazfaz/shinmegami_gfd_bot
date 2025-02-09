import io

import discord
import numpy as np
from PIL import Image

from helpers.message_utils import get_image_attachment_count, mention_no_one
from logger import logger
from plugins.base import BasePlugin


class PixelCounter(BasePlugin):
    async def on_message(self, message: discord.Message):
        if message.reference is None or not isinstance(message.reference, discord.MessageReference):
            return
        if not message.content.lower().startswith('.pixels'):
            return
        replied_to_message = await message.channel.fetch_message(message.reference.message_id)
        if get_image_attachment_count(replied_to_message) < 1:
            await message.reply('I can only count pixels in images')
            return
        try:
            await self.count_pixels(message, replied_to_message)
        except Exception as e:
            logger.error(str(e))
            await message.reply('I cant math this one', allowed_mentions=mention_no_one)

    @staticmethod
    async def count_pixels(message, replied_to_message):
        detected_res = []
        async with message.channel.typing():
            for attachment in replied_to_message.attachments:
                if not attachment.content_type.startswith('image/'):
                    continue
                image_data = await attachment.read()
                img = Image.open(io.BytesIO(image_data))
                image_np = np.array(img)
                horizontal_res = []
                vertical_res = []
                for row in image_np:
                    changes = np.sum(np.any(row[:-1] != row[1:], axis=1))
                    horizontal_res.append(changes)
                image_transposed = np.transpose(image_np, (1, 0, 2))
                for y in range(img.height):
                    vertical_pixels = image_transposed[y]
                    changes = np.sum(np.any(vertical_pixels[:-1] != vertical_pixels[1:], axis=1))
                    vertical_res.append(changes)
                horizontal = int(np.floor(np.max(horizontal_res)))
                vertical = int(np.floor(np.max(vertical_res)))
                detected_res.append((horizontal, vertical, img.width, img.height,))
        text = 'Detected pixel counts:\n'
        for res in detected_res:
            text += f'**{res[0]}** x **{res[1]}** (Original **{res[2]}** x **{res[3]}**)\n'
        text += '\n*This might be completely wrong*'
        await message.reply(text, allowed_mentions=mention_no_one)
