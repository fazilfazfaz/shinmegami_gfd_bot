import asyncio
import datetime
import io
import random
import re

import discord
from google import genai
from google.genai import types as gtypes
from google.genai.errors import APIError

import database.helper
from database.models import GeneratedImageLog
from helpers.message_utils import mention_no_one, escape_discord_identifiers, get_image_attachment_count
from logger import logger
from plugins.base import BasePlugin


class RateLimit:
    MIN_INTERVAL = 60

    def __init__(self):
        self.start_time = asyncio.get_running_loop().time()
        self.count = 0

    def increment(self):
        self.count += 1

    def is_limit_reached(self, limit=3) -> bool:
        has_expired = (asyncio.get_running_loop().time() - self.start_time) > self.MIN_INTERVAL
        if has_expired:
            self.count = 0
            self.start_time = asyncio.get_running_loop().time()
            return False
        return self.count >= limit


class Hallucinater(BasePlugin):
    ask_later = 'Ask me again later!'

    def __init__(self, client, config):
        super().__init__(client, config)
        self.gen_ai_client = genai.Client(api_key=config.get('GEMINI_KEY'))
        self.rate_limiter: dict[int, RateLimit] = {}
        self.img_gen_count_max_per_month = int(self.config.get('IMG_GEN_COUNT_MAX_PER_MONTH', 100))
        self.bot_nick_name = self.config.get('BOT_NICK_NAME')
        self.ai_random_available = self.config.get('AI_RANDOM_AVAILABLE', 'false') == 'true'
        self.ai_random_available_from = None
        self.ai_random_available_to = None

    async def on_message(self, message: discord.Message):
        user_id = message.author.id
        self.rate_limiter.setdefault(user_id, RateLimit())
        if message.content.lower().startswith('.genimg '):
            if self.ai_random_available and not self.is_ai_available():
                await self.respond_ai_not_available(message)
                return
            if self.rate_limiter[user_id].is_limit_reached(2):
                await message.reply("Slow down!")
                return
            await self.respond_to_gen_img_prompt(message, message.content[8:])
            return
        if not message.content.lower().startswith(f'{self.bot_nick_name}, '):
            return
        if self.ai_random_available and not self.is_ai_available():
            await self.respond_ai_not_available(message)
            return
        user_prompt = re.sub(rf'^{self.bot_nick_name}, *', '', message.content, flags=re.IGNORECASE).strip()
        if user_prompt == '':
            await message.reply('I got nothing to say to that!')
            return
        limit = 30
        replied_to_message = None
        if message.reference is not None and isinstance(message.reference, discord.MessageReference):
            replied_to_message = await message.channel.fetch_message(message.reference.message_id)
            if get_image_attachment_count(replied_to_message) > 0:
                limit = 5
            else:
                await message.reply('I only look at pics')
                return
        if self.rate_limiter[user_id].is_limit_reached(limit):
            await message.reply("Slow down!")
            return
        await self.respond_to_prompt(message, replied_to_message, user_prompt)

    async def respond_to_prompt(self, message: discord.Message, replied_to_message: discord.Message, user_prompt):
        contents = []
        if replied_to_message is not None and len(replied_to_message.attachments) > 0:
            for attachment in replied_to_message.attachments:
                if not attachment.content_type.startswith('image/'):
                    continue
                img_bytes = await attachment.read()
                contents.append(gtypes.Part.from_bytes(data=img_bytes, mime_type=attachment.content_type))
        elif message.attachments:
            for attachment in message.attachments:
                if not attachment.content_type.startswith('image/'):
                    continue
                img_bytes = await attachment.read()
                contents.append(gtypes.Part.from_bytes(data=img_bytes, mime_type=attachment.content_type))
        contents.append(user_prompt)
        response_modalities = ['TEXT']
        database.helper.gfd_database_helper.replenish_db()
        total_generated_images = GeneratedImageLog.get_count()
        database.helper.gfd_database_helper.release_db()
        if total_generated_images < self.img_gen_count_max_per_month:
            response_modalities.append('IMAGE')
        try:
            async with message.channel.typing():
                response = await self.gen_ai_client.aio.models.generate_content(
                    model="models/gemini-2.5-flash-image",
                    contents=contents,
                    config=gtypes.GenerateContentConfig(
                        response_modalities=response_modalities,
                    )
                )
                texts = []
                files = []
                for part in response.candidates[0].content.parts:
                    if part.text is not None:
                        texts.append(part.text)
                    elif part.inline_data is not None:
                        img_bytes = io.BytesIO()
                        img_bytes.write(part.inline_data.data)
                        img_bytes.seek(0)
                        files.append(discord.File(img_bytes, 'generated_image.png'))
            if files:
                database.helper.gfd_database_helper.replenish_db()
                GeneratedImageLog.increment_count(len(files))
                database.helper.gfd_database_helper.release_db()
                texts.append(
                    f'Monthly image gen usage: {total_generated_images + len(files)}/{self.img_gen_count_max_per_month}'
                )
            await message.reply(
                escape_discord_identifiers("\n".join(texts)),
                files=files,
                allowed_mentions=mention_no_one
            )
            self.rate_limiter[message.author.id].increment()
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
                    model='imagen-4.0-generate-001',
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
            self.rate_limiter[message.author.id].increment()
        except APIError as e:
            logger.error(str(e))
            if e.code == 400:
                await message.reply('Naughty words in this one! Try rephrasing.')
                return
            await message.reply(self.ask_later)

    def is_ai_available(self):
        if self.ai_random_available_from is None or self.ai_random_available_to < datetime.datetime.now():
            available_after = random.randint(1, 2)
            self.ai_random_available_from = datetime.datetime.now() + datetime.timedelta(hours=available_after)
            self.ai_random_available_to = self.ai_random_available_from + datetime.timedelta(hours=1)
        return self.ai_random_available_from <= datetime.datetime.now() <= self.ai_random_available_to

    async def respond_ai_not_available(self, message: discord.Message):
        if message.content.lower().startswith('.genimg'):
            ai_random_disable_template = self.config.get('AI_RANDOM_DISABLE_TEMPLATE_IMG_GEN')
        else:
            ai_random_disable_template = self.config.get('AI_RANDOM_DISABLE_TEMPLATE_GENERAL')
        if ai_random_disable_template is None:
            return
        message_content = (
            ai_random_disable_template
            .replace('{TIME_FROM}', f'<t:{int(self.ai_random_available_from.timestamp())}:F>')
            .replace('{TIME_TO}', f'<t:{int(self.ai_random_available_to.timestamp())}:F>')
        )
        await message.reply(message_content)
