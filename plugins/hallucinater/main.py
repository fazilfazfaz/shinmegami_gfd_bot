import asyncio
import io
import re

import discord
from google import genai
from google.genai import types as gtypes

import database.helper
from database.models import GeneratedImageLog
from helpers.message_utils import mention_no_one, escape_discord_identifiers, get_image_attachment_count
from logger import logger
from plugins.base import BasePlugin


class Hallucinater(BasePlugin):
    ask_later = 'Ask me again later!'

    def __init__(self, client, config):
        super().__init__(client, config)
        self.gen_ai_client = genai.Client(api_key=config.get('GEMINI_KEY'))
        self.rate_limiter = {}
        self.img_gen_count_max_per_month = int(self.config.get('IMG_GEN_COUNT_MAX_PER_MONTH', 100))
        self.bot_nick_name = self.config.get('BOT_NICK_NAME')

    async def on_message(self, message: discord.Message):
        current_time = asyncio.get_running_loop().time()
        user_id = message.author.id
        if message.content.lower().startswith('.genimg '):
            if user_id in self.rate_limiter and current_time < self.rate_limiter[user_id]:
                await message.reply("Slow down!")
                return
            self.rate_limiter[user_id] = current_time + 60
            await self.respond_to_gen_img_prompt(message, message.content[8:])
            return
        if not message.content.lower().startswith(f'{self.bot_nick_name}, '):
            return
        user_prompt = re.sub(rf'^{self.bot_nick_name}, *', '', message.content, flags=re.IGNORECASE).strip()
        if user_prompt == '':
            await message.reply('I got nothing to say to that!')
            return
        extension = 5
        replied_to_message = None
        if message.reference is not None and isinstance(message.reference, discord.MessageReference):
            replied_to_message = await message.channel.fetch_message(message.reference.message_id)
            if get_image_attachment_count(replied_to_message) > 0:
                extension = 30
            else:
                await message.reply('I only look at pics')
                return
        if user_id in self.rate_limiter and current_time < self.rate_limiter[user_id]:
            await message.reply("Slow down!")
            return
        self.rate_limiter[user_id] = current_time + extension
        await self.respond_to_prompt(message, replied_to_message, user_prompt)

    async def respond_to_prompt(self, message: discord.Message, replied_to_message: discord.Message, user_prompt):
        contents = []
        non_image_prompt = ('Respond to the prompt in the next line pretending to be a bot cat who is in to gaming.'
                            'Keep responses short and to the point.\n') + user_prompt
        if replied_to_message is not None and len(replied_to_message.attachments) > 0:
            for attachment in replied_to_message.attachments:
                if not attachment.content_type.startswith('image/'):
                    continue
                img_bytes = await attachment.read()
                contents.append(gtypes.Part.from_bytes(data=img_bytes, mime_type=attachment.content_type))
            contents.append(user_prompt)
        else:
            contents.append(non_image_prompt)
        try:
            async with message.channel.typing():
                response = await self.gen_ai_client.aio.models.generate_content(
                    model="gemini-2.0-flash",
                    contents=contents,
                )
            await message.reply(escape_discord_identifiers(response.text), allowed_mentions=mention_no_one)
        except Exception as e:
            logger.error(str(e))
            await message.reply(self.ask_later)
            return

    async def respond_to_gen_img_prompt(self, message, user_prompt):
        if user_prompt == '':
            await message.reply('I need something to work with!')
            return
        database.helper.gfd_database_helper.replenish_db()
        total_generated_images = GeneratedImageLog.get_count()
        database.helper.gfd_database_helper.release_db()
        if not total_generated_images < self.img_gen_count_max_per_month:
            await message.reply('Image generation limit reached for this month! Try again later.')
            return
        try:
            async with message.channel.typing():
                response = await self.gen_ai_client.aio.models.generate_images(
                    model='imagen-3.0-generate-002',
                    prompt=user_prompt,
                    config=gtypes.GenerateImagesConfig(
                        number_of_images=1,
                        output_mime_type='image/png',
                    )
                )
                if len(response.generated_images) < 1:
                    await message.reply('Try something else later - I can\'t with this one!')
                    return
                generated_image = response.generated_images[0]
                img_bytes = io.BytesIO()
                img_bytes.write(generated_image.image.image_bytes)
                img_bytes.seek(0)
                await message.reply(
                    content=f'Here you go! Monthly usage: {total_generated_images + 1}/{self.img_gen_count_max_per_month}',
                    file=discord.File(img_bytes, 'image.png')
                )
            database.helper.gfd_database_helper.replenish_db()
            GeneratedImageLog.increment_count()
            database.helper.gfd_database_helper.release_db()
        except Exception as e:
            logger.error(str(e))
            await message.reply(self.ask_later)
