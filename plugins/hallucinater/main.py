import asyncio
import datetime
import io
import random
import re
from typing import Optional

import discord
from google import genai
from google.genai import types as gtypes

from helpers.message_utils import mention_no_one, escape_discord_identifiers, get_image_attachment_count
from logger import logger
from plugins.base import BasePlugin


class Hallucinater(BasePlugin):
    ask_later = 'Ask me again later!'

    def __init__(self, client, config):
        super().__init__(client, config)
        self.gen_ai_client = genai.Client(api_key=config.get('GEMINI_KEY'))
        self.rate_limiter = {}
        self.img_gen_winner: Optional[int] = None
        self.img_gen_lottery_channel: Optional[discord.TextChannel] = None
        self.img_gen_lottery_ignore_ids = []
        self.img_gen_lottery_ignore_ids = list(
            map(lambda x: int(x), filter(None, self.config.get('IMAGE_GEN_LOTTERY_IGNORE_IDS', '').split(',')))
        )
        self.img_gen_lottery_hour = int(self.config.get('IMAGE_GEN_LOTTERY_HOUR', 20))
        self.img_gen_busy = False

    def on_ready(self):
        if self.is_ready():
            return
        if 'IMAGE_GEN_LOTTERY_CHANNEL' not in self.config:
            return
        self.img_gen_lottery_channel = self.client.get_channel(int(self.config.get('IMAGE_GEN_LOTTERY_CHANNEL')))
        asyncio.create_task(self.run_image_gen_lottery())

    async def on_message(self, message: discord.Message):
        bot_nick_name = self.config.get('BOT_NICK_NAME')
        if message.content.lower().startswith('.genimg '):
            await self.respond_to_gen_img_prompt(message, message.content[8:])
            return
        if not message.content.lower().startswith(f'{bot_nick_name}, '):
            return
        user_prompt = re.sub(rf'^{bot_nick_name}, *', '', message.content, flags=re.IGNORECASE).strip()
        if user_prompt == '':
            await message.reply('I got nothing to say to that!')
            return
        user_id = message.author.id
        current_time = asyncio.get_running_loop().time()
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
        if self.img_gen_busy:
            return
        self.img_gen_busy = True
        if self.img_gen_winner is None:
            await message.reply('Wait for the next lottery ⏰')
            self.img_gen_busy = False
            return
        if self.img_gen_winner != message.author.id:
            await message.reply(
                'I\'m waiting for the real winner to respond!\n'
                'Identity theft is not a joke!'
            )
            self.img_gen_busy = False
            return
        if user_prompt == '':
            await message.reply('I need something to work with!')
            self.img_gen_busy = False
            return
        try:
            async with message.channel.typing():
                response = await self.gen_ai_client.aio.models.generate_images(
                    model='imagen-3.0-generate-002',
                    prompt=user_prompt,
                    config=gtypes.GenerateImagesConfig(
                        number_of_images=1,
                    )
                )
            if len(response.generated_images) < 1:
                await message.reply('Try something else later - I can\'t with this one!')
                return
            generated_image = response.generated_images[0]
            img_bytes = io.BytesIO()
            img_bytes.write(generated_image.image.image_bytes)
            img_bytes.seek(0)
            await message.reply(file=discord.File(img_bytes, 'image.png'))
            self.img_gen_winner = None
        except Exception as e:
            logger.error(str(e))
            await message.reply(self.ask_later)
        finally:
            self.img_gen_busy = False

    async def run_image_gen_lottery(self):
        while True:
            now = datetime.datetime.now()
            target_time = ((now + datetime.timedelta(days=1))
                           .replace(hour=self.img_gen_lottery_hour, minute=0, second=0, microsecond=0))
            delta_seconds = (target_time - now).total_seconds()
            try:
                members = [
                    member for member in self.img_gen_lottery_channel.members
                    if
                    not member.bot and member.id != self.client.user.id and member.id not in self.img_gen_lottery_ignore_ids
                ]
                if not members:
                    logger.info("No eligible members found in the channel for gen image lottery")
                else:
                    self.img_gen_winner = random.choice(members).id
                    logger.info(f"Image generation lottery winner: {self.img_gen_winner}")
                    await self.img_gen_lottery_channel.send(
                        f"Congratulations <@{self.img_gen_winner}>, you are the image generation lottery winner for today! 🎉\n"
                        "You can generate an image with the `.genimg` command!"
                    )
                logger.info(f'Sleeping for {delta_seconds} seconds until next gen image lottery')
                await asyncio.sleep(max(delta_seconds, 0))
                if self.img_gen_winner is not None:
                    logger.info(f'Image generation lottery lapsed')
                    img_gen_winner = self.img_gen_winner
                    self.img_gen_winner = None
                    await self.img_gen_lottery_channel.send(
                        f"<@{img_gen_winner}>, you didn't generate an image!"
                    )
            except Exception as e:
                logger.error(f"Error in run_image_gen_lottery: {str(e)}")
                await asyncio.sleep(max(delta_seconds, 0))
