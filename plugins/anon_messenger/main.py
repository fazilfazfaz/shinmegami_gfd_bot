from plugins.base import BasePlugin


class AnonMessenger(BasePlugin):

    def __init__(self, client, config):
        super().__init__(client, config)
        if 'ANON_MSG_CHANNEL' in self.config:
            self.anon_msg_channel_id = int(self.config['ANON_MSG_CHANNEL'])
        else:
            self.anon_msg_channel_id = None
        self.anon_msg_channel = None

    async def on_message(self, message):
        if not self.anon_msg_channel_id:
            return
        if not self.anon_msg_channel:
            self.anon_msg_channel = self.client.get_channel(self.anon_msg_channel_id)
        if not message.content.lower().startswith('.say '):
            return
        message_content = 'Somebody says:\n>>> ' + message.content[5:]
        await self.anon_msg_channel.send(message_content)
