import random
from typing import Optional

import discord
import peewee

from database.helper import gfd_database_helper
from database.models import GiftySanta as GiftySantaDbModel, GiftySantaAssignment
from plugins.base import BasePlugin


class GiftySanta(BasePlugin):
    no_gifty_message = 'There is no gifty santa in progress for that to work!'

    def __init__(self, client, config):
        super().__init__(client, config)
        channel_config_key = 'GIFTY_SANTA_CHANNEL'
        if channel_config_key in self.config:
            self.gifty_channel_id = int(self.config[channel_config_key])
        else:
            raise Exception(channel_config_key + ' must be set for ' + self.__class__.__name__)
        self.gifty_channel: Optional[discord.TextChannel] = None
        self.current_gifty_santa: Optional[GiftySantaDbModel] = None

    async def on_message(self, message: discord.Message):
        if not self.gifty_channel:
            self.gifty_channel = self.client.get_channel(self.gifty_channel_id)
        is_private = message.channel.type == discord.ChannelType.private
        if is_private:
            await self.on_message_private(message)
            return
        if message.channel.id != self.gifty_channel_id:
            return
        await self.on_message_channel(message)

    async def on_message_private(self, message: discord.Message):
        if message.content.lower().startswith('.set-gift'):
            await self.set_gift(message)

    async def set_gift(self, message: discord.Message):
        gift_name = message.content[10:]
        if len(gift_name) < 1:
            await message.reply('Gift must be specified!')
            return
        self.load_current_gifty_santa()
        if self.current_gifty_santa is None:
            await message.reply(self.no_gifty_message)
            return
        gfd_database_helper.replenish_db()
        assignment: GiftySantaAssignment = GiftySantaAssignment.get_or_none(
            GiftySantaAssignment.gift_santa_id == self.current_gifty_santa.id,
            GiftySantaAssignment.santa_user_id == message.author.id,
        )
        if assignment is None:
            gfd_database_helper.release_db()
            await message.reply('Santas have not been assigned yet!')
        else:
            is_setting = assignment.gift_name is None
            assignment.gift_name = gift_name
            assignment.save()
            gfd_database_helper.release_db()
            await message.reply('Gift has been set!' if is_setting else 'Gift has been updated!')

    async def on_message_channel(self, message: discord.Message):
        message_lower = message.content.lower()
        if message_lower.startswith('.start-santa'):
            await self.start_gifty_santa(message)
        elif message_lower.startswith('.end-santa'):
            await self.end_gifty_santa(message)
        elif message_lower.startswith('.assign-santas'):
            await self.assign_santas(message)
        elif message_lower.startswith('.reveal-gift'):
            await self.reveal_gift(message)

    async def start_gifty_santa(self, message: discord.Message):
        name = message.content[13:]
        if len(name) < 1:
            await message.reply('A name must be provided!')
            return
        self.load_current_gifty_santa()
        if self.current_gifty_santa is not None:
            await message.reply(f'There is another gifty santa in progress! **{self.current_gifty_santa.name}**')
            return
        gfd_database_helper.replenish_db()
        self.current_gifty_santa = GiftySantaDbModel.create(name=name)
        gfd_database_helper.release_db()
        await message.reply(f"A new gifty santa has started 🎅\nUse `.assign-santas` when ready!")

    async def end_gifty_santa(self, message: discord.Message):
        self.load_current_gifty_santa()
        if self.current_gifty_santa is None:
            await message.reply('There is no gifty santa in progress!\nAnd I can\'t actually murder santas!')
            return
        old_name = self.current_gifty_santa.name
        gfd_database_helper.replenish_db()
        self.current_gifty_santa.is_complete = True
        self.current_gifty_santa.save()
        gfd_database_helper.release_db()
        self.current_gifty_santa = None
        await message.reply(f'Gifty santa **{old_name}** has concluded 🎅\nThanks everyone for participating!')

    async def assign_santas(self, message: discord.Message):
        self.load_current_gifty_santa()
        if self.current_gifty_santa is None:
            await message.reply(self.no_gifty_message)
            return
        if isinstance(self.gifty_channel, discord.Thread):
            members = await self.gifty_channel.fetch_members()
            members = list(map(lambda x: self.gifty_channel.guild.get_member(x.id), members))
        else:
            members = self.gifty_channel.members
        channel_members_without_me = list(filter(lambda x: x.id != self.client.user.id, members))
        picked = set()
        gfd_database_helper.replenish_db()
        is_reassigned = False
        for member in channel_members_without_me:
            while True:
                giftee = random.choice(channel_members_without_me)
                if giftee.id == member.id or giftee.id in picked:
                    continue
                picked.add(giftee.id)
                break
            assignment: GiftySantaAssignment
            created: bool
            assignment, created = GiftySantaAssignment.get_or_create(
                gift_santa_id=self.current_gifty_santa.id,
                santa_user_id=member.id,
                giftee_user_id=giftee.id
            )
            if not created:
                is_reassigned = True
                assignment.giftee_user_id = giftee.id
                assignment.save()

            channel = await member.create_dm()
            await channel.send(f'Your giftee for **{self.current_gifty_santa.name}** is **{giftee.display_name}**!')
        gfd_database_helper.release_db()
        await message.reply('Santas have been re-assigned!' if is_reassigned else 'Santas have been assigned!')

    async def reveal_gift(self, message):
        self.load_current_gifty_santa()
        if self.current_gifty_santa is None:
            await message.reply(self.no_gifty_message)
            return
        gfd_database_helper.replenish_db()
        query = GiftySantaAssignment.select() \
            .where(GiftySantaAssignment.is_revealed == False, GiftySantaAssignment.gift_name != None) \
            .order_by(peewee.fn.Random()) \
            .limit(1)
        assignment: GiftySantaAssignment = query.get_or_none()
        if assignment is None:
            gfd_database_helper.release_db()
            await message.reply('No pending reveals!')
        else:
            await message.reply(f'The gift for <@{assignment.giftee_user_id}> is **{assignment.gift_name}**')
            assignment.is_revealed = True
            assignment.save()
            gfd_database_helper.release_db()

    def load_current_gifty_santa(self):
        if self.current_gifty_santa is not None:
            return
        gfd_database_helper.replenish_db()
        self.current_gifty_santa = GiftySantaDbModel.get_or_none(GiftySantaDbModel.is_complete == False)
        gfd_database_helper.release_db()
