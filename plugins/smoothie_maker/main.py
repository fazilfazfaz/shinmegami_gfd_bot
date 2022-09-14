import random

from plugins.base import BasePlugin


class SmoothieMaker(BasePlugin):
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
    self_smoothie_message_formats = [
        'Enjoy this {} 🥤',
        'Here have this {} 🥤',
        'How about a {} 🥤',
    ]
    dedicated_smoothie_message_formats = [
        'Hey <@{to}>, {_from} got you a {smoothie} 🥤',
        '<@{to}>, {_from} asked me to get you this {smoothie} 🥤',
        '<@{to}>, {_from} says hi. Oh and here, have this {smoothie} 🥤',
    ]
    herm_dedicated_smoothie_message_formats = [
        'Thanks {_from} for the {smoothie} 🥤',
        '{_from} is trying bulk me up',
        'I cant handle another smoothie right now {_from}',
    ]

    async def on_message(self, message):
        asked_for_personal_smoothie = message.content.lower() in ['.smoothie', '.smoothies']
        asked_for_smoothie_dedication = message.content.lower().startswith('.smoothie ')
        if asked_for_personal_smoothie or asked_for_smoothie_dedication:
            smoothie_name_parts = []
            smoothie_name_parts_options = self.smoothie_components.copy()
            for part in range(random.randint(2, 3)):
                smoothie_name_part = random.choice(smoothie_name_parts_options)
                smoothie_name_parts_options.remove(smoothie_name_part)
                smoothie_name_parts.append(smoothie_name_part)
            smoothie_name = " ".join(smoothie_name_parts)
            if asked_for_smoothie_dedication and len(message.mentions) > 0:
                if message.mentions[0].id == self.client.user.id:
                    dedicated_message_text = random.choice(self.herm_dedicated_smoothie_message_formats)
                    message_content = dedicated_message_text.format(_from=message.author.display_name,
                                                                    smoothie=smoothie_name)
                else:
                    dedicated_message_text = random.choice(self.dedicated_smoothie_message_formats)
                    message_content = dedicated_message_text.format(to=message.mentions[0].id,
                                                                    _from=message.author.display_name,
                                                                    smoothie=smoothie_name)
            elif asked_for_smoothie_dedication:
                target = message.content[10:]
                if target == '':
                    message_content = f'I made this {smoothie_name} 🥤\nBut I have nobody to give it to'
                else:
                    message_content = f'I made this {smoothie_name} 🥤\nNow who is this {target}?'
            else:
                message_content = random.choice(self.self_smoothie_message_formats).format(smoothie_name)
            await message.reply(content=message_content)
