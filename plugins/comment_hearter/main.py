from logger import logger
from plugins.base import BasePlugin


class CommentHearter(BasePlugin):
    auto_like_channels = []
    client = None
    config = None

    def on_ready(self):
        if self.is_ready():
            return
        if 'HEART_CHANNELS' in self.config:
            self.auto_like_channels = self.config['HEART_CHANNELS'].split(',')

    async def on_message(self, message):
        if str(message.channel.id) in self.auto_like_channels:
            await self.like_message(message)

    async def like_message(self, message):
        if len(message.attachments) < 1:
            return
        logger.debug(f'Liking a message')
        await message.add_reaction('❤️')
