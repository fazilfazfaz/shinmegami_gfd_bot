class CommentHearter:
    auto_like_channels = ['support', 'check-this-out', 'food', 'purrfect-pets']
    client = None
    config = None

    def __init__(self, client, config):
        self.client = client
        self.config = config

    async def on_message(self, message):
        if message.channel.name in self.auto_like_channels:
            await self.like_message(message)

    async def like_message(self, message):
        if len(message.attachments) < 1:
            return
        print(f'Liking a message')
        await message.add_reaction('❤️')
