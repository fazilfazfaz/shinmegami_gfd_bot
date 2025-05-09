import asyncio
import math
import random
import secrets
import time

import discord

from database.helper import gfd_database_helper
from database.models import User, DuckAttemptLog
from logger import logger
from plugins.base import BasePlugin

MAX_USER_MISS_COUNT = 1

system_random_generator = secrets.SystemRandom()


class DuckHuntGame(BasePlugin):
    current_duck_channel = None
    last_duck_spawn_time = 0
    last_duck_message = None
    current_miss_count = {}
    message_counter = 0
    min_message_count = -1

    duck_stat_commands = ['.duckstats', '.dickstats', '.duckstat']
    duck_befriend_commands = ['.bef', '.befriend', '!bef', '🍕']
    duck_shoo_commands = [
        '.shoo', '.shoes', '.shoe', '.shue', '👞', '👟', '🥿', '👢', '🥾', ':booty:', '👠', '🩰',
        '👡', '🎿', '🩴', '⛸', '🛼'
    ]
    duck_kill_commands = ['.bang', '.kill', '.bang', '.shoot', '🔫']
    all_duck_commands = []

    befriend_miss_messages = ["The duck didn't want to be friends, maybe next time.",
                              "Well this is awkward, the duck needs to think about it.",
                              "The duck said no, maybe bribe it with some pizza? Ducks love pizza don't they?",
                              "Who knew ducks could be so picky?"]

    shoo_miss_messages = [
        "The duck paid no attention.", "That's one metal duck, wont work.",
        'Duck is here to stay this time, try again?',
    ]

    kill_miss_messages = ["WHOOSH! You missed the duck completely!", "Your gun jammed!", "Better luck next time.",
                          "WTF!? Who are you Dick Cheney?"]

    def __init__(self, client, config):
        super().__init__(client, config)
        if 'DUCK_REL_MSG_COUNT' not in self.config or 'DUCK_CHANNELS' not in self.config:
            raise Exception('DUCK_REL_MSG_COUNT env var not set')
        self.all_duck_commands = set(
            self.duck_stat_commands + self.duck_befriend_commands + self.duck_kill_commands + self.duck_shoo_commands
        )
        self.all_duck_commands.add('.fam')
        self.all_duck_commands.add('.graves')
        self.min_message_count = int(self.config['DUCK_REL_MSG_COUNT'])
        self.channels_to_release_in = self.config['DUCK_CHANNELS'].split(',')

    def on_ready(self):
        if self.is_ready():
            return

        # if 'DUCK_CHANNELS' in self.config:
        #     asyncio.get_event_loop().create_task(self.duck_spawner())

    async def on_message(self, message):
        lower_case_message = message.content.lower()
        if lower_case_message in self.all_duck_commands:
            user = self.get_duck_user_from_message_author(message.author)
            if lower_case_message == '.fam':
                await self.print_duck_family_or_pgtips_gif(message, user)
            elif lower_case_message == '.graves':
                await self.print_duck_graves(message, user)
            elif lower_case_message in self.duck_stat_commands:
                await self.print_duck_statistics(message.channel)
            elif lower_case_message in self.duck_befriend_commands:
                if not self.is_duck_catchable(message.channel):
                    return await self.post_no_duck_message(message, 'befriend')
                elif self.should_miss_attempt(user):
                    return await self.post_duck_miss_message(user, message, 'befriend')
                await self.befriend_duck_for_user(user, message)
            elif lower_case_message in self.duck_kill_commands:
                if not self.is_duck_catchable(message.channel):
                    return await self.post_no_duck_message(message, 'kill')
                elif self.should_miss_attempt(user):
                    return await self.post_duck_miss_message(user, message, 'kill')
                await self.kill_duck_for_user(user, message)
            elif lower_case_message in self.duck_shoo_commands:
                if not self.is_duck_catchable(message.channel):
                    return await self.post_no_duck_message(message, 'shoo')
                elif self.should_miss_attempt(user):
                    return await self.post_duck_miss_message(user, message, 'shoo')
                await self.shoo_duck_for_user(user, message)
            return
        if str(message.channel.id) not in self.channels_to_release_in:
            return
        self.message_counter += 1
        if self.message_counter >= self.min_message_count:
            self.message_counter = 0
            if self.current_duck_channel is not None:
                await self.last_duck_message.delete()
            await self.release_a_duck()

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
                minutes_to_sleep = random.randint(120, 140) * 60
                if 'DEV_MODE' in self.config and self.config['DEV_MODE'] == 'true':
                    minutes_to_sleep = 0
                logger.info(f'Duck to be released after {minutes_to_sleep}')
                await asyncio.sleep(minutes_to_sleep)
                await self.release_a_duck()

    async def befriend_duck_for_user(self, user, message):
        self.current_duck_channel = None
        time_to_befriend = math.floor(time.time() - self.last_duck_spawn_time)
        gfd_database_helper.replenish_db()
        user.add_duck_friend()
        gfd_database_helper.release_db()
        message_parts = [
            '<@{}> You befriended a duck in {} seconds!'.format(message.author.id, time_to_befriend),
            'You now have {} lil duckie friends.'.format(user.ducks_befriended)
        ]
        response_message = '\n'.join(message_parts)
        await message.channel.send(response_message)

    async def kill_duck_for_user(self, user, message):
        self.current_duck_channel = None
        time_to_befriend = math.floor(time.time() - self.last_duck_spawn_time)
        gfd_database_helper.replenish_db()
        user.add_duck_kill()
        gfd_database_helper.release_db()
        message_parts = [
            '<@{}> You shot a duck in {} seconds!'.format(message.author.id, time_to_befriend),
            'You have shot {} lil ducks.'.format(user.ducks_killed)
        ]
        response_message = '\n'.join(message_parts)
        await message.channel.send(response_message)

    async def shoo_duck_for_user(self, user, message):
        self.current_duck_channel = None
        time_to_shoo = math.floor(time.time() - self.last_duck_spawn_time)
        gfd_database_helper.replenish_db()
        user.add_duck_shoo()
        gfd_database_helper.release_db()
        message_parts = [
            '<@{}> You shooed a duck away in {} seconds!'.format(message.author.id, time_to_shoo),
            'Good luck, duck!'
        ]
        response_message = '\n'.join(message_parts)
        await message.channel.send(response_message)

    async def print_duck_statistics(self, channel):
        gfd_database_helper.replenish_db()
        befriended_ducks_map = {}
        killed_ducks_map = {}
        shooed_ducks_map = {}
        shooed_ducks_count = 0
        for user in User.select():
            befriended_ducks_map[user.user_id] = user.ducks_befriended
            killed_ducks_map[user.user_id] = user.ducks_killed
            shooed_ducks_map[user.user_id] = user.ducks_shooed
            shooed_ducks_count += user.ducks_shooed
        gfd_database_helper.release_db()
        ducks_users = []
        for member in channel.members:
            if self.client.user.id == member.id or member.bot:
                continue
            user_stats_parts = []
            if member.id in befriended_ducks_map and befriended_ducks_map[member.id] > 0:
                user_stats_parts.append(f'{befriended_ducks_map[member.id]} befriended')
            if member.id in killed_ducks_map and killed_ducks_map[member.id] > 0:
                user_stats_parts.append(f'{killed_ducks_map[member.id]} shot')
            if member.id in shooed_ducks_map and shooed_ducks_map[member.id] > 0:
                user_stats_parts.append(f'{shooed_ducks_map[member.id]} shooed')
            if len(user_stats_parts) == 0:
                continue
            ducks_users.append(f'**{member.display_name}**: {" & ".join(user_stats_parts)}')
        ducks_users.append("")
        ducks_users.append(f'A total of {shooed_ducks_count} ducks have been shooed away')
        await channel.send("\n".join(ducks_users))

    def should_miss_attempt(self, user):
        if user.user_id in self.current_miss_count:
            current_miss_count_for_user = self.current_miss_count[user.user_id]
            if current_miss_count_for_user >= MAX_USER_MISS_COUNT:
                return False
        else:
            current_miss_count_for_user = 0
        chance = self.calculate_hit_chance(user)
        randomval = system_random_generator.random()
        logger.debug(f'Random value: {randomval} chance: {chance}')
        gfd_database_helper.replenish_db()
        if not randomval <= chance:
            self.current_miss_count[user.user_id] = current_miss_count_for_user + 1
            DuckAttemptLog.create_attempt(user.user_id, chance, randomval, True)
            gfd_database_helper.release_db()
            return True
        DuckAttemptLog.create_attempt(user.user_id, chance, randomval, False)
        gfd_database_helper.release_db()
        return False

    def get_duck_user_from_message_author(self, author):
        gfd_database_helper.replenish_db()
        user = User.get_by_author(author)
        gfd_database_helper.release_db()
        return user

    def calculate_hit_chance(self, user):
        shoot_time = time.time()
        spawn_time = self.last_duck_spawn_time
        logger.debug(f'Shooting delay {shoot_time - spawn_time}')
        logger.debug(f'User has repented: {user.has_repented_for_shooting_ducks()}')
        if 1 <= shoot_time - spawn_time <= 10 or not user.has_repented_for_shooting_ducks():
            out = system_random_generator.uniform(.65, .80)
            return out
        else:
            return 1

    async def post_duck_miss_message(self, user, message, action_type):
        if action_type == 'befriend':
            _message = random.choice(self.befriend_miss_messages)
        elif action_type == 'shoo':
            _message = random.choice(self.shoo_miss_messages)
        else:
            _message = random.choice(self.kill_miss_messages)
        await message.reply(_message)

    def is_duck_catchable(self, channel):
        logger.debug(f'Checking for duck: {self.current_duck_channel} {self.last_duck_message} {channel.id}')
        return self.current_duck_channel is not None and \
               self.last_duck_message is not None and \
               self.last_duck_message.channel.id == channel.id

    async def post_no_duck_message(self, message, action_type):
        if action_type == 'befriend':
            await message.reply("You tried befriending a non-existent duck, that's hecking creepy.")
        elif action_type == 'shoo':
            await message.reply("You tried shooing away a non-existent duck, that's such shoe.")
        else:
            await message.reply("There is no duck. What are you shooting at?")

    async def release_a_duck(self):
        channel_selected = random.choice(self.channels_to_release_in)
        channel = None
        for channel in self.client.guilds[0].channels:
            if str(channel.id) == channel_selected:
                break

        if channel is None:
            return

        self.current_miss_count = {}
        self.last_duck_message = await channel.send('A wild 🦆 has appeared!!')
        logger.debug(f'Released a new duck in {channel.name} with message {self.last_duck_message.id}')
        self.current_duck_channel = channel.id
        self.last_duck_spawn_time = time.time()

    async def print_duck_family_or_pgtips_gif(self, message, user):
        embed_url = None
        if user.ducks_killed > 0 and not user.has_repented_for_shooting_ducks():
            embed_url = 'https://c.tenor.com/4aYkNoeULW4AAAAC/mokey-puppet-monkey.gif'
            message_parts = [
                'You\'ve shot ducks 😱',
                'No family for you!',
            ]
        elif user.ducks_befriended > 0:
            message_parts = [
                'Your duckie fam is here!',
                '🦆' * user.ducks_befriended,
            ]
            if user.ducks_killed > 0:
                message_parts[1] += '🪦' * user.ducks_killed
        else:
            embed_url = 'https://c.tenor.com/qV4ycK5YEY8AAAAC/shrug-idk.gif'
            message_parts = [
                'You should meet more ducks',
            ]
        if embed_url is not None:
            embed = discord.Embed()
            embed.set_image(url=embed_url)
        else:
            embed = None
        await message.reply("\n".join(message_parts), embed=embed)

    async def print_duck_graves(self, message, user):
        if user.ducks_killed < 1:
            embed_url = 'https://c.tenor.com/lndtLWwXZC0AAAAi/%D1%87%D1%82%D0%BE.gif'
            embed = discord.Embed()
            embed.set_image(url=embed_url)
            await message.reply(embed=embed)
        else:
            message_parts = [
                'RIP 🌸 🌼 🌻 ✿ ❀ ✾ 💐 🌷',
                '🪦' * user.ducks_killed
            ]
            await message.reply("\n".join(message_parts))
