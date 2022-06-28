import asyncio
import random
import time

import math

from database.helper import GFDDatabaseHelper
from database.models import User


class DuckHuntGame:
    client = None
    config = None
    current_duck_channel = None
    last_duck_spawn_time = 0
    last_duck_message = None

    befriend_miss_messages = ["The duck didn't want to be friends, maybe next time.",
                              "Well this is awkward, the duck needs to think about it.",
                              "The duck said no, maybe bribe it with some pizza? Ducks love pizza don't they?",
                              "Who knew ducks could be so picky?"]

    kill_miss_messages = ["WHOOSH! You missed the duck completely!", "Your gun jammed!", "Better luck next time.",
                          "WTF!? Who are you Dick Cheney?"]

    def __init__(self, client, config):
        self.client = client
        self.config = config

        asyncio.get_event_loop().create_task(self.duck_spawner())

    async def on_message(self, message):
        if message.content in ['.fam']:
            await self.print_duck_family_or_pgtips_gif(message)
        elif message.content in ['.duckstats', '.dickstats', '.duckstat']:
            await self.print_duck_statistics(message.channel)
        elif message.content in ['.bef', '.befriend', '!bef', '🍕']:
            if not self.is_duck_catchable(message.channel):
                return await self.post_no_duck_message(message.channel, 'befriend')
            elif self.should_miss_attempt():
                return await self.post_duck_miss_message(message, 'befriend')
            await self.befriend_duck_for_user(message)
        elif message.content in ['.bang', '.kill', '.bang', '.shoot', '🔫']:
            if not self.is_duck_catchable(message.channel):
                return await self.post_no_duck_message(message.channel, 'kill')
            elif self.should_miss_attempt():
                return await self.post_duck_miss_message(message, 'kill')
            await self.kill_duck_for_user(message)

    async def duck_spawner(self):
        while True:
            seconds_since_last_duck = time.time() - self.last_duck_spawn_time
            been_less_than_an_hour = seconds_since_last_duck <= 3600
            if self.current_duck_channel is not None and been_less_than_an_hour:
                await asyncio.sleep(5)
                continue
            if self.current_duck_channel is not None and not been_less_than_an_hour:
                await self.last_duck_message.delete()
                await self.release_a_duck()
            else:
                minutes_to_sleep = random.randint(40, 60) * 60
                print(f'Duck to be released after {minutes_to_sleep}')
                await asyncio.sleep(minutes_to_sleep)
                await self.release_a_duck()

    async def befriend_duck_for_user(self, message):
        self.current_duck_channel = None
        time_to_befriend = math.floor(time.time() - self.last_duck_spawn_time)
        GFDDatabaseHelper.replenish_db()
        user = User.get_by_message(message)
        user.add_duck_friend()
        GFDDatabaseHelper.release_db()
        message_parts = [
            '<@{}> You befriended a duck in {} seconds!'.format(message.author.id, time_to_befriend),
            'You now have {} lil duckie friends.'.format(user.ducks_befriended)
        ]
        response_message = '\n'.join(message_parts)
        await message.channel.send(response_message)

    async def kill_duck_for_user(self, message):
        self.current_duck_channel = None
        time_to_befriend = math.floor(time.time() - self.last_duck_spawn_time)
        GFDDatabaseHelper.replenish_db()
        user = User.get_by_message(message)
        user.add_duck_kill()
        GFDDatabaseHelper.release_db()
        message_parts = [
            '<@{}> You shot a duck in {} seconds!'.format(message.author.id, time_to_befriend),
            'You have shot {} lil ducks.'.format(user.ducks_befriended)
        ]
        response_message = '\n'.join(message_parts)
        await message.channel.send(response_message)

    async def print_duck_statistics(self, channel):
        GFDDatabaseHelper.replenish_db()
        befriended_ducks_map = {}
        killed_ducks_map = {}
        for user in User.select():
            befriended_ducks_map[user.user_id] = user.ducks_befriended
            killed_ducks_map[user.user_id] = user.ducks_killed
        GFDDatabaseHelper.release_db()
        ducks_users = []
        for member in channel.members:
            if self.client.user.id == member.id:
                continue
            bef_count = befriended_ducks_map[member.id] if member.id in befriended_ducks_map else 0
            kill_count = killed_ducks_map[member.id] if member.id in befriended_ducks_map else 0
            ducks_users.append(f'**{member.display_name}**: {bef_count} befriended & {kill_count} shot')
        await channel.send("\n".join(ducks_users))

    def should_miss_attempt(self):
        chance = self.calculate_hit_chance()
        if not random.random() <= chance and chance > .05:
            return True
        return False

    def calculate_hit_chance(self):
        shoot_time = time.time()
        spawn_time = self.last_duck_spawn_time
        if shoot_time - spawn_time < 1:
            return .05
        elif 1 <= shoot_time - spawn_time <= 7:
            out = random.uniform(.60, .75)
            return out
        else:
            return 1

    async def post_duck_miss_message(self, message, type):
        if type == 'befriend':
            _message = random.choice(self.befriend_miss_messages)
        else:
            _message = random.choice(self.kill_miss_messages)
        await message.reply(_message)

    def is_duck_catchable(self, channel):
        return self.current_duck_channel == channel.id

    async def post_no_duck_message(self, channel, type):
        if type == 'befriend':
            await channel.send("You tried befriending a non-existent duck, that's hecking creepy.")
        else:
            await channel.send("There is no duck. What are you shooting at?")

    async def release_a_duck(self):
        channels_to_release_in = self.config['DUCK_CHANNELS'].split(',')
        channel_selected = random.choice(channels_to_release_in)
        channel = None
        for channel in self.client.guilds[0].channels:
            if channel.name == channel_selected:
                break

        if channel is None:
            return

        self.last_duck_message = await channel.send('A wild 🦆 has appeared!!')
        print(f'Released a new duck in {channel.name} with message {self.last_duck_message.id}')
        self.current_duck_channel = channel.id
        self.last_duck_spawn_time = time.time()

    async def print_duck_family_or_pgtips_gif(self, message):
        GFDDatabaseHelper.replenish_db()
        user = User.get_by_message(message)
        GFDDatabaseHelper.release_db()
        if user.ducks_killed > 0:
            message_parts = [
                'You\'ve shot ducks 😱',
                'No family for you!',
                'https://c.tenor.com/4aYkNoeULW4AAAAC/mokey-puppet-monkey.gif',
            ]
        elif user.ducks_befriended > 0:
            message_parts = [
                'Your duckie fam is here!',
                '🦆' * user.ducks_befriended,
            ]
        else:
            message_parts = [
                'You should meet more ducks',
                'https://c.tenor.com/qV4ycK5YEY8AAAAC/shrug-idk.gif',
            ]
        await message.reply("\n".join(message_parts))
