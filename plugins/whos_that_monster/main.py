import asyncio
import io
import json
import os
import random
from typing import Optional

import discord
import numpy as np
from PIL import Image

from database.helper import gfd_database_helper
from database.models import User
from logger import logger
from plugins.base import BasePlugin


class WhosThatMonster(BasePlugin):
    filename = 'monster.png'

    def __init__(self, client, config):
        super().__init__(client, config)
        self.current_monster: Optional[str] = None
        self.current_monster_file: Optional[str] = None
        self.channel: Optional[discord.TextChannel] = None
        self.delay: int = 60

    def on_ready(self):
        if self.is_ready():
            return
        if 'WHOS_THAT_MONSTER_CHANNEL' not in self.config:
            return
        if 'MONSTER_RELEASE_DELAY_MINUTES' not in self.config:
            return
        self.delay: int = int(self.config['MONSTER_RELEASE_DELAY_MINUTES'])
        self.channel = self.client.get_channel(int(self.config['WHOS_THAT_MONSTER_CHANNEL']))
        asyncio.get_event_loop().create_task(self.run())

    async def run(self):
        while True:
            try:
                await self.post_monster()
                await asyncio.sleep(self.delay * 60)
                await self.reveal_monster()
            except Exception as e:
                logger.error(str(e))

    async def on_message(self, message: discord.Message):
        if message.content.lower() == '.monsters':
            return await self.post_leaderboard()
        if message.content.lower() == self.current_monster:
            gfd_database_helper.replenish_db()
            user = User.get_by_author(message.author)
            user.monsters_guessed += 1
            user.save()
            gfd_database_helper.release_db()
            await message.reply(content='Yes!', file=self.get_current_monster())

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

    def get_current_monster(self) -> discord.File:
        monsters_dir = self.get_monster_files_path()
        im = Image.open(os.path.join(monsters_dir, self.current_monster_file))
        return discord.File(self.get_image_bytes(im), self.filename)

    def get_hidden_monster(self) -> discord.File:
        monsters_dir = self.get_monster_files_path()
        monsters = os.listdir(monsters_dir)
        monster = random.choice(monsters)
        self.current_monster = monster[0:-4]
        self.current_monster_file = monster
        logger.info(f'Monster released {self.current_monster}')
        im = Image.open(os.path.join(monsters_dir, monster))
        data = np.array(im)
        red, green, blue, alpha = data.T
        white_areas = (red >= 0) & (green >= 0) & (blue >= 0)
        data[..., :-1][white_areas.T] = (65, 65, 65)
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
        await self.channel.send(
            file=file,
            content="\n".join(message_parts)
        )

    async def reveal_monster(self):
        if self.current_monster is None:
            return
        self.current_monster = None
        self.current_monster_file = None
        await self.channel.send(content=f'It was {self.current_monster}!', file=self.get_current_monster())

    async def post_leaderboard(self):
        message_lines = [
            'Who\'s caught them all??',
            '',
        ]
        users = User.select().order_by(User.monsters_guessed.desc())
        for user in users:
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
