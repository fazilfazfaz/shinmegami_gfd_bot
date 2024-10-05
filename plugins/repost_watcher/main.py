import re

import discord

from database.helper import gfd_links_database_helper
from database.models import PostedLinkV2
from plugins.base import BasePlugin


class RepostWatcher(BasePlugin):
    link_regex = r'https?://[^\s]{1,2048}'
    basic_url_regex_pattern = re.compile(link_regex, re.DOTALL)
    link_count_msg_pattern = re.compile(r'\.linkcount <?(' + link_regex + ')', re.DOTALL)

    async def on_message(self, message):
        if message.content == '.toplinks':
            await self.post_top_links(message)
            return
        if message.content.startswith('.linkcount '):
            await self.post_link_count(message)
            return
        reacted = False
        for link in re.finditer(self.basic_url_regex_pattern, message.content):
            actual_link = link.group(0)
            actual_link = self.clean_link(actual_link)
            hits = PostedLinkV2.get_hits_by_link(actual_link)
            posted_link = await self.process_link(actual_link)
            if reacted is False and hits > 1:
                reacted = True
                await message.add_reaction('♻')

    @staticmethod
    async def process_link(link) -> PostedLinkV2:
        link_minus_qp, qp = PostedLinkV2.parse_link(link)
        gfd_links_database_helper.replenish_db()
        posted_link: PostedLinkV2
        posted_link, create = PostedLinkV2.get_or_create(link_minus_qp=link_minus_qp, qp=qp)
        posted_link.increment_hits()
        posted_link.save()
        gfd_links_database_helper.release_db()
        return posted_link

    @staticmethod
    async def post_top_links(message):
        gfd_links_database_helper.replenish_db()
        num_links = 10
        posted_links: list[PostedLinkV2] = PostedLinkV2.get_top_links(num_links)
        gfd_links_database_helper.release_db()
        if len(posted_links) < 1:
            await message.reply('No links recorded yet')
            return
        message_parts = [
            f'These are the top {num_links} links posted:',
        ]
        for posted_link in posted_links:
            message_parts.append(f'<{posted_link.full_link()}> ({PostedLinkV2.get_hits_times_text(posted_link.hits)})')
        await message.reply("\n".join(message_parts))

    async def post_link_count(self, message):
        m = self.link_count_msg_pattern.search(message.content)
        if m is None:
            await message.reply('I need a link to work with 🏺🪙')
            return
        gfd_links_database_helper.replenish_db()
        hits = PostedLinkV2.get_hits_by_link(self.clean_link(m.group(1)))
        gfd_links_database_helper.release_db()
        if hits < 1:
            embed_url = 'https://media.tenor.com/v6FjukZCkggAAAAd/i-dont-know-what-that-is-data.gif'
            embed = discord.Embed()
            embed.set_image(url=embed_url)
            await message.reply(embed=embed)
            return
        await message.reply(f'I\'ve seen this {PostedLinkV2.get_hits_times_text(hits)} in the past')

    @staticmethod
    def clean_link(actual_link):
        return actual_link.strip('<>')
