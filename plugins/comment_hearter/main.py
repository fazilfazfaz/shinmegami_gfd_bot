class CommentHearter:
    auto_like_channels = []
    client = None
    config = None

    def __init__(self, client, config):
        self.client = client
        self.config = config
        self.auto_like_channels = config['HEART_CHANNELS'].split(',')

    async def on_message(self, message):
        if str(message.channel.id) in self.auto_like_channels:
            await self.like_message(message)

    async def like_message(self, message):
        if len(message.attachments) < 1:
            return
        print(f'Liking a message')
        await message.add_reaction('❤️')
