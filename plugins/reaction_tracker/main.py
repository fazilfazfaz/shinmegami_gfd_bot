import asyncio
import sqlite3

import discord

from database.helper import gfd_emojis_database_helper
from database.models import UserReaction, db_emojis
from helpers.lists import chunks
from logger import logger
from plugins.base import BasePlugin


class ReactionTracker(BasePlugin):
    payloads = []

    def on_ready(self):
        if self.is_ready():
            return
        asyncio.get_event_loop().create_task(self.run())

    async def on_message(self, message: discord.Message):
        if message.content.lower() == '.emojis':
            await self.post_emoji_stats(message)
        if message.content.lower() == '.emojis-users':
            await self.post_emoji_users(message)
        elif message.content.lower().startswith('.emojis') and len(message.mentions) > 0:
            await self.post_emoji_stats_for_users(message)

    async def run(self):
        while True:
            try:
                await asyncio.sleep(30)
                copy = self.payloads.copy()
                self.payloads = []
                if len(copy) > 0:
                    await self.process_payloads(copy)
            except Exception as e:
                print(e)

    @staticmethod
    async def post_emoji_stats(message: discord.Message):
        gfd_emojis_database_helper.replenish_db()
        res: sqlite3.Cursor = db_emojis.execute_sql(
            'SELECT emoji_id,emoji_str,SUM(CASE WHEN is_add THEN 1 ELSE -1 END) AS count FROM userreaction\n'
            'GROUP BY COALESCE(emoji_id, emoji_str)\n'
            'ORDER BY count DESC\n'
            'LIMIT 10'
        )
        rows = res.fetchall()
        message_parts = []
        for row in rows:
            if row[2] < 1:
                continue
            if row[0]:
                emoji_str = f'<:test:{row[0]}>'
            else:
                emoji_str = row[1]
            message_parts.append(f'{emoji_str}: {row[2]}')
        if len(message_parts) == 0:
            await message.reply('I haven\'t tracked anything yet')
        else:
            chunk: list
            for chunk in chunks(message_parts, 30):
                await message.reply("\n".join(chunk))
        gfd_emojis_database_helper.release_db()

    @staticmethod
    async def post_emoji_users(message: discord.Message):
        gfd_emojis_database_helper.replenish_db()
        message_parts = []
        res: sqlite3.Cursor = db_emojis.execute_sql(
            'SELECT target_user_id, SUM(CASE WHEN is_add THEN 1 ELSE -1 END) AS count FROM userreaction\n'
            'GROUP BY target_user_id\n'
            'HAVING count > 0\n'
            'ORDER BY count DESC\n'
        )
        rows = res.fetchall()
        if len(rows):
            message_parts.append(f'**Receivers:**')
            for row in rows:
                message_parts.append(f'<@{row[0]}>: {row[1]}')
        res: sqlite3.Cursor = db_emojis.execute_sql(
            'SELECT source_user_id, SUM(CASE WHEN is_add THEN 1 ELSE -1 END) AS count FROM userreaction\n'
            'GROUP BY source_user_id\n'
            'HAVING count > 0\n'
            'ORDER BY count DESC\n'
        )
        rows = res.fetchall()
        if len(rows):
            message_parts.append(f'**Givers:**')
            for row in rows:
                message_parts.append(f'<@{row[0]}>: {row[1]}')
        if len(message_parts) == 0:
            await message.reply('I haven\'t tracked anything yet')
        else:
            await message.reply("\n".join(message_parts), allowed_mentions=discord.AllowedMentions(users=False))
        gfd_emojis_database_helper.release_db()

    @staticmethod
    def _add_to_user_specific_message_parts(emojis, user_specific_message_parts, header) -> int:
        message_parts = []
        total = 0
        for emoji in emojis:
            if emoji[2] < 1:
                continue
            if emoji[0]:
                emoji_str = f'<:test:{emoji[0]}>'
            else:
                emoji_str = emoji[1]
            message_parts.append(f'{emoji_str}\t{emoji[2]}')
            total += emoji[2]
        if len(message_parts) != 0:
            message_parts.insert(0, header)
            user_specific_message_parts += message_parts
        return total

    @staticmethod
    async def post_emoji_stats_for_users(message: discord.Message):
        gfd_emojis_database_helper.replenish_db()
        message_parts = []
        for user in message.mentions:
            res: sqlite3.Cursor = db_emojis.execute_sql(
                'SELECT emoji_id,emoji_str,SUM(CASE WHEN is_add THEN 1 ELSE -1 END) AS count FROM userreaction\n'
                'WHERE target_user_id = ?\n'
                'GROUP BY COALESCE(emoji_id, emoji_str)\n'
                'ORDER BY count desc',
                (user.id,)
            )
            emojis_received = res.fetchall()
            res: sqlite3.Cursor = db_emojis.execute_sql(
                'SELECT emoji_id,emoji_str,SUM(CASE WHEN is_add THEN 1 ELSE -1 END) AS count FROM userreaction\n'
                'WHERE source_user_id = ?\n'
                'GROUP BY COALESCE(emoji_id, emoji_str)\n'
                'ORDER BY count desc',
                (user.id,)
            )
            emojis_given = res.fetchall()
            user_specific_message_parts = []
            received_total = 0
            given_total = 0
            if len(emojis_received) > 0:
                received_total = ReactionTracker._add_to_user_specific_message_parts(
                    emojis_received,
                    user_specific_message_parts,
                    '*Reactions received*',
                )
            if len(emojis_given) > 0:
                given_total = ReactionTracker._add_to_user_specific_message_parts(
                    emojis_given,
                    user_specific_message_parts,
                    '*Reactions given*',
                )
            if len(user_specific_message_parts) != 0:
                user_specific_message_parts.insert(0, f'Stats for **{user.display_name}**:')
                user_specific_message_parts.insert(1, f'Total given: **{given_total}**, received: **{received_total}**')
                user_specific_message_parts.append('')
                message_parts += user_specific_message_parts
        if len(message_parts) == 0:
            await message.reply('I don\'t have any data')
        else:
            await message.reply("\n".join(message_parts))
        gfd_emojis_database_helper.release_db()

    async def track_reaction(self, payload: discord.RawReactionActionEvent):
        if payload.user_id == self.client.user.id:
            return
        self.payloads.append(payload)
        logger.info('Tracked reaction')

    async def process_payloads(self, payloads: list[discord.RawReactionActionEvent]):
        gfd_emojis_database_helper.replenish_db()
        logger.info('Saving tracked reactions')
        for payload in payloads:
            is_add = True
            if payload.event_type == 'REACTION_ADD':
                target_user_id = payload.message_author_id
            elif payload.event_type == 'REACTION_REMOVE':
                is_add = False
                channel = await self.client.guilds[0].fetch_channel(payload.channel_id)
                message = await channel.fetch_message(payload.message_id)
                target_user_id = message.author.id
            else:
                continue
            if payload.user_id == target_user_id:
                continue
            if payload.emoji.is_custom_emoji():
                emoji_id = payload.emoji.id
                emoji_str = None
            else:
                emoji_id = None
                emoji_str = str(payload.emoji)
            UserReaction.create(
                source_user_id=payload.user_id,
                target_user_id=target_user_id,
                emoji_id=emoji_id,
                emoji_str=emoji_str,
                is_add=is_add
            )
        gfd_emojis_database_helper.release_db()
