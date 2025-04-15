import asyncio
import io
import json
import os
import random
import time
from typing import Optional

import discord
import numpy as np
from PIL import Image
from google import genai

from database.helper import gfd_database_helper
from database.models import User
from helpers.message_utils import mention_no_one
from helpers.single_worker_pool import QueueBasedWorker
from logger import logger
from plugins.base import BasePlugin


class WhosThatMonster(BasePlugin):
    filename = 'monster.png'

    def __init__(self, client, config):
        super().__init__(client, config)
        self.main_loop: Optional[asyncio.Task] = None
        self.current_monster: Optional[str] = None
        self.current_monster_file: Optional[str] = None
        self.current_monster_message: Optional[discord.Message] = None
        self.channel: Optional[discord.TextChannel] = None
        self.delay: int = 60
        self.queue_worker: Optional[QueueBasedWorker] = QueueBasedWorker()
        self.current_phrase_evaluations = {}
        if 'MONSTER_RELEASE_ON_DEMAND_USERS' in config:
            self.on_demand_release_users = list(
                map(lambda x: int(x), config['MONSTER_RELEASE_ON_DEMAND_USERS'].split(','))
            )
        else:
            self.on_demand_release_users = []
        self.gen_ai_client = genai.Client(api_key=config['GEMINI_KEY'])

    def on_ready(self):
        if self.is_ready():
            return
        if 'WHOS_THAT_MONSTER_CHANNEL' not in self.config:
            return
        if 'MONSTER_RELEASE_DELAY_MINUTES' not in self.config:
            return
        self.delay: int = int(self.config['MONSTER_RELEASE_DELAY_MINUTES'])
        self.channel = self.client.get_channel(int(self.config['WHOS_THAT_MONSTER_CHANNEL']))
        self.start_main_loop()

    def start_main_loop(self):
        self.main_loop = asyncio.get_event_loop().create_task(self.run())

    async def run(self):
        await self.queue_worker.start()
        await asyncio.sleep(self.delay * 60)
        while True:
            try:
                await self.post_monster()
                await asyncio.sleep(self.delay * 60)
                await self.reveal_monster()
            except Exception as e:
                logger.error(str(e))

    async def on_message(self, message: discord.Message):
        msg = message.content.lower()
        if message.channel.type == discord.ChannelType.private and msg == '.release-monster':
            if message.author.id in self.on_demand_release_users and not self.current_monster_message:
                await self.post_monster()
                self.main_loop.cancel()
                self.start_main_loop()
            return
        if msg == '.monsters':
            return await self.post_leaderboard()
        if msg == self.current_monster:
            gfd_database_helper.replenish_db()
            user = User.get_by_author(message.author)
            user.monsters_guessed += 1
            user.save()
            gfd_database_helper.release_db()
            await message.reply(content='Yes!', file=self.get_monster_file(self.current_monster_file))
            self.current_monster = None
            self.current_monster_message = None
            self.current_monster_file = None
            return
        if (message.reference is not None
                and self.current_monster_message is not None
                and message.reference.message_id == self.current_monster_message.id):
            await self.schedule_phrase_score_check(message)
            return

    async def schedule_phrase_score_check(self, message):
        author_id = message.author.id
        if author_id in self.current_phrase_evaluations \
                and time.time() - self.current_phrase_evaluations[author_id] < 5:
            await message.reply('No spamming!')
            return
        self.current_phrase_evaluations[author_id] = time.time()
        self.queue_worker.submit(self.gemini_processor, message, self.current_monster)

    async def gemini_processor(self, message: discord.Message, monster_name):
        prompt = (
            f"How apt is the caption \"{message.content}\" for the monster {monster_name} just by how it looks."
            "Do not consider its nature, biology or other details. Just the visual makeup."
            "Return a score out of 10 in the x/10 format only."
            "Be a little strict on the scoring if the caption is very short."
        )
        try:
            async with message.channel.typing():
                response = await self.gen_ai_client.aio.models.generate_content(
                    model="gemini-2.0-flash",
                    contents=[prompt],
                )
        except Exception as e:
            logger.error(str(e))
            await message.reply(f'I couldn\'t digest that one')
            return
        await message.reply(f'This description is a **{response.text.strip()}**!', allowed_mentions=mention_no_one)

    @staticmethod
    def get_image_bytes(image: Image) -> io.BytesIO:
        image_bytes = io.BytesIO()
        image.seek(0)
        image.save(image_bytes, format='PNG')
        image_bytes.seek(0)
        return image_bytes

    @staticmethod
    def get_monster_files_path():
        dir_path = os.path.realpath(os.path.dirname(__file__))
        return dir_path + '/../../resources/monsters/'

    def get_monster_file(self, monster_file) -> Optional[discord.File]:
        im = Image.open(os.path.join(self.get_monster_files_path(), monster_file))
        return discord.File(self.get_image_bytes(im), self.filename)

    def get_hidden_monster(self) -> discord.File:
        monsters_dir = self.get_monster_files_path()
        monster_files = os.listdir(monsters_dir)
        monster = random.choice(list(filter(lambda x: x.endswith('.png'), monster_files)))
        self.current_monster = monster[0:-4]
        self.current_monster_file = monster
        logger.info(f'Monster released {self.current_monster}')
        im = Image.open(os.path.join(monsters_dir, monster))
        data = np.array(im)
        red, green, blue, alpha = data.T
        filter_out_areas = (red >= 0) & (green >= 0) & (blue >= 0)
        data[..., :-1][filter_out_areas.T] = (65, 65, 65)
        im2 = Image.fromarray(data)
        return discord.File(self.get_image_bytes(im2), self.filename)

    async def post_monster(self):
        file = self.get_hidden_monster()
        message_parts = [
            'Who\'s that monster??',
        ]
        clues = self.get_clues()
        if clues:
            message_parts.append(f'Clues: {clues}')
        self.current_phrase_evaluations = {}
        await self.queue_worker.clear()
        self.current_monster_message = await self.channel.send(
            file=file,
            content="\n".join(message_parts)
        )

    async def reveal_monster(self):
        if self.current_monster is None:
            return
        await self.channel.send(
            content=f'It was {self.current_monster}!',
            file=self.get_monster_file(self.current_monster_file)
        )
        self.current_monster = None
        self.current_monster_file = None

    async def post_leaderboard(self):
        message_lines = [
            'Who\'s caught them all??',
            '',
        ]
        users = User.select().order_by(User.monsters_guessed.desc())
        for user in users:
            if user.user_id == self.client.user.id:
                continue
            message_lines.append(f'<@{user.user_id}>: {user.monsters_guessed}')
        await self.channel.send(content="\n".join(message_lines), allowed_mentions=discord.AllowedMentions(users=False))

    def get_clues(self):
        if not self.current_monster:
            return None
        monsters_dir = self.get_monster_files_path()
        clues_file = os.path.join(monsters_dir, 'clues.json')
        if not os.path.exists(clues_file):
            return None
        with open(clues_file, 'r') as f:
            clues = json.load(f)
            return clues[self.current_monster] if self.current_monster in clues else None
