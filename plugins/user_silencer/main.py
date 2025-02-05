import datetime
import random
import time

from logger import logger
from plugins.base import BasePlugin


class UserSilencer(BasePlugin):
    users_to_silence = []
    last_silence_times = {}

    def on_ready(self):
        if self.is_ready():
            return
        if 'USERS_TO_SILENCE' in self.config:
            self.users_to_silence += self.config['USERS_TO_SILENCE'].split(",")

    async def on_message(self, message):
        if str(message.author.id) in self.users_to_silence:
            await self.timeout_user(message)

    async def timeout_user(self, message):
        chance = random.randint(1, 1000)
        too_soon_to_silence = False
        if message.author.id in self.last_silence_times:
            if time.time() - self.last_silence_times[message.author.id] < 600:
                too_soon_to_silence = True
        if chance <= 2 and not too_soon_to_silence:
            logger.debug(f'We got {message.author.display_name}!')
            self.last_silence_times[message.author.id] = time.time()
            await message.author.timeout(datetime.timedelta(seconds=60))
            await message.reply("Oh no! you lost your mouth 😶")
        else:
            logger.debug(f'{message.author.display_name} got away with chance {chance}')
