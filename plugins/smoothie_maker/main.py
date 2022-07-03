import random


class SmoothieMaker:
    client = None
    config = None
    smoothie_components = [
        'strawberry',
        'kiwi',
        'orange',
        'peanut-butter',
        'banana',
        'apple',
        'kale',
        'mango',
        'cherry',
        'peach',
        'blueberry',
        'citrus',
        'honey',
        'ginger',
        'vanilla',
        'chocolate',
        'pineapple',
        'papaya',
        'protein',
    ]
    message_prefixes = [
        'Enjoy this {} 🥤',
        'Here have this {} 🥤',
        'How about a {} 🥤',
    ]

    def __init__(self, client, config):
        self.client = client
        self.config = config

    async def on_message(self, message):
        if message.content.lower() in ['.smoothies', '.smoothie']:
            smoothie_name_parts = []
            smoothie_name_parts_options = self.smoothie_components.copy()
            for part in range(random.randint(2, 3)):
                smoothie_name_part = random.choice(smoothie_name_parts_options)
                smoothie_name_parts_options.remove(smoothie_name_part)
                smoothie_name_parts.append(smoothie_name_part)
            smoothie_name = " ".join(smoothie_name_parts)
            message_content = random.choice(self.message_prefixes).format(smoothie_name)
            await message.reply(content=message_content)
